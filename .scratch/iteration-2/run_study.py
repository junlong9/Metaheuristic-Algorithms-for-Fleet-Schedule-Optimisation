"""Run the Iteration 2 decision, stagger, constraint, and settings studies.

Each finished trial is written to study-results.json before the next one starts.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import savn_iteration2 as study
import savn_priority_based_selection as baseline
import savn_priority_sa as annealing

RESULTS_PATH = Path(__file__).resolve().parent / "study-results.json"
RUNTIME_LIMIT_SECONDS = study.RUNTIME_LIMIT_SECONDS


def load_results():
    if RESULTS_PATH.exists():
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    return {
        "decision": {"tuned": None, "candidate": [], "tightened": []},
        "stagger": [],
        "constraints": [],
        "sweep": [],
    }


def save_results(results):
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")


def measured(schedule, horizon, started, timed_out=False):
    availability = baseline.compute_availability(schedule, horizon)
    return {
        "worst_day": int(availability.min()),
        "smoothness": float(availability.std()),
        "average": float(availability.mean()),
        "seconds": round(time.perf_counter() - started, 1),
        "timed_out": timed_out,
    }


def run_polish(schedule, horizon, scenario=None, as_loaded=None):
    started = time.perf_counter()
    polished, _, _ = annealing.greedy_polish(
        schedule,
        horizon=horizon,
        max_iters=study.TUNED_ITERATIONS,
        shift_sets=study.TUNED_SHIFT_SETS,
        scenario=scenario,
        as_loaded=as_loaded,
    )
    return polished, measured(polished, horizon, started)


def run_candidate(
    schedule,
    horizon,
    seed,
    tightened=False,
    scenario=None,
    as_loaded=None,
    **settings,
):
    started = time.perf_counter()
    deadline = time.monotonic() + RUNTIME_LIMIT_SECONDS
    best, _, _ = annealing.basin_hopping_optimise(
        schedule,
        escape_cycles=settings.get("escape_cycles", 15),
        plateau_moves=settings.get("plateau_moves", 30),
        random_seed=seed,
        escape_temperature=settings.get("escape_temperature", 1.5),
        baseline_max_iters=settings.get(
            "baseline_max_iters",
            study.TUNED_ITERATIONS,
        ),
        tightened=tightened,
        shift_sets=study.TUNED_SHIFT_SETS,
        scenario=scenario,
        as_loaded=as_loaded,
        deadline=deadline,
    )
    timed_out = time.monotonic() >= deadline
    return best, measured(best, horizon, started, timed_out)


def has_named(rows, name):
    return any(row.get("name") == name for row in rows)


def run_decision(schedule, horizon, results):
    decision = results["decision"]

    if decision["tuned"] is None:
        print("Tuned baseline", flush=True)
        _, record = run_polish(schedule, horizon)
        record["name"] = "tuned-baseline"
        decision["tuned"] = record
        save_results(results)
        print(record, flush=True)

    for seed in study.DECISION_SEEDS:
        name = f"candidate-seed-{seed}"

        if has_named(decision["candidate"], name):
            continue

        print(name, flush=True)
        _, record = run_candidate(schedule, horizon, seed)
        record["name"] = name
        record["seed"] = seed
        decision["candidate"].append(record)
        save_results(results)
        print(record, flush=True)

    for seed in study.DECISION_SEEDS:
        name = f"tightened-seed-{seed}"

        if has_named(decision["tightened"], name):
            continue

        print(name, flush=True)
        _, record = run_candidate(schedule, horizon, seed, tightened=True)
        record["name"] = name
        record["seed"] = seed
        decision["tightened"].append(record)
        save_results(results)
        print(record, flush=True)

    if decision["tuned"] and len(decision["candidate"]) == 3:
        decision["judgement"] = study.judge_candidate(
            decision["tuned"],
            decision["candidate"],
        )
        save_results(results)
        print(decision["judgement"], flush=True)


def run_stagger(schedule, horizon, results):
    for kind in ("as-loaded", "bunched", "spread"):
        name = f"start-{kind}"

        if has_named(results["stagger"], name):
            continue

        started = time.perf_counter()
        start_schedule = study.build_start_schedule(schedule, kind, horizon)
        record = measured(start_schedule, horizon, started)
        record["name"] = name
        record["kind"] = kind
        print(name, record, flush=True)

        _, polished = run_polish(start_schedule, horizon)
        polished["name"] = f"tuned-from-{kind}"
        print(polished["name"], polished, flush=True)

        _, candidate = run_candidate(start_schedule, horizon, seed=1)
        candidate["name"] = f"candidate-from-{kind}"
        candidate["seed"] = 1
        print(candidate["name"], candidate, flush=True)

        results["stagger"].append({
            "name": name,
            "kind": kind,
            "start": record,
            "tuned": polished,
            "candidate": candidate,
        })
        save_results(results)


def run_constraints(schedule, horizon, base_date, results):
    scenarios = study.load_scenarios(
        ROOT / "operational_constraints.json",
        base_date,
    )

    for scenario in scenarios:
        name = f"scenario-{scenario['name']}"

        if has_named(results["constraints"], name):
            continue

        breaches = study.operational_breaches(
            schedule,
            scenario,
            schedule,
            horizon,
        )
        row = {"name": name, "scenario": scenario["name"], "breaches": breaches}

        if breaches:
            row["feasible"] = False
        else:
            polished_schedule, polished = run_polish(
                schedule,
                horizon,
                scenario=scenario,
                as_loaded=schedule,
            )
            row["feasible"] = True
            row["tuned"] = polished
            row["tuned_breaches"] = study.operational_breaches(
                polished_schedule,
                scenario,
                schedule,
                horizon,
            )

        results["constraints"].append(row)
        save_results(results)
        print(name, row["feasible"], flush=True)


def run_sweep(schedule, horizon, results):
    done = {row["name"] for row in results["sweep"]}

    def run_trial(variant):
        name = f"{variant['name']}-seed-{variant['seed']}"

        if name in done:
            return next(row for row in results["sweep"] if row["name"] == name)

        print(name, flush=True)
        _, record = run_candidate(
            schedule,
            horizon,
            seed=variant["seed"],
            escape_temperature=variant.get("escape_temperature", 1.5),
            escape_cycles=variant.get("escape_cycles", 15),
            plateau_moves=variant.get("plateau_moves", 30),
            baseline_max_iters=variant.get(
                "baseline_max_iters",
                study.TUNED_ITERATIONS,
            ),
        )
        record["name"] = name
        record["seed"] = variant["seed"]
        record["variant"] = variant["name"]
        results["sweep"].append(record)
        done.add(name)
        save_results(results)
        print(record, flush=True)
        return record

    study.run_screening(
        run_trial,
        time_limit_seconds=3600,
        clock=time.monotonic,
    )


def main():
    requested = set(sys.argv[1:] or ["decision", "stagger", "constraints", "sweep"])
    schedule, base_date = baseline.load_heavy_schedule(
        baseline.FILE_PATH,
        baseline.SHEET_NAME,
    )
    horizon = baseline.get_forecast_horizon(schedule)
    results = load_results()

    if "decision" in requested:
        run_decision(schedule, horizon, results)

    if "constraints" in requested:
        run_constraints(schedule, horizon, base_date, results)

    if "stagger" in requested:
        run_stagger(schedule, horizon, results)

    if "sweep" in requested:
        run_sweep(schedule, horizon, results)


if __name__ == "__main__":
    main()
