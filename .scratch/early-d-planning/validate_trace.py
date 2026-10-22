"""Replay printed-run histories and independently audit all maintenance clocks."""
import hashlib
import json
from pathlib import Path

import numpy as np

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[1]
NAMES = ("A", "B", "C", "D")
DURATION = dict(zip(NAMES, (14, 28, 84, 126)))
INTERVAL = dict(zip(NAMES, (365, 730, 1460, 2920)))


def audit_schedule(schedule, report):
    h = report["horizon_inclusive"]
    early = dict(zip(NAMES, (42, 70, 70, report["D_early_allowance_days"])))
    occupied = {}
    early_total = 0
    for ac, checks in schedule.items():
        first = checks[0]["latest_start"]
        assert checks[0]["check"] == "A" and checks[0]["start"] == first
        due = dict(zip(NAMES, (first, first+365, first+1095, first+2555)))
        available = first
        a = np.zeros(h+1, dtype=bool)
        for e in checks:
            c, start = e["check"], e["start"]
            end = start+e["duration"]
            assert e["duration"] == DURATION[c]
            assert 0 <= start <= h and start >= available
            assert start >= due[c]-early[c] and start <= min(due.values())
            assert e["earliest_start"] == max(0, due[c]-early[c])
            assert e["latest_start"] == due[c]
            assert all(end <= due[name] for name in NAMES[NAMES.index(c)+1:])
            assert not a[start:min(end, h+1)].any()
            a[start:min(end, h+1)] = True
            if c == "D":
                early_total += due[c]-start
            for name in NAMES[:NAMES.index(c)+1]:
                due[name] = end+INTERVAL[name]
            available = end
        assert min(due.values()) > h
        occupied[ac] = a
    fleet = len(schedule)-sum(occupied.values())
    for group in report["dependency_groups"]:
        group_a = len(group["aircraft"])-sum(occupied[ac] for ac in group["aircraft"])
        assert int(group_a.min()) >= group["minimum_available"]
    return fleet, early_total


def check_metrics(schedule, metrics, report, periods):
    availability, early_total = audit_schedule(schedule, report)
    outside = np.ones(len(availability), dtype=bool)
    deficit = 0
    for index, p in enumerate(periods):
        block = availability[p["start_day"]:p["end_day"]+1]
        outside[p["start_day"]:p["end_day"]+1] = False
        w = metrics["periods"][index]
        expected = int(np.maximum(p["required"]-block, 0).sum())
        assert w["minimum"] == int(block.min())
        assert w["shortage_days"] == int((block < p["required"]).sum())
        assert w["deficit_aircraft_days"] == expected
        deficit += expected
    outside_min = int(availability[outside].min())
    assert metrics["outside_minimum"] == outside_min
    assert metrics["full_horizon_minimum"] == int(availability.min())
    assert metrics["D_early_days_total"] == early_total
    assert np.isclose(metrics["mean_availability"], availability.mean())
    assert np.isclose(metrics["std_availability"], availability.std())
    return (-float(deficit), -early_total/365, outside_min-float(availability.std())/100)


def main():
    audits = []
    for filename in ("trace-priority.json", "trace-annealing-seed3.json"):
        source = FOLDER/filename
        report = json.loads(source.read_text(encoding="utf-8"))
        for run in report["runs"]:
            final, history = run["schedule"], run["history"]
            periods = run["metrics"]["periods"]
            # Reverse stored rebuilds to reconstruct the exact initial schedule,
            # without asking the planner to generate it again.
            current = dict(final)
            for step in history:
                for r in step["rebuilds"]:
                    current[r["aircraft"]] = r["after_checks"]
            for step in reversed(history):
                for r in step["rebuilds"]:
                    assert current[r["aircraft"]] == r["after_checks"]
                    current[r["aircraft"]] = r["before_checks"]
            score = check_metrics(current, run["metrics"]["initial_rebuilt"], report, periods)
            best = score
            for step in history:
                np.testing.assert_allclose(score, step["previous_score"], atol=1e-12, rtol=0)
                for r in step["rebuilds"]:
                    assert current[r["aircraft"]] == r["before_checks"]
                    current[r["aircraft"]] = r["after_checks"]
                    assert r["before_counts"] == {c: sum(e["check"] == c for e in r["before_checks"]) for c in NAMES}
                    assert r["after_counts"] == {c: sum(e["check"] == c for e in r["after_checks"]) for c in NAMES}
                new_score = check_metrics(current, step["current_metrics"], report, periods)
                np.testing.assert_allclose(new_score, step["score"], atol=1e-12, rtol=0)
                assert step["new_best"] == (new_score > best)
                if new_score > best:
                    best = new_score
                np.testing.assert_allclose(best, step["best_score"], atol=1e-12, rtol=0)
                expected = ("improving" if new_score > score else "worse (annealing escape)"
                            if new_score < score else "equal (annealing escape)")
                assert step["acceptance"] == expected
                score = new_score
            final_score = check_metrics(final, run["metrics"], report, periods)
            np.testing.assert_allclose(final_score, best, atol=1e-12, rtol=0)
            text = Path(report["iteration_log"]).read_text(encoding="utf-8")
            for step in history:
                assert f"Iteration {step['iteration']} |" in text
            audits.append({"file": filename, "valid": True,
                           "iterations_replayed": len(history),
                           "results_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                           "busy_minima": [p["minimum"] for p in periods],
                           "outside_minimum": run["metrics"]["outside_minimum"]})
    result = {"validation": "Independent maintenance-clock and daily occupancy replay for every accepted iteration; rebuild continuity, scores, best-so-far and log coverage checked",
              "algorithm_sha256": hashlib.sha256((ROOT/"savn_early_d_planning.py").read_bytes()).hexdigest(),
              "runs": audits}
    (FOLDER/"trace-validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
