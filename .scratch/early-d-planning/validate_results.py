"""Independent audit of serialized plans using day occupancy and clock replay."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
folder = Path(__file__).parent
source = folder / "results-early730-comparison.json"
report = json.loads(source.read_text())
wb = openpyxl.load_workbook(ROOT/"heavy_maintenance_forecast.xlsx", read_only=True, data_only=True)
rows = iter(wb["MxEvents"].values)
headers = [str(c).strip() for c in next(rows)]
first_loaded = {}
for values in rows:
    row = dict(zip(headers, values))
    name = row["Aircraft"]
    if name not in first_loaded or row["Start"] < first_loaded[name]["Start"]:
        first_loaded[name] = row
base = datetime.fromisoformat(report["base_date"])
wb.close()
horizon = report["horizon_inclusive"]
allowance = report["D_early_allowance_days"]
names = ("A", "B", "C", "D")
durations = {"A":14, "B":28, "C":84, "D":126}
intervals = {"A":365, "B":730, "C":1460, "D":2920}
early = {"A":42, "B":70, "C":70, "D":allowance}
audits = []
assert len(report["runs"]) == 4, "The comparison must be complete"
for run in report["runs"]:
    schedule, metrics = run["schedule"], run["metrics"]
    assert set(schedule) == set(first_loaded)
    occupancy = {}
    total_earliness = 0
    for ac, checks in schedule.items():
        first = checks[0]["start"]
        assert first == (first_loaded[ac]["Latest_Start"]-base).days
        assert checks[0]["check"] == "A" and first == checks[0]["latest_start"]
        due = {"A":first, "B":first+365, "C":first+1095, "D":first+2555}
        previous_end = first
        occupied = np.zeros(horizon+1, dtype=bool)
        for check in checks:
            c, start = check["check"], check["start"]
            end = start+check["duration"]
            assert check["duration"] == durations[c]
            assert 0 <= start <= horizon and start >= previous_end
            assert start >= due[c]-early[c] and start <= min(due.values())
            assert check["earliest_start"] == max(0, due[c]-early[c])
            assert check["latest_start"] == due[c]
            for higher in names[names.index(c)+1:]:
                assert end <= due[higher]
            assert not occupied[start:min(end,horizon+1)].any()
            occupied[start:min(end,horizon+1)] = True
            if c == "D":
                total_earliness += due[c]-start
            for covered in names[:names.index(c)+1]:
                due[covered] = end+intervals[covered]
            previous_end = end
        assert min(due.values()) > horizon, (ac, "uncovered future deadline")
        assert due == run["terminal_due_dates"][ac]
        occupancy[ac] = occupied
    a = len(schedule)-sum(occupancy.values())
    outside = np.ones(horizon+1, dtype=bool)
    deficit = 0
    for period in metrics["periods"]:
        start, end = period["start_day"], period["end_day"]+1
        assert int(a[start:end].min()) == period["minimum"]
        assert period["minimum"] >= period["required"] == 20
        outside[start:end] = False
        deficit += int(np.maximum(period["required"]-a[start:end],0).sum())
    assert int(a.min()) == metrics["full_horizon_minimum"]
    assert int(a[outside].min()) == metrics["outside_minimum"]
    assert np.isclose(a.mean(), metrics["mean_availability"])
    assert np.isclose(a.std(), metrics["std_availability"])
    assert int((len(schedule)-a).sum()) == metrics["downtime_within_horizon"]
    assert total_earliness == metrics["D_early_days_total"]
    for group in report["dependency_groups"]:
        group_a = len(group["aircraft"])-sum(occupancy[ac] for ac in group["aircraft"])
        assert group_a.min() >= group["minimum_available"]
    final_score = (-float(deficit), -total_earliness/365,
                   float(a[outside].min())-float(a.std())/100)
    initial = metrics["initial_rebuilt"]
    initial_score = (-sum(p["deficit_aircraft_days"] for p in initial["periods"]),
                     -initial["D_early_days_total"]/365,
                     initial["outside_minimum"]-initial["std_availability"]/100)
    best_recorded = max([initial_score]+[tuple(step["score"]) for step in run["history"]])
    np.testing.assert_allclose(final_score, best_recorded, atol=1e-12, rtol=0)
    audits.append({"method":metrics["method"], "seed":metrics["seed"],
                   "valid":True, "busy_minima":[p["minimum"] for p in metrics["periods"]],
                   "outside_minimum":metrics["outside_minimum"],
                   "maximum_D_early_days":max(e["latest_start"]-e["start"]
                       for es in schedule.values() for e in es if e["check"] == "D")})
result = {"results_file_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
          "algorithm_file_sha256":hashlib.sha256((ROOT/"savn_early_d_planning.py").read_bytes()).hexdigest(),
          "validation":"Independent daily occupancy and clock replay; best-so-far, boundaries, dependency groups and both targets checked", "runs":audits}
(folder/"serialized-validation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
