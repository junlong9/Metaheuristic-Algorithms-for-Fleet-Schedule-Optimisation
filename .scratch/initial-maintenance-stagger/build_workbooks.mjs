import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const output = path.join(root, 'outputs', 'initial-stagger');
const data = JSON.parse(await fs.readFile(path.join(here, 'schedule-data.json'), 'utf8'));
await fs.mkdir(output, { recursive: true });
await fs.mkdir(path.join(here, 'previews'), { recursive: true });
const navy = '#203A53', light = '#EAF0F5', blue = '#397EAB';
const date = value => value ? new Date(`${value}T00:00:00Z`) : null;

function table(sheet, headers, rows, dates = []) {
  const values = [headers, ...rows.map(row => row.map((value, i) => dates.includes(i) ? date(value) : value))];
  const range = sheet.getRangeByIndexes(0, 0, values.length, headers.length);
  range.values = values;
  range.format.font = {name: 'Arial', size: 10, color: '#253443'};
  range.format.rowHeight = 20;
  range.format.columnWidth = 18;
  range.format.verticalAlignment = 'center';
  const header = sheet.getRangeByIndexes(0, 0, 1, headers.length);
  header.format = {fill: navy, font: {name: 'Arial', size: 10, bold: true, color: '#FFFFFF'}, wrapText: true};
  header.format.rowHeight = 38;
  header.format.horizontalAlignment = 'center';
  for (const i of dates) sheet.getRangeByIndexes(1, i, rows.length, 1).setNumberFormat('dd mmm yyyy');
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  return range;
}

for (const variant of data.variants) {
  const workbook = Workbook.create();
  for (const name of ['Summary', 'MxEvents', 'Availability', 'Fleet', 'CheckRules', 'History', 'OperationalConstraints']) workbook.worksheets.add(name);
  const summary = workbook.worksheets.getItem('Summary');
  const events = workbook.worksheets.getItem('MxEvents');
  const availability = workbook.worksheets.getItem('Availability');
  const fleet = workbook.worksheets.getItem('Fleet');
  const rules = workbook.worksheets.getItem('CheckRules');
  const history = workbook.worksheets.getItem('History');
  const operational = workbook.worksheets.getItem('OperationalConstraints');
  table(events, data.event_columns, variant.events, [2, 3, 5, 6, 7]);
  table(history, data.event_columns, variant.history, [2, 3, 5, 6, 7]);
  table(fleet, data.fleet_columns, variant.fleet, [1, 3, 4, 5, 6, 7, 8, 11, 12, 13]);
  fleet.getRange('A1:P1').format.rowHeight = 58;
  fleet.getRange('C1:C25').format.columnWidth = 24;
  fleet.getRange('J1:K25').format.columnWidth = 24;
  fleet.getRange('O1:P25').format.columnWidth = 24;
  table(rules, ['Check', 'Duration_Days', 'Interval_Days', 'Early_Start_Allowance_Days'],
    Object.entries(data.rules).map(([check, rule]) => [check, rule.duration, rule.interval, rule.early]));
  rules.getRange('B1:D5').format.columnWidth = 26;
  table(availability, ['Date', 'In_Maintenance', 'Available', 'D_In_Maintenance'], variant.daily, [0]);
  const lastDayRow = variant.daily.length + 1;
  availability.getRange(`C2:C${lastDayRow}`).formulas = variant.daily.map((_, i) => [`=Summary!$B$7-B${i + 2}`]);
  availability.getRange(`B2:D${lastDayRow}`).setNumberFormat('0');
  const lastEventRow = variant.events.length + 1;
  events.getRange(`D2:D${lastEventRow}`).formulas = variant.events.map((_, i) => [`=C${i + 2}+E${i + 2}`]);
  const lastHistoryRow = variant.history.length + 1;
  if (variant.history.length) history.getRange(`D2:D${lastHistoryRow}`).formulas = variant.history.map((_, i) => [`=C${i + 2}+E${i + 2}`]);

  const original = data.original_metrics;
  const current = variant.metrics;
  const metricRows = [
    ['Aircraft', data.fleet_size, data.fleet_size, 'aircraft'],
    ['Forecast starts', date(data.forecast_start), date(data.forecast_start), 'inclusive'],
    ['Forecast ends', date(data.forecast_end), date(data.forecast_end), 'inclusive'],
    ['Peak simultaneous D checks', original.peak_concurrent_D_checks, current.peak_concurrent_D_checks, 'aircraft'],
    ['Worst-day availability', original.worst_day_availability, current.worst_day_availability, 'aircraft'],
    ['Availability standard deviation', original.availability_std_population, current.availability_std_population, 'population'],
    ['Mean availability', original.mean_availability, current.mean_availability, 'aircraft'],
    ['Maintenance aircraft-days', original.maintenance_aircraft_days, current.maintenance_aircraft_days, 'within horizon'],
    ['D checks intersecting forecast', original.visible_D_count, current.visible_D_count, 'includes later cycles'],
    ['Aircraft with first D before 2030', original.aircraft_first_D_before_2030, current.aircraft_first_D_before_2030, 'aircraft'],
    ['Earliest first forecast D start', date(original.first_D_start), date(current.first_D_start), 'calendar date'],
    ['Latest first forecast D start', date(original.last_first_D_start), date(current.last_first_D_start), 'calendar date'],
    ['Loose scenario', original.operational_scenarios.loose.passes ? 'Pass' : 'Fail', current.operational_scenarios.loose.passes ? 'Pass' : 'Fail', 'unchanged rules'],
    ['Medium scenario', original.operational_scenarios.medium.passes ? 'Pass' : 'Fail', current.operational_scenarios.medium.passes ? 'Pass' : 'Fail', 'unchanged rules'],
    ['Tight scenario', original.operational_scenarios.tight.passes ? 'Pass' : 'Fail', current.operational_scenarios.tight.passes ? 'Pass' : 'Fail', 'dependency breaches'],
  ];
  summary.showGridLines = false;
  summary.tabColor = navy;
  summary.getRange('A1:S44').format.font = {name: 'Arial', size: 10, color: '#253443'};
  summary.getRange('A1:S44').format.rowHeight = 22;
  summary.getRange('A1:A44').format.columnWidth = 42;
  summary.getRange('B1:C44').format.columnWidth = 18;
  summary.getRange('D1:D44').format.columnWidth = 22;
  summary.getRange('E1:E44').format.columnWidth = 3;
  summary.getRange('F1:S44').format.columnWidth = 10;
  summary.getRange('A2').values = [[variant.title]];
  summary.getRange('A2').format.font = {name: 'Arial', size: 15, bold: true, color: navy};
  summary.getRange('A3').values = [['Synthetic input forecast with older initial maintenance ages.']];
  summary.getRange('A4').values = [[variant.slug === 'moderate'
    ? 'Three age cohorts: phase advances of 1, 3 and 5 model years; 8 aircraft in each.'
    : 'Six age cohorts: phase advances of 1 to 6 model years; 4 aircraft in each.']];
  summary.getRange('A6:D6').values = [['Metric', 'Original forecast', 'This forecast', 'Units / scope']];
  summary.getRange('A6:D6').format = {fill: navy, font: {name: 'Arial', size: 10, bold: true, color: '#FFFFFF'}};
  summary.getRange('A7:D21').values = metricRows;
  summary.getRange('B8:C9').setNumberFormat('dd mmm yyyy');
  summary.getRange('B17:C18').setNumberFormat('dd mmm yyyy');
  summary.getRange('B12:C13').setNumberFormat('0.000');
  summary.getRange('B14:C16').setNumberFormat('#,##0');
  summary.getRange('C10').formulas = [[`=MAX(Availability!D2:D${lastDayRow})`]];
  summary.getRange('C11').formulas = [[`=MIN(Availability!C2:C${lastDayRow})`]];
  summary.getRange('C12').formulas = [[`=STDEV.P(Availability!C2:C${lastDayRow})`]];
  summary.getRange('C13').formulas = [[`=AVERAGE(Availability!C2:C${lastDayRow})`]];
  summary.getRange('C14').formulas = [[`=SUM(Availability!B2:B${lastDayRow})`]];
  summary.getRange('C15').formulas = [[`=COUNTIF(MxEvents!B2:B${lastEventRow},"D")`]];
  summary.getRange('C16').formulas = [['=COUNTIF(Fleet!M2:M25,"<"&DATE(2030,1,1))']];
  summary.getRange('C17').formulas = [['=MIN(Fleet!M2:M25)']];
  summary.getRange('C18').formulas = [['=MAX(Fleet!M2:M25)']];
  fleet.getRange('O2:O25').formulas = variant.fleet.map((_, i) => [`=Summary!$B$8+CheckRules!$C$5-I${i + 2}`]);
  fleet.getRange('O2:O25').setNumberFormat('0');
  for (const row of [10, 11]) summary.getRange(`A${row}:D${row}`).format.fill = light;
  summary.getRange('A23:D23').values = [['Year', 'Original D starts', 'This D starts', 'This peak D overlap']];
  summary.getRange('A23:D23').format = {fill: navy, font: {name: 'Arial', size: 10, bold: true, color: '#FFFFFF'}, wrapText: true};
  summary.getRange('A23:D23').format.rowHeight = 34;
  const annual = variant.annual.map((row, i) => [row[0], data.original_annual[i][1], row[1], row[2]]);
  summary.getRange(`A24:D${23 + annual.length}`).values = annual;
  summary.getRange('A24:D36').setNumberFormat('0');
  const annualFormulas = annual.map((_, i) => [`=COUNTIFS(MxEvents!$B$2:$B$${lastEventRow},"D",MxEvents!$C$2:$C$${lastEventRow},">="&DATE(A${24 + i},1,1),MxEvents!$C$2:$C$${lastEventRow},"<"&DATE(A${24 + i}+1,1,1))`]);
  summary.getRange(`C24:C${23 + annual.length}`).formulas = annualFormulas;
  const chart = summary.charts.add('bar', summary.getRange(`A23:C${23 + annual.length}`));
  chart.title = 'D check starts by year, including later cycles';
  chart.titleTextStyle.typeface = 'Arial';
  chart.titleTextStyle.fontSize = 13;
  chart.setPosition('F6', 'S22');
  chart.legend = {position: 'bottom', textStyle: {typeface: 'Arial', fontSize: 11}};
  chart.xAxis = {axisType: 'textAxis', textStyle: {typeface: 'Arial', fontSize: 10}};
  chart.yAxis = {numberFormatCode: '0', numberFormatSourceLinked: false, textStyle: {typeface: 'Arial', fontSize: 10}};
  chart.series.items[0].fill = '#A2AAB2';
  chart.series.items[1].fill = blue;
  const notes = [
    'A: 42 days early. B, C and D: 70 days early. Durations and reset intervals are unchanged.',
    'This is a new input dataset. Future displacement limits use this dataset as the loaded reference.',
    'Changed initial ages bring later D cycles into the forecast. Mean availability can therefore fall.',
    'Fleet records opening due clocks and sequence positions. History records checks completed before the forecast.',
    'The current optimiser assumes the opening A check. It needs an initial-state adapter to use these aged inputs.',
    'Source: heavy_maintenance_forecast.xlsx; operational scenarios copied from operational_constraints.json.',
    'Daily maintenance counts are generated snapshots; check-end and summary formulas recalculate in Excel.',
  ];
  summary.getRange('A38:A44').values = notes.map(note => [note]);
  summary.getRange('A38:A44').format.font = {name: 'Arial', size: 10, color: '#526170'};

  const auditRows = [];
  for (const [name, scenario] of Object.entries(current.operational_scenarios)) {
    auditRows.push([name, 'Displacement from this loaded input', null, null, null, null, 0, scenario.displacement_limit_days, 0]);
    for (const p of scenario.busy_periods) auditRows.push([name, 'Busy period', null, p.start, p.end, p.minimum_availability, p.actual_minimum, null, p.breach_days]);
    for (const g of scenario.dependency_groups) auditRows.push([name, 'Dependency group', g.aircraft.join(', '), null, null, g.minimum_available, g.actual_minimum, null, g.breach_days]);
  }
  table(operational, ['Scenario', 'Constraint', 'Aircraft', 'Start', 'End', 'Minimum_Required', 'Actual_Minimum', 'Displacement_Limit_Days', 'Breach_Days'], auditRows, [3, 4]);
  operational.getRange('B1:B16').format.columnWidth = 39;
  operational.getRange('C1:C16').format.columnWidth = 64;
  operational.getRange('F1:I16').format.columnWidth = 24;
  operational.getRange('I2:I16').conditionalFormats.add('cellIs', {operator: 'greaterThan', formula: 0, format: {fill: '#FCE8E6', font: {color: '#9E2424', bold: true}}});

  workbook.recalculate();
  console.log(variant.slug, (await workbook.inspect({kind: 'table', range: 'Summary!A7:D21', include: 'values,formulas', tableMaxRows: 15, tableMaxCols: 4, maxChars: 2200})).ndjson);
  console.log((await workbook.inspect({kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!', options: {useRegex: true, maxResults: 20}, summary: 'Formula error scan', maxChars: 800})).ndjson);
  for (const [sheetName, range] of [['Summary', 'A1:S44'], ['MxEvents', 'A1:J8'], ['Availability', 'A1:D8'], ['Fleet', 'A1:P6'], ['CheckRules', 'A1:D5'], ['History', 'A1:J8'], ['OperationalConstraints', 'A1:I16']]) {
    const preview = await workbook.render({sheetName, range, scale: 1.5, format: 'png'});
    await fs.writeFile(path.join(here, 'previews', `${variant.slug}-${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(path.join(output, variant.filename));
  console.log('Exported', variant.filename);
}
