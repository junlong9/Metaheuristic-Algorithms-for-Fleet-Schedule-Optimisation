"""Iteration 2 comparison, operational limits, and start schedules."""

import json
from datetime import datetime

TUNED_SHIFT_SETS = (
    (-28, -14, 14, 28),
    (-14, -7, 7, 14),
    (-7, -3, 3, 7),
    (-3, -1, 1, 3),
)
TUNED_ITERATIONS = 400
DECISION_SEEDS = (1, 2, 3)
SCREENING_SEED = 99
RUNTIME_LIMIT_SECONDS = 300
SMOOTHNESS_MARGIN = 0.005

SCREENING_VARIANTS = (
    {"name": "escape_temperature_1.0", "escape_temperature": 1.0},
    {"name": "escape_temperature_2.0", "escape_temperature": 2.0},
    {"name": "escape_cycles_8", "escape_cycles": 8},
    {"name": "escape_cycles_25", "escape_cycles": 25},
    {"name": "plateau_moves_15", "plateau_moves": 15},
    {"name": "plateau_moves_45", "plateau_moves": 45},
    {"name": "polish_iterations_200", "baseline_max_iters": 200},
    {"name": "polish_iterations_800", "baseline_max_iters": 800},
)

import copy

import numpy as np

import vn_priority_based_selection as baseline


def median_day(days):
    ordered = sorted(days)
    mid = len(ordered) // 2

    if len(ordered) % 2 == 1:
        return ordered[mid]

    return (ordered[mid - 1] + ordered[mid] + 1) // 2


def _target_start(event, median, kind):
    earliest = event["earliest_start"]
    latest = event["latest_start"]

    if kind == "bunched":
        return min(max(median, earliest), latest)

    return max(
        (earliest, latest),
        key=lambda day: (abs(day - median), day),
    )


def build_start_schedule(schedule, kind, horizon):
    """Build a start schedule of the same checks and due dates.

    The opening check on each aircraft is pinned to its due date by the
    maintenance replay, so the stagger moves the next check, the first one
    the replay will actually place somewhere else in its start window.
    """

    if kind == "as-loaded":
        return copy.deepcopy(schedule)

    if kind not in ("bunched", "spread"):
        raise ValueError(f"Unknown start schedule: {kind}")

    movable_index = 1
    median = median_day(
        events[movable_index]["start"]
        for events in schedule.values()
    )
    started = {}

    for aircraft, events in schedule.items():
        event = events[movable_index]
        target = _target_start(event, median, kind)
        rebuilt = baseline.rebuild_aircraft_schedule(
            events,
            horizon=horizon,
            event_index=movable_index,
            new_start=target,
        )

        if rebuilt is None:
            raise ValueError(
                f"{aircraft} cannot move check {movable_index + 1} "
                f"to day {target}."
            )

        started[aircraft] = rebuilt

    return started


def load_scenarios(path, base_date):
    if isinstance(base_date, datetime):
        base_date = base_date.date()

    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)

    scenarios = []

    for scenario in document["scenarios"]:
        loaded = {
            "name": scenario["name"],
            "displacement_limit_days": scenario["displacement_limit_days"],
            "dependency_groups": scenario["dependency_groups"],
            "busy_periods": [],
        }

        for period in scenario["busy_periods"]:
            start = datetime.strptime(period["start"], "%Y-%m-%d").date()
            end = datetime.strptime(period["end"], "%Y-%m-%d").date()
            loaded["busy_periods"].append({
                "start_day": (start - base_date).days,
                "end_day": (end - base_date).days,
                "minimum_availability": period["minimum_availability"],
            })

        scenarios.append(loaded)

    return scenarios


def _median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def judge_candidate(
    tuned,
    runs,
    runtime_limit_seconds=RUNTIME_LIMIT_SECONDS,
    smoothness_margin=SMOOTHNESS_MARGIN,
):
    smoothness = [run["smoothness"] for run in runs]
    seconds = [run["seconds"] for run in runs]
    median_smoothness = _median(smoothness)
    median_seconds = _median(seconds)
    ordered_runs = sorted(runs, key=lambda run: run["seconds"])
    median_run = ordered_runs[len(ordered_runs) // 2]
    hold_worst_day = all(run["worst_day"] == 18 for run in runs)
    smoother = tuned["smoothness"] - median_smoothness >= smoothness_margin
    fast_enough = (
        median_run["seconds"] <= runtime_limit_seconds
        and not median_run.get("timed_out", False)
    )

    return {
        "keep": hold_worst_day and smoother and fast_enough,
        "median_smoothness": median_smoothness,
        "spread": max(smoothness) - min(smoothness),
        "median_seconds": median_seconds,
        "holds_worst_day": hold_worst_day,
    }


def run_screening(run_trial, time_limit_seconds, clock, variants=SCREENING_VARIANTS):
    started = clock()
    results = []

    for variant in variants:
        if clock() - started >= time_limit_seconds:
            break

        trial = dict(variant)
        trial["seed"] = SCREENING_SEED
        results.append(run_trial(trial))

    if not results or clock() - started >= time_limit_seconds:
        return results

    best = min(
        results,
        key=lambda item: (-item["worst_day"], item["smoothness"]),
    )
    best_name = best.get("variant", best["name"])
    repeat = {"name": best_name, "seed": DECISION_SEEDS[0]}

    for variant in variants:
        if variant["name"] == best_name:
            repeat.update(variant)
            break

    repeat["name"] = best_name
    repeat["seed"] = DECISION_SEEDS[0]
    results.append(run_trial(repeat))
    return results


def neighbor_is_legal(schedule, neighbor, scenario, as_loaded, horizon):
    if not scenario:
        return True

    candidate = copy.deepcopy(schedule)
    candidate[neighbor["aircraft"]] = neighbor["events"]
    return not operational_breaches(candidate, scenario, as_loaded, horizon)


def operational_breaches(schedule, scenario, as_loaded, horizon):
    breaches = []
    breaches.extend(_displacement_breaches(schedule, scenario, as_loaded))
    breaches.extend(_busy_period_breaches(schedule, scenario, horizon))
    breaches.extend(_dependency_breaches(schedule, scenario, horizon))
    return breaches


def _displacement_breaches(schedule, scenario, as_loaded):
    limit = scenario.get("displacement_limit_days")

    if limit is None:
        return []

    breaches = []

    for aircraft in sorted(as_loaded):
        loaded_events = as_loaded[aircraft]
        moved_events = schedule[aircraft]

        for index, loaded in enumerate(loaded_events):
            moved_days = abs(moved_events[index]["start"] - loaded["start"])

            if moved_days > limit:
                breaches.append(
                    f"{aircraft} check {index + 1} moved "
                    f"{moved_days} days from its as-loaded start"
                )

    return breaches


def _busy_period_breaches(schedule, scenario, horizon):
    periods = scenario.get("busy_periods") or []

    if not periods:
        return []

    availability = baseline.compute_availability(schedule, horizon)
    breaches = []

    for period in periods:
        start_day = period["start_day"]
        end_day = period["end_day"]
        required = period["minimum_availability"]
        worst_day = int(availability[start_day:end_day + 1].min())

        if worst_day < required:
            breaches.append(
                f"busy period days {start_day}-{end_day} "
                f"worst-day availability {worst_day} is below {required}"
            )

    return breaches


def _dependency_breaches(schedule, scenario, horizon):
    groups = scenario.get("dependency_groups") or []

    if not groups:
        return []

    breaches = []

    for group in groups:
        names = group["aircraft"]
        required = group["minimum_available"]
        occupied = np.zeros(horizon + 1, dtype=int)

        for aircraft in names:
            for event in schedule[aircraft]:
                start = event["start"]
                end = start + event["duration"]
                occupied[start:end] += 1

        available = len(names) - occupied
        worst = int(available.min())

        if worst < required:
            breaches.append(
                f"dependency group {', '.join(names)} "
                f"falls to {worst} available"
            )

    return breaches
