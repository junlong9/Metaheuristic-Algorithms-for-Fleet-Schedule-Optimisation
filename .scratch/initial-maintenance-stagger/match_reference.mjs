import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const data = JSON.parse(await fs.readFile(path.join(here, 'schedule-data.json'), 'utf8'));
const mode = process.argv[2] ?? 'inspect';
const previewDir = path.join(here, 'reference-previews');
await fs.mkdir(previewDir, {recursive: true});
const toDate = value => new Date(`${value}T00:00:00Z`);

if (mode === 'inspect') {
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(root, data.source)));
  console.log((await wb.inspect({kind: 'sheet', include: 'id,name', maxChars: 1800})).ndjson);
  for (const [sheetName, range] of [['MxEvents','A1:J7'], ['Availability','A1:T28'], ['Fleet','A1:B6'], ['CheckRules','A1:D5'], ['Summary','A1:G2']]) {
    const preview = await wb.render({sheetName, range, scale: 1.5, format: 'png'});
    await fs.writeFile(path.join(previewDir, `original-${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
} else {
  for (const variant of data.variants) {
    const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(root, data.source)));
    const mx = wb.worksheets.getItem('MxEvents');
    mx.getRange('A2:J279').clear({applyTo: 'contents'});
    mx.getRangeByIndexes(1, 0, variant.events.length, 10).values = variant.events.map(row =>
      row.map((value, col) => [2,3,5,6,7].includes(col) ? toDate(value) : value));
    const av = wb.worksheets.getItem('Availability');
    av.getRange('A2:C4382').values = variant.daily.map(row => [toDate(row[0]), row[1], row[2]]);
    const fleet = wb.worksheets.getItem('Fleet');
    // Preserve the aircraft order in the original template.
    const originalNames = fleet.getRange('A2:A25').values.flat();
    const initial = new Map(variant.fleet.map(row => [row[0], row[1]]));
    fleet.getRange('B2:B25').values = originalNames.map(name => [toDate(initial.get(name))]);
    // Match the source's sample variance / standard-deviation convention.
    const n = variant.daily.length;
    const mean = variant.metrics.mean_availability;
    const populationVariance = variant.metrics.availability_std_population ** 2;
    const sampleVariance = populationVariance * n / (n - 1);
    const available = variant.daily.map(row => row[2]);
    const unavailable = variant.daily.map(row => row[1]);
    wb.worksheets.getItem('Summary').getRange('A2:G2').values = [[
      mean, Math.min(...available), Math.max(...available), sampleVariance,
      Math.sqrt(sampleVariance), data.fleet_size - mean, Math.max(...unavailable),
    ]];
    wb.recalculate();
    console.log(variant.slug, (await wb.inspect({kind: 'table', range: 'Summary!A1:G2', tableMaxRows: 2, tableMaxCols: 7, maxChars: 1300})).ndjson);
    console.log((await wb.inspect({kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NUM!', options: {useRegex: true, maxResults: 10}, maxChars: 400})).ndjson);
    for (const [sheetName, range] of [['MxEvents','A1:J7'], ['Availability','A1:T28'], ['Fleet','A1:B6'], ['CheckRules','A1:D5'], ['Summary','A1:G2']]) {
      const preview = await wb.render({sheetName, range, scale: 1.5, format: 'png'});
      await fs.writeFile(path.join(previewDir, `${variant.slug}-${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
    }
    const xlsx = await SpreadsheetFile.exportXlsx(wb);
    await xlsx.save(path.join(here, `template-data-${variant.slug}.xlsx`));
  }
}
