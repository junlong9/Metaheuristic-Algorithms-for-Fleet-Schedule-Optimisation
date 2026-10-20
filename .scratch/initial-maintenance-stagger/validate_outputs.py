"""Audit the saved Excel files against the unchanged maintenance model."""
import hashlib
import json
import ast
from zipfile import ZipFile
from lxml import etree
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
# Load the exact existing rule/replay definitions without its plotting imports.
baseline_source = (ROOT / "vn_priority_based_selection.py").read_text()
definitions = {
    "_initial_due_dates", "_update_due_dates", "rebuild_aircraft_schedule",
    "is_aircraft_feasible", "is_feasible", "is_rule_compliant_schedule",
}
selected = [node for node in ast.parse(baseline_source).body
            if (isinstance(node, ast.FunctionDef) and node.name in definitions)
            or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id in {"CHECK_RULES", "CHECK_SEQUENCE"} for t in node.targets))]
namespace = {}
exec(compile(ast.Module(body=selected, type_ignores=[]), "baseline_rule_definitions", "exec"), namespace)
baseline = SimpleNamespace(**namespace)

data = json.loads((HERE / "schedule-data.json").read_text())
base = pd.Timestamp(data["forecast_start"])
end = pd.Timestamp(data["forecast_end"])
days = pd.date_range(base, end)
assert hashlib.sha256((ROOT / data["source"]).read_bytes()).hexdigest() == data["source_sha256"]
assert hashlib.sha256((ROOT / "operational_constraints.json").read_bytes()).hexdigest() == data["constraints_sha256"]
audits = []

for variant in data["variants"]:
    output = ROOT / "outputs" / "initial-stagger-20261013" / variant["filename"]
    xlsx = pd.ExcelFile(output)
    events = pd.read_excel(xlsx, sheet_name="MxEvents")
    history = pd.DataFrame(variant["history"], columns=data["event_columns"])
    for col in ["Start", "End", "Due_Date", "Earliest_Start", "Latest_Start"]:
        history[col] = pd.to_datetime(history[col])
    fleet = pd.read_excel(xlsx, sheet_name="Fleet")
    state = pd.DataFrame(variant["fleet"], columns=data["fleet_columns"])
    for col in ["First_Start", "Opening_D_Due"]:
        state[col] = pd.to_datetime(state[col])
    daily = pd.read_excel(xlsx, sheet_name="Availability")
    rules = pd.read_excel(xlsx, sheet_name="CheckRules")
    pd.testing.assert_frame_equal(rules, pd.read_excel(ROOT / data["source"], sheet_name="CheckRules"))
    assert xlsx.sheet_names == ["MxEvents", "Availability", "Fleet", "CheckRules", "Summary"]
    for name in xlsx.sheet_names:
        assert pd.read_excel(xlsx, sheet_name=name).columns.tolist() == pd.read_excel(ROOT / data["source"], sheet_name=name).columns.tolist()
    assert events.columns.tolist() == data["event_columns"]
    assert len(fleet) == 24 and fleet.Aircraft.nunique() == 24
    assert list(daily.Date) == list(days)
    complete = pd.concat([history, events]).sort_values(["Aircraft", "Start"])
    for aircraft, frame in complete.groupby("Aircraft"):
        origin = frame.iloc[0].Latest_Start
        schedule = {aircraft: [{
            "check": r.Check, "start": (r.Start - origin).days,
            "duration": int(r.Duration), "earliest_start": (r.Earliest_Start - origin).days,
            "latest_start": (r.Latest_Start - origin).days,
        } for r in frame.itertuples()]}
        validation_horizon = max(e["latest_start"] + e["duration"] for e in schedule[aircraft])
        assert baseline.is_rule_compliant_schedule(schedule, validation_horizon), aircraft
    occupancy = np.zeros((24, len(days)), dtype=int)
    ds = np.zeros(len(days), dtype=int)
    names = sorted(events.Aircraft.unique())
    for r in events.itertuples():
        assert r.End == r.Start + pd.Timedelta(days=r.Duration)
        assert r.Earliest_Start <= r.Start <= r.Latest_Start
        assert (r.Latest_Start - r.Earliest_Start).days == baseline.CHECK_RULES[r.Check]["early"]
        assert (r.Latest_Start - r.Start).days <= baseline.CHECK_RULES[r.Check]["early"]
        lo = max(0, (r.Start - base).days)
        hi = min(len(days), (r.End - base).days)
        assert lo < hi
        occupancy[names.index(r.Aircraft), lo:hi] += 1
        if r.Check == "D":
            ds[lo:hi] += 1
    assert occupancy.max() <= 1
    available = 24 - occupancy.sum(axis=0)
    np.testing.assert_array_equal(daily.In_Maintenance, occupancy.sum(axis=0))
    np.testing.assert_array_equal(daily.Available, available)
    for r in state.itertuples():
        assert 0 <= r.Opening_D_Age_Days <= baseline.CHECK_RULES["D"]["interval"]
        assert r.Opening_D_Age_Days == baseline.CHECK_RULES["D"]["interval"] - (r.Opening_D_Due - base).days
        upcoming = events[events.Aircraft == r.Aircraft].iloc[0]
        assert upcoming.Check == r.Opening_Check_Type
        assert upcoming.Start == r.First_Start
        assert fleet.loc[fleet.Aircraft == r.Aircraft, "First_Start"].iloc[0] == r.First_Start
    wb = openpyxl.load_workbook(output, read_only=True, data_only=True)
    summary = wb["Summary"]
    expected = [available.mean(), available.min(), available.max(), available.var(ddof=1),
                available.std(ddof=1), occupancy.sum(axis=0).mean(), occupancy.sum(axis=0).max()]
    np.testing.assert_allclose([c.value for c in summary[2]], expected, atol=1e-10)
    for sheet in wb:
        for row in sheet.iter_rows():
            assert not any(cell.data_type == "e" for cell in row), sheet.title
    wb.close()
    with ZipFile(ROOT / data["source"]) as reference, ZipFile(output) as exported:
        assert set(reference.namelist()) == set(exported.namelist())
        allowed = {"xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml", "xl/worksheets/sheet3.xml", "xl/worksheets/sheet5.xml", "xl/charts/chart1.xml"}
        assert all(reference.read(p) == exported.read(p) for p in reference.namelist() if p not in allowed)
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
        for number in [1, 2, 3, 5]:
            part = f"xl/worksheets/sheet{number}.xml"
            original_xml = etree.fromstring(reference.read(part))
            result_xml = etree.fromstring(exported.read(part))
            original_data = original_xml.find('s:sheetData', ns)
            result_data = result_xml.find('s:sheetData', ns)
            assert etree.tostring(original_data[0]) == etree.tostring(result_data[0])
            for element in [original_xml, result_xml]:
                element.remove(element.find('s:sheetData', ns))
                element.remove(element.find('s:dimension', ns))
            assert etree.tostring(original_xml) == etree.tostring(result_xml), part
        original_chart = etree.fromstring(reference.read('xl/charts/chart1.xml'))
        result_chart = etree.fromstring(exported.read('xl/charts/chart1.xml'))
        values = result_chart.findall('.//c:ser/c:val/c:numRef/c:numCache/c:pt/c:v', ns)
        np.testing.assert_array_equal([int(v.text) for v in values], available)
        for element in [original_chart, result_chart]:
            for value in element.findall('.//c:ser/c:val/c:numRef/c:numCache/c:pt/c:v', ns):
                value.text = '0'
        assert etree.tostring(original_chart) == etree.tostring(result_chart)
    audits.append({
        "file": output.name, "checks": len(events), "historical_checks": len(history),
        "worst_day_availability": int(available.min()), "peak_concurrent_D_checks": int(ds.max()),
        "maintenance_rules": "Pass: unchanged baseline replay on full histories",
        "daily_counts_and_formula_caches": "Pass", "source_files_unchanged": True,
        "exact_original_template_and_native_chart": "Pass",
        "operational_scenarios": {k: s["passes"] for k, s in variant["metrics"]["operational_scenarios"].items()},
    })
(HERE / "validation.json").write_text(json.dumps(audits, indent=2))
print(json.dumps(audits, indent=2))
