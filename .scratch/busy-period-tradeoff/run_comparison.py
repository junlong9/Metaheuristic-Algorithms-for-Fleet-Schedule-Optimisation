"""Isolated period-objective experiment; published search modules stay unchanged.

Use the existing priority polish and basin-hopping control flow, replacing only
their in-process score and common proposal adapters for a new busy-period goal.
The target is soft during repair and mandatory for a reported successful plan.
"""
import contextlib
import copy
import json
import sys
import time
from pathlib import Path

from check_windows import ROOT, baseline
import numpy as np
import savn_basin_hopping as basin
import savn_iteration2 as study

OUT = Path(__file__).parent
TARGET = 20
SECONDS = 60
CANDIDATE_WARM_ITERATIONS = 80


def main():
    loaded, base = baseline.load_heavy_schedule(ROOT / baseline.FILE_PATH, baseline.SHEET_NAME)
    horizon = baseline.get_forecast_horizon(loaded)
    first = (baseline.pd.Timestamp("2033-09-14") - base).days
    last = (baseline.pd.Timestamp("2033-10-13") - base).days
    mask = np.ones(horizon + 1, dtype=bool)
    mask[first:last+1] = False
    scenario = study.load_scenarios(ROOT / "operational_constraints.json", base)[0]
    scenario["busy_periods"] = []
    assert not study.operational_breaches(loaded, scenario, loaded, horizon)
    assert baseline.is_rule_compliant_schedule(loaded, horizon)

    def score(a):
        window = a[first:last+1]
        deficit = float(np.maximum(TARGET - window, 0).sum())
        # std < 100, so an extra aircraft outside dominates smoothness.
        return (min(float(window.min()), TARGET), -deficit,
                float(a[mask].min()) - float(a.std()) / 100)

    def priority(event, a):
        start = max(event["start"], first)
        end = min(event["start"] + event["duration"], last + 1)
        # During repair, checks in the lowest-availability target days go first.
        if a[first:last+1].min() < TARGET:
            return float(a[start:end].min()) if start < end else 100.0
        return float(a[event["start"]:event["start"]+event["duration"]].min())

    def proposals(schedule, availability, forecast, shifts=(-1, 1),
                  scenario=None, as_loaded=None, improving=False, current_score=None):
        ordered = baseline.prioritise_events(schedule, availability)
        levels = sorted({priority(schedule[ac][idx], availability) for ac, idx in ordered})
        for level in levels:
            neighbors = []
            for aircraft, index in ordered:
                events = schedule[aircraft]
                event = events[index]
                if priority(event, availability) != level:
                    continue
                for shift in shifts:
                    new_start = event["start"] + shift
                    rebuilt = baseline.rebuild_aircraft_schedule(events, forecast, index, new_start)
                    if rebuilt is None:
                        continue
                    a = baseline.availability_with_rebuilt_aircraft(availability, events, rebuilt)
                    candidate = {"aircraft": aircraft, "event_index": index,
                                 "check": event["check"], "old_start": event["start"],
                                 "new_start": new_start, "shift": shift, "events": rebuilt,
                                 "availability": a, "score": score(a)}
                    if improving and candidate["score"] <= current_score:
                        continue
                    if not study.neighbor_is_legal(schedule, candidate, scenario, as_loaded, forecast):
                        continue
                    neighbors.append(candidate)
            if neighbors:
                return neighbors
        return []

    def improvements(schedule, availability, forecast, current_score, shifts=(-1, 1)):
        return proposals(schedule, availability, forecast, shifts, scenario, loaded,
                         improving=True, current_score=current_score)

    baseline.score_availability = score
    baseline._priority_level = priority
    baseline.generate_neighbors = improvements
    basin.annealing.generate_feasible_neighbors = proposals

    loaded_a = baseline.compute_availability(loaded, horizon)
    saved_priority, saved_base = baseline.load_heavy_schedule(
        ROOT / "optimised_heavy_maintenance_output.xlsx", "Optimised_MxEvents")
    assert saved_base == base
    saved_a = baseline.compute_availability(saved_priority, horizon)

    def metrics(schedule):
        a = baseline.compute_availability(schedule, horizon)
        window = a[first:last+1]
        before = a[first-30:first]
        after = a[last+1:last+31]
        outside_loss = np.maximum(loaded_a[mask] - a[mask], 0)
        outside_gain = np.maximum(a[mask] - loaded_a[mask], 0)
        return {"target_met": bool(window.min() >= TARGET),
                "period_minimum": int(window.min()),
                "period_deficit_aircraft_days": int(np.maximum(TARGET-window, 0).sum()),
                "period_shortage_days": int((window < TARGET).sum()),
                "period_mean": float(window.mean()),
                "outside_minimum": int(a[mask].min()), "full_horizon_minimum": int(a.min()),
                "30_days_before_minimum": int(before.min()),
                "30_days_after_minimum": int(after.min()),
                "outside_aircraft_days_lost_vs_loaded": int(outside_loss.sum()),
                "outside_aircraft_days_gained_vs_loaded": int(outside_gain.sum()),
                "net_outside_aircraft_days_change_vs_loaded": int((a[mask]-loaded_a[mask]).sum()),
                "net_period_aircraft_days_change_vs_loaded": int((window-loaded_a[first:last+1]).sum()),
                "net_period_aircraft_days_change_vs_saved_priority": int((window-saved_a[first:last+1]).sum()),
                "net_outside_aircraft_days_change_vs_saved_priority": int((a[mask]-saved_a[mask]).sum()),
                "largest_daily_drop_30_days_before_vs_loaded": int(np.maximum(loaded_a[first-30:first]-before, 0).max()),
                "largest_daily_drop_30_days_after_vs_loaded": int(np.maximum(loaded_a[last+1:last+31]-after, 0).max()),
                "full_horizon_std": float(a.std()), "full_horizon_mean": float(a.mean()),
                "maximum_displacement_days": max(abs(e["start"]-loaded[ac][i]["start"])
                    for ac, events in schedule.items() for i, e in enumerate(events)),
                "maintenance_compliant": bool(baseline.is_rule_compliant_schedule(schedule, horizon)),
                "other_operational_breaches": study.operational_breaches(schedule, scenario, loaded, horizon)}

    document = {"period": ["2033-09-14", "2033-10-13"], "target": TARGET,
                "trial_limit_seconds": SECONDS,
                "scope": "Availability outside the target may fall; legal maintenance rules, 70-day as-loaded displacement and both loose dependency groups (2 of 4) remain hard.",
                "objective": "Maximise busy-period minimum capped at 20, minimise aircraft-day shortage below 20, maximise outside minimum minus std/100.",
                "priority": "Worst target days first until repaired, then original worst-day ordering.",
                "candidate_warm_iterations": CANDIDATE_WARM_ITERATIONS,
                "candidate_settings_note": "80 warm-start/polish iterations allow actual escapes within 60 seconds; deterministic priority retains its 400-iteration cap. This is an exploratory time-budget comparison, not a definitive method ranking.",
                "warning": "Exploratory adaptation, not a rerun of the old global objective. 60-second budget is shorter than prior 300-second decision study.",
                "as_loaded": metrics(loaded), "saved_priority_export": metrics(saved_priority), "runs": []}

    previous_path = OUT / "comparison-results.json"
    if previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        if not previous.get("candidate_warm_iterations"):
            (OUT / "pilot-warm-only-results.json").write_text(json.dumps(previous, indent=2), encoding="utf-8")
        for record in previous["runs"]:
            if record["method"] == "priority-period-objective":
                schedule = json.loads((OUT / "schedule-priority-period-objective-None.json").read_text())
                record.update(metrics(schedule))
                document["runs"].append(record)

    def persist():
        (OUT / "comparison-results.json").write_text(json.dumps(document, indent=2), encoding="utf-8")

    persist()
    for name, seed in [("priority-period-objective", None)] + [("basin-hopping-period-objective", s) for s in (1, 2, 3)]:
        if seed is None and document["runs"]:
            continue
        print(f"Starting {name}, seed={seed}", flush=True)
        started = time.monotonic()
        deadline = started + SECONDS
        with (OUT / f"{name}-{seed}.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            if seed is None:
                schedule, _, history = basin.greedy_polish(
                    loaded, horizon, max_iters=study.TUNED_ITERATIONS,
                    shift_sets=study.TUNED_SHIFT_SETS, scenario=scenario,
                    as_loaded=loaded, deadline=deadline)
            else:
                schedule, _, history = basin.basin_hopping_optimise(
                    loaded, random_seed=seed, shift_sets=study.TUNED_SHIFT_SETS,
                    baseline_max_iters=CANDIDATE_WARM_ITERATIONS,
                    scenario=scenario, as_loaded=loaded, deadline=deadline)
        elapsed = time.monotonic() - started
        record = {"method": name, "seed": seed, "seconds": round(elapsed, 3),
                  "timed_out": elapsed >= SECONDS, "history_entries": len(history),
                  "escape_moves": sum(1 for line in (OUT / f"{name}-{seed}.log").read_text().splitlines() if line.startswith("Escape move ")),
                  "polished_escape_cycles": sum(1 for step in history if step.get("phase") == "polish"),
                  **metrics(schedule)}
        assert record["maintenance_compliant"] and not record["other_operational_breaches"]
        assert np.isclose(record["full_horizon_mean"], document["as_loaded"]["full_horizon_mean"])
        (OUT / f"schedule-{name}-{seed}.json").write_text(json.dumps(schedule, indent=2), encoding="utf-8")
        document["runs"].append(record)
        persist()
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
