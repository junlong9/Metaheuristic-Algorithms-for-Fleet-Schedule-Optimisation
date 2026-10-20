"""Staged hyperparameter study for vn_priority_based_selection."""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import vn_priority_based_selection as opt  # noqa: E402


OUTPUT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = OUTPUT_DIR / "hyperparameter-results.json"
WORKBOOK = ROOT / "heavy_maintenance_forecast.xlsx"
SHEET = "MxEvents"

DEFAULT_SHIFTS = [(-28, 28), (-14, 14), (-7, 7), (-3, 3)]


def generate_neighbors_study(
    schedule,
    availability,
    horizon,
    current_score,
    shifts,
    selection,
):
    """Same proposal rules, with an optional change to early-exit."""

    ordered_events = opt.prioritise_events(schedule, availability)
    priority_levels = []

    for aircraft, index in ordered_events:
        level = opt._priority_level(schedule[aircraft][index], availability)
        if level not in priority_levels:
            priority_levels.append(level)

    collected = []

    for level in priority_levels:
        level_neighbors = []

        for aircraft, index in ordered_events:
            events = schedule[aircraft]
            event = events[index]

            if opt._priority_level(event, availability) != level:
                continue

            old_start = event["start"]

            for shift in shifts:
                new_start = old_start + shift
                rebuilt_events = opt.rebuild_aircraft_schedule(
                    events,
                    horizon=horizon,
                    event_index=index,
                    new_start=new_start,
                )
                if rebuilt_events is None:
                    continue

                candidate_availability = opt.availability_with_rebuilt_aircraft(
                    availability,
                    events,
                    rebuilt_events,
                )
                candidate_score = opt.score_availability(candidate_availability)

                if candidate_score <= current_score:
                    continue

                neighbor = {
                    "aircraft": aircraft,
                    "event_index": index,
                    "check": event["check"],
                    "old_start": old_start,
                    "new_start": new_start,
                    "shift": shift,
                    "events": rebuilt_events,
                    "availability": candidate_availability,
                    "score": candidate_score,
                }

                if selection == "first_improving":
                    return [neighbor]

                level_neighbors.append(neighbor)

        if not level_neighbors:
            continue

        if selection == "first_level":
            return level_neighbors

        collected.extend(level_neighbors)

    return collected


def run_optimise(
    initial_schedule,
    max_iters=400,
    shift_sets=None,
    selection="first_level",
):
    if shift_sets is None:
        shift_sets = DEFAULT_SHIFTS

    horizon = opt.get_forecast_horizon(initial_schedule)

    if not opt.is_rule_compliant_schedule(initial_schedule, horizon):
        raise ValueError("Initial schedule is not rule-compliant.")

    current = copy.deepcopy(initial_schedule)
    availability = opt.compute_availability(current, horizon)
    current_score = opt.score_availability(availability)

    best = copy.deepcopy(current)
    best_score = current_score
    accepted_moves = 0
    last_shift_set = None

    for iteration in range(max_iters):
        improved = False

        for shifts in shift_sets:
            neighbors = generate_neighbors_study(
                current,
                availability,
                horizon,
                current_score,
                shifts=shifts,
                selection=selection,
            )
            if not neighbors:
                continue

            best_neighbor = max(neighbors, key=lambda item: item["score"])
            if best_neighbor["score"] <= current_score:
                continue

            current[best_neighbor["aircraft"]] = best_neighbor["events"]
            availability = best_neighbor["availability"]
            current_score = best_neighbor["score"]
            accepted_moves += 1
            last_shift_set = list(shifts)
            improved = True

            if current_score > best_score:
                best = copy.deepcopy(current)
                best_score = current_score
            break

        if not improved:
            return {
                "best": best,
                "score": best_score,
                "availability": opt.compute_availability(best, horizon),
                "horizon": horizon,
                "stopped_at": iteration,
                "accepted_moves": accepted_moves,
                "last_shift_set": last_shift_set,
                "exhausted": True,
            }

    return {
        "best": best,
        "score": best_score,
        "availability": opt.compute_availability(best, horizon),
        "horizon": horizon,
        "stopped_at": max_iters,
        "accepted_moves": accepted_moves,
        "last_shift_set": last_shift_set,
        "exhausted": False,
    }


def score_tuple(score):
    return [float(score[0]), float(score[1]), float(score[2])]


def trial_record(name, phase, params, result, elapsed, original_score):
    availability = result["availability"]
    return {
        "name": name,
        "phase": phase,
        "params": params,
        "score": score_tuple(result["score"]),
        "min": float(np.min(availability)),
        "std": float(np.std(availability)),
        "avg": float(np.mean(availability)),
        "stopped_at": result["stopped_at"],
        "accepted_moves": result["accepted_moves"],
        "last_shift_set": result["last_shift_set"],
        "exhausted": result["exhausted"],
        "rule_compliant": bool(
            opt.is_rule_compliant_schedule(result["best"], result["horizon"])
        ),
        "elapsed_seconds": elapsed,
        "beat_original": score_tuple(result["score"]) > score_tuple(original_score),
    }


def load_results():
    if not RESULTS_PATH.exists():
        return {"trials": []}
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def save_results(payload):
    RESULTS_PATH.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def already_done(payload, name):
    return any(trial["name"] == name for trial in payload["trials"])


def run_named_trial(payload, schedule, original_score, name, phase, params):
    if already_done(payload, name):
        print(f"skip {name}", flush=True)
        return

    print(f"run  {name}", flush=True)
    started = time.perf_counter()
    result = run_optimise(
        schedule,
        max_iters=params["max_iters"],
        shift_sets=[tuple(item) for item in params["shift_sets"]],
        selection=params["selection"],
    )
    elapsed = time.perf_counter() - started
    record = trial_record(name, phase, params, result, elapsed, original_score)
    payload["trials"].append(record)
    save_results(payload)
    print(
        f"     min={record['min']:.0f} std={record['std']:.6f} "
        f"moves={record['accepted_moves']} stop={record['stopped_at']} "
        f"time={record['elapsed_seconds']:.1f}s",
        flush=True,
    )


def shift_params(shift_sets, max_iters=400, selection="first_level"):
    return {
        "max_iters": max_iters,
        "shift_sets": [list(item) for item in shift_sets],
        "selection": selection,
    }


def build_catalogue():
    trials = []

    trials.append((
        "baseline_default",
        "baseline",
        shift_params(DEFAULT_SHIFTS, max_iters=400),
    ))

    for budget in (5, 10, 20, 40, 80, 160, 400, 800):
        trials.append((
            f"iters_{budget}",
            "max_iters",
            shift_params(DEFAULT_SHIFTS, max_iters=budget),
        ))

    for size in (1, 2, 3, 5, 7, 10, 14, 21, 28, 35, 42, 56, 70):
        trials.append((
            f"single_pm{size}",
            "single_neighbourhood",
            shift_params([( -size, size )], max_iters=400),
        ))

    ladders = {
        "vns_default": DEFAULT_SHIFTS,
        "vns_plus_day": [(-28, 28), (-14, 14), (-7, 7), (-3, 3), (-1, 1)],
        "vns_plus_wide": [(-42, 42), (-28, 28), (-14, 14), (-7, 7), (-3, 3)],
        "vns_plus_month": [(-56, 56), (-28, 28), (-14, 14), (-7, 7), (-3, 3)],
        "vns_early_window": [(-70, 70), (-42, 42), (-28, 28), (-14, 14), (-3, 3)],
        "vns_weekly": [(-28, 28), (-14, 14), (-7, 7), (-1, 1)],
        "vns_fine": [(-14, 14), (-7, 7), (-3, 3), (-1, 1)],
        "vns_coarse": [(-70, 70), (-42, 42), (-28, 28)],
        "vns_geometric": [(-32, 32), (-16, 16), (-8, 8), (-4, 4), (-2, 2)],
        "vns_geometric_plus_day": [
            (-32, 32), (-16, 16), (-8, 8), (-4, 4), (-2, 2), (-1, 1)
        ],
        "vns_three_level": [(-28, 28), (-7, 7), (-1, 1)],
        "vns_two_level_28_7": [(-28, 28), (-7, 7)],
        "vns_two_level_14_3": [(-14, 14), (-3, 3)],
        "vns_monthish": [(-30, 30), (-15, 15), (-7, 7), (-3, 3)],
        "vns_dense": [
            (-28, 28), (-21, 21), (-14, 14), (-7, 7), (-3, 3), (-1, 1)
        ],
        "vns_wide_dense": [
            (-56, 56), (-42, 42), (-28, 28), (-14, 14), (-7, 7), (-3, 3), (-1, 1)
        ],
    }
    for name, shifts in ladders.items():
        trials.append((name, "vns_ladder", shift_params(shifts)))

    trials.append((
        "order_small_first_default",
        "order",
        shift_params(list(reversed(DEFAULT_SHIFTS))),
    ))
    trials.append((
        "order_small_first_weekly",
        "order",
        shift_params([(-1, 1), (-7, 7), (-14, 14), (-28, 28)]),
    ))
    trials.append((
        "order_interleaved",
        "order",
        shift_params([(-14, 14), (-28, 28), (-3, 3), (-7, 7)]),
    ))
    trials.append((
        "order_wide_then_day",
        "order",
        shift_params([(-42, 42), (-1, 1), (-28, 28), (-7, 7)]),
    ))

    richer = {
        "rich_paired_weeks": [
            (-28, -14, 14, 28),
            (-7, -3, 3, 7),
        ],
        "rich_one_union": [
            (-28, -14, -7, -3, 3, 7, 14, 28),
        ],
        "rich_dense_union": [
            (-28, -21, -14, -7, -3, -1, 1, 3, 7, 14, 21, 28),
        ],
        "rich_vns_with_halves": [
            (-28, -14, 14, 28),
            (-14, -7, 7, 14),
            (-7, -3, 3, 7),
            (-3, -1, 1, 3),
        ],
        "asymmetric_left_heavy": [(-28, -14, 14), (-7, -3, 3)],
        "asymmetric_right_heavy": [(-14, 14, 28), (-3, 3, 7)],
    }
    for name, shifts in richer.items():
        trials.append((name, "richer_shifts", shift_params(shifts)))

    for selection in ("all_levels", "first_improving"):
        trials.append((
            f"select_{selection}_default",
            "selection",
            shift_params(DEFAULT_SHIFTS, selection=selection),
        ))

    return trials


def add_follow_up_trials(payload):
    """After the first sweep, refine the best few shift sets."""

    ranked = sorted(
        payload["trials"],
        key=lambda item: (item["score"], -item["elapsed_seconds"]),
        reverse=True,
    )
    seen = set()
    extras = []

    for trial in ranked:
        key = (
            json.dumps(trial["params"]["shift_sets"]),
            trial["params"]["selection"],
        )
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 6:
            break

        stem = trial["name"]
        shifts = trial["params"]["shift_sets"]
        selection = trial["params"]["selection"]

        for budget in (80, 200, 800):
            extras.append((
                f"refine_{stem}_iters_{budget}",
                "refine_budget",
                shift_params(shifts, max_iters=budget, selection=selection),
            ))

        if selection == "first_level":
            extras.append((
                f"refine_{stem}_all_levels",
                "refine_selection",
                shift_params(shifts, selection="all_levels"),
            ))

    return extras


def summarise(payload, original_score, original_stats, started):
    ranked = sorted(payload["trials"], key=lambda item: item["score"], reverse=True)
    payload["workbook"] = str(WORKBOOK)
    payload["original_score"] = score_tuple(original_score)
    payload["original_stats"] = original_stats
    payload["trial_count"] = len(payload["trials"])
    payload["elapsed_seconds"] = time.perf_counter() - started
    payload["best"] = ranked[0] if ranked else None
    payload["top10"] = ranked[:10]
    save_results(payload)


def main():
    schedule, _base_date = opt.load_heavy_schedule(WORKBOOK, SHEET)
    horizon = opt.get_forecast_horizon(schedule)
    original_availability = opt.compute_availability(schedule, horizon)
    original_score = opt.evaluate_schedule(schedule, horizon)
    original_stats = {
        "aircraft": len(schedule),
        "events": sum(len(events) for events in schedule.values()),
        "horizon": horizon,
        "min": float(np.min(original_availability)),
        "std": float(np.std(original_availability)),
        "avg": float(np.mean(original_availability)),
    }

    payload = load_results()
    payload["original_score"] = score_tuple(original_score)
    payload["original_stats"] = original_stats
    started = time.perf_counter()

    print(
        f"Loaded {original_stats['aircraft']} aircraft, "
        f"{original_stats['events']} events, horizon {horizon}. "
        f"Original score {score_tuple(original_score)}",
        flush=True,
    )

    for name, phase, params in build_catalogue():
        run_named_trial(payload, schedule, original_score, name, phase, params)

    for name, phase, params in add_follow_up_trials(payload):
        run_named_trial(payload, schedule, original_score, name, phase, params)

    summarise(payload, original_score, original_stats, started)
    best = payload["best"]
    print(
        f"\nDone. {payload['trial_count']} trials, "
        f"{payload['elapsed_seconds']:.1f}s. Best {best['name']} "
        f"min={best['min']:.0f} std={best['std']:.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
