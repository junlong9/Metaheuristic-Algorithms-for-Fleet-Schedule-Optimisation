"""Reload serialized schedules under the unmodified computational model."""
import json
from pathlib import Path
from check_windows import ROOT, baseline
import savn_iteration2 as study
import numpy as np

folder = Path(__file__).parent
results = json.loads((folder / "comparison-results.json").read_text())
loaded, base = baseline.load_heavy_schedule(ROOT / baseline.FILE_PATH, baseline.SHEET_NAME)
horizon = baseline.get_forecast_horizon(loaded)
scenario = study.load_scenarios(ROOT / "operational_constraints.json", base)[0]
scenario["busy_periods"] = []
first = (baseline.pd.Timestamp(results["period"][0])-base).days
last = (baseline.pd.Timestamp(results["period"][1])-base).days
original_downtime = sum(e["duration"] for es in loaded.values() for e in es)
record = []
for run in results["runs"]:
    path = folder / f'schedule-{run["method"]}-{run["seed"]}.json'
    schedule = json.loads(path.read_text())
    assert baseline.is_rule_compliant_schedule(schedule, horizon)
    assert not study.operational_breaches(schedule, scenario, loaded, horizon)
    availability = baseline.compute_availability(schedule, horizon)
    assert availability[first:last+1].min() == run["period_minimum"] == 20
    assert availability.min() == run["full_horizon_minimum"]
    assert np.isclose(availability.std(), run["full_horizon_std"])
    assert sum(e["duration"] for es in schedule.values() for e in es) == original_downtime
    assert run["net_period_aircraft_days_change_vs_loaded"] == -run["net_outside_aircraft_days_change_vs_loaded"]
    assert run["net_period_aircraft_days_change_vs_saved_priority"] == -run["net_outside_aircraft_days_change_vs_saved_priority"]
    record.append({"file": path.name, "valid": True, "score_under_original_global_objective": list(map(float, baseline.evaluate_schedule(schedule, horizon)))})
(folder / "serialized-validation.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
