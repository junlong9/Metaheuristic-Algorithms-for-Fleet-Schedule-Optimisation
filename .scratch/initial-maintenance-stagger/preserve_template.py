"""Package Artifact Tool-authored values in the exact original Excel template.

Keep native drawing/chart settings and all styles, which the spreadsheet
import/render path does not fully retain. No workbook-authoring library is
used here: only authored cell payloads and chart caches are transferred.
"""
import copy
from datetime import datetime
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree as ET
from openpyxl.utils.datetime import to_excel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
data = json.loads((HERE / "schedule-data.json").read_text())
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CHART = "http://schemas.openxmlformats.org/drawingml/2006/chart"
ns = {"s": NS, "c": CHART}


def strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(si.itertext()) for si in tree]


def transfer_rows(original, authored, last_row, sst):
    template = ET.fromstring(original)
    generated = ET.fromstring(authored)
    old_rows = template.find(f"{{{NS}}}sheetData")
    new_rows = generated.find(f"{{{NS}}}sheetData")
    originals = {cell.get("r"): cell for cell in old_rows.iter(f"{{{NS}}}c")}
    incoming = {int(row.get("r")): row for row in new_rows}
    style_by_column = {''.join(filter(str.isalpha, cell.get('r'))): cell.get('s')
                       for cell in old_rows[1]}
    header = copy.deepcopy(old_rows[0])
    old_rows.clear()
    old_rows.append(header)
    for number in range(2, last_row + 1):
        row = ET.SubElement(old_rows, f"{{{NS}}}row", r=str(number))
        for authored_cell in incoming[number]:
            reference = authored_cell.get("r")
            if authored_cell.find(f"{{{NS}}}v") is None and authored_cell.find(f"{{{NS}}}is") is None:
                continue
            column = ''.join(filter(str.isalpha, reference))
            cell = copy.deepcopy(authored_cell)
            cell.attrib.clear()
            cell.set("r", reference)
            old = originals.get(reference)
            style = old.get("s") if old is not None else style_by_column.get(column)
            if style is not None:
                cell.set("s", style)
            kind = authored_cell.get("t")
            if kind == "s":
                index = int(authored_cell.find(f"{{{NS}}}v").text)
                cell.clear()
                cell.set("r", reference)
                if style is not None:
                    cell.set("s", style)
                cell.set("t", "inlineStr")
                inline = ET.SubElement(cell, f"{{{NS}}}is")
                text = ET.SubElement(inline, f"{{{NS}}}t")
                text.text = sst[index]
            elif kind == "d":
                value = cell.find(f"{{{NS}}}v")
                value.text = str(to_excel(datetime.fromisoformat(value.text.replace('Z', '+00:00')).replace(tzinfo=None)))
            elif kind:
                cell.set("t", kind)
            row.append(cell)
    dimension = template.find(f"{{{NS}}}dimension")
    last_column = ''.join(filter(str.isalpha, header[-1].get('r')))
    dimension.set("ref", f"A1:{last_column}{last_row}")
    return ET.tostring(template, xml_declaration=True, encoding="UTF-8", standalone=True)


with ZipFile(ROOT / data["source"]) as template:
    for variant in data["variants"]:
        modified = {}
        with ZipFile(HERE / f"template-data-{variant['slug']}.xlsx") as authored:
            sst = strings(authored)
            for index, count in [(1, len(variant["events"]) + 1), (2, len(variant["daily"]) + 1), (3, 25), (5, 2)]:
                part = f"xl/worksheets/sheet{index}.xml"
                modified[part] = transfer_rows(template.read(part), authored.read(part), count, sst)
            availability = ET.fromstring(modified["xl/worksheets/sheet2.xml"])
            cells = {c.get("r"): c.find(f"{{{NS}}}v").text
                     for c in availability.iter(f"{{{NS}}}c") if c.find(f"{{{NS}}}v") is not None}
            chart = ET.fromstring(template.read("xl/charts/chart1.xml"))
            cache = chart.find('.//c:ser/c:val/c:numRef/c:numCache', namespaces=ns)
            points = cache.findall('c:pt', namespaces=ns)
            assert len(points) == len(variant["daily"])
            for point in points:
                row = int(point.get("idx")) + 2
                point.find('c:v', namespaces=ns).text = cells[f"C{row}"]
            modified["xl/charts/chart1.xml"] = ET.tostring(chart, xml_declaration=True, encoding="UTF-8", standalone=True)
        output = ROOT / "outputs" / "initial-stagger-20261013" / variant["filename"]
        with ZipFile(output, "w") as final:
            for entry in template.infolist():
                final.writestr(copy.copy(entry), modified.get(entry.filename, template.read(entry.filename)))
        print(f"Matched original template: {output.name}")
