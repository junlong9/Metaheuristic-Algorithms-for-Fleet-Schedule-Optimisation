"""Check existing busy windows without altering any forecast or search code."""
import ast
import json
import sys
import types
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
tree = ast.parse((ROOT / "vn_priority_based_selection.py").read_text())
tree.body = [
    n for n in tree.body
    if not (isinstance(n, ast.Import) and any(a.name == "matplotlib.pyplot" for a in n.names))
    and not (isinstance(n, ast.ImportFrom) and n.module == "visualisations")
]
baseline = types.ModuleType("vn_priority_based_selection")
exec(compile(tree, str(ROOT / "vn_priority_based_selection.py"), "exec"), baseline.__dict__)
sys.modules[baseline.__name__] = baseline


def main():
    loaded, base = baseline.load_heavy_schedule(ROOT / baseline.FILE_PATH, baseline.SHEET_NAME)
    horizon = baseline.get_forecast_horizon(loaded)
    saved, saved_base = baseline.load_heavy_schedule(ROOT / "optimised_heavy_maintenance_output.xlsx", "Optimised_MxEvents")
    assert saved_base == base
    config = json.loads((ROOT / "operational_constraints.json").read_text())
    results = []
    for period in config["scenarios"][0]["busy_periods"]:
        first = (baseline.pd.Timestamp(period["start"]) - base).days
        last = (baseline.pd.Timestamp(period["end"]) - base).days
        forced = []
        for day in range(first, last + 1):
            aircraft = []
            for name, checks in loaded.items():
                due = checks[0]["latest_start"] + 365 * 7
                if due <= day < due + 56:
                    aircraft.append(name)
            forced.append({"date": (base + timedelta(days=day)).strftime("%Y-%m-%d"), "forced_D": aircraft, "availability_upper_bound_from_D": len(loaded) - len(aircraft)})
        result = {
            "start": period["start"], "end": period["end"], "target": 20,
            "loaded_min": int(baseline.compute_availability(loaded, horizon)[first:last+1].min()),
            "saved_priority_min": int(baseline.compute_availability(saved, horizon)[first:last+1].min()),
            "D_only_window_upper_bound": min(d["availability_upper_bound_from_D"] for d in forced),
            "impossible_days": [d for d in forced if d["availability_upper_bound_from_D"] < 20],
        }
        results.append(result)
    output = {"base_date": str(base.date()), "windows": results,
              "note": "D-only bound is a necessary condition, not a feasibility certificate. Saved priority output is the earlier export, not the latest tuned run."}
    (Path(__file__).parent / "window-check.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
