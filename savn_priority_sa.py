"""Simulated-annealing / basin-hopping wrapper around priority VNS.

This module imports ``savn_priority_based_selection`` as ``baseline`` and
does not edit that hill-climb. It adds Metropolis acceptance, feasible
(including non-improving) neighbours, classic cooling SA, a tabu-aware
greedy polish, and basin hopping from the protected best-so-far.
"""

from __future__ import annotations

import argparse
import copy
import math
import random
import time

import numpy as np

import savn_priority_based_selection as baseline
from export import (
    export_optimised_to_excel,
    make_availability_table,
    schedule_to_events_table,
)


FILE_PATH = "heavy_maintenance_forecast.xlsx"
SHEET_NAME = "MxEvents"
OUTPUT_FILE = "optimised_priority_sa_output.xlsx"

VNS_SHIFT_SETS = (
    (-28, 28),
    (-14, 14),
    (-7, 7),
    (-3, 3),
)
ESCAPE_SHIFTS = tuple(
    shift for shift_set in VNS_SHIFT_SETS for shift in shift_set
)


def score_tuple(score):
    """Plain Python tuple so JSON and comparisons stay stable."""

    return (float(score[0]), float(score[1]), float(score[2]))


def start_vector(schedule):
    """Hashable restore key: every event start, in aircraft / index order."""

    return tuple(
        (aircraft, index, int(event["start"]))
        for aircraft in sorted(schedule)
        for index, event in enumerate(schedule[aircraft])
    )


def accept_candidate(current_score, candidate_score, temperature, rng):
    """Always accept a better lex score; else staged Metropolis.

    The score is ``(min, -std, avg)``. Loss is taken from the first
    differing component only: ``exp(-loss / T)``.
    """

    current_score = score_tuple(current_score)
    candidate_score = score_tuple(candidate_score)

    if candidate_score > current_score:
        return True
    if temperature <= 0:
        return False
    if candidate_score == current_score:
        return True

    for current_part, candidate_part in zip(current_score, candidate_score):
        if candidate_part != current_part:
            loss = current_part - candidate_part
            if loss <= 0:
                return True
            return rng.random() < math.exp(-loss / temperature)

    return True


def generate_feasible_neighbors(schedule, availability, horizon, shifts):
    """Feasible neighbours at the first non-empty priority level.

    Same rebuild / incremental-availability path as the baseline, but
    every legal rebuild is kept (not only improving moves).
    """

    ordered_events = baseline.prioritise_events(schedule, availability)
    priority_levels = []

    for aircraft, index in ordered_events:
        level = baseline._priority_level(schedule[aircraft][index], availability)
        if level not in priority_levels:
            priority_levels.append(level)

    for level in priority_levels:
        neighbors = []
        seen = set()

        for aircraft, index in ordered_events:
            events = schedule[aircraft]
            event = events[index]
            if baseline._priority_level(event, availability) != level:
                continue

            old_start = event["start"]

            for shift in shifts:
                new_start = old_start + shift
                if new_start == old_start:
                    continue

                rebuilt_events = baseline.rebuild_aircraft_schedule(
                    events,
                    horizon=horizon,
                    event_index=index,
                    new_start=new_start,
                )
                if rebuilt_events is None:
                    continue

                key = (
                    aircraft,
                    index,
                    tuple(
                        (item["check"], item["start"]) for item in rebuilt_events
                    ),
                )
                if key in seen:
                    continue
                seen.add(key)

                candidate_availability = (
                    baseline.availability_with_rebuilt_aircraft(
                        availability,
                        events,
                        rebuilt_events,
                    )
                )
                candidate_score = baseline.score_availability(
                    candidate_availability
                )
                neighbors.append({
                    "aircraft": aircraft,
                    "event_index": index,
                    "check": event["check"],
                    "old_start": old_start,
                    "new_start": new_start,
                    "shift": shift,
                    "events": rebuilt_events,
                    "availability": candidate_availability,
                    "score": score_tuple(candidate_score),
                })

        if neighbors:
            return neighbors

    return []


def _apply_neighbor(schedule, neighbor):
    schedule[neighbor["aircraft"]] = copy.deepcopy(neighbor["events"])
    return (
        neighbor["availability"].copy(),
        score_tuple(neighbor["score"]),
    )


def _candidate_start_vector(schedule, neighbor):
    trial = copy.deepcopy(schedule)
    trial[neighbor["aircraft"]] = neighbor["events"]
    return start_vector(trial)


def select_escape_candidate(
    schedule,
    availability,
    current_score,
    horizon,
    temperature,
    rng,
    require_lower_minimum=False,
    shifts=None,
):
    """Pick one Metropolis-accepted escape neighbour.

    ``require_lower_minimum`` keeps only candidates with min < current min.
    Otherwise only ``score <= current`` (plateau / downhill) is eligible.
    Shift sets are tried in VNS order, then the union, unless ``shifts``
    is supplied.
    """

    current_score = score_tuple(current_score)
    if shifts is None:
        shift_options = list(VNS_SHIFT_SETS) + [ESCAPE_SHIFTS]
    else:
        shift_options = [tuple(shifts)]

    considered = 0
    eligible_count = 0

    for shift_set in shift_options:
        neighbors = generate_feasible_neighbors(
            schedule,
            availability,
            horizon,
            shift_set,
        )
        considered += len(neighbors)

        if require_lower_minimum:
            current_min = current_score[0]
            eligible = [
                neighbor
                for neighbor in neighbors
                if neighbor["score"][0] < current_min
            ]
        else:
            eligible = [
                neighbor
                for neighbor in neighbors
                if score_tuple(neighbor["score"]) <= current_score
            ]

        eligible_count += len(eligible)
        if not eligible:
            continue

        order = list(range(len(eligible)))
        rng.shuffle(order)

        for neighbor_index in order:
            neighbor = eligible[neighbor_index]
            if accept_candidate(
                current_score,
                neighbor["score"],
                temperature,
                rng,
            ):
                availability, current_score = _apply_neighbor(
                    schedule,
                    neighbor,
                )
                return True, schedule, availability, current_score, {
                    "accepted": True,
                    "eligible": eligible_count,
                    "considered": considered,
                    "require_lower_minimum": require_lower_minimum,
                    "aircraft": neighbor["aircraft"],
                    "shift": neighbor["shift"],
                    "score": current_score,
                }

    return False, schedule, availability, current_score, {
        "accepted": False,
        "eligible": eligible_count,
        "considered": considered,
        "require_lower_minimum": require_lower_minimum,
    }


def greedy_polish(
    schedule,
    horizon,
    max_iters=400,
    tabu_vectors=None,
):
    """Improve-only priority search. Optional tabu on full start_vector."""

    tabu_vectors = set(tabu_vectors or [])
    current = copy.deepcopy(schedule)
    availability = baseline.compute_availability(current, horizon)
    current_score = score_tuple(baseline.score_availability(availability))
    history = [{
        "iteration": 0,
        "min": current_score[0],
        "std": -current_score[1],
        "avg": current_score[2],
    }]

    for iteration in range(max_iters):
        improved = False

        for shifts in VNS_SHIFT_SETS:
            neighbors = baseline.generate_neighbors(
                current,
                availability,
                horizon,
                current_score,
                shifts=shifts,
            )
            allowed = []
            for neighbor in neighbors:
                if score_tuple(neighbor["score"]) <= current_score:
                    continue
                if tabu_vectors and (
                    _candidate_start_vector(current, neighbor) in tabu_vectors
                ):
                    continue
                allowed.append(neighbor)

            if not allowed:
                continue

            best_neighbor = max(allowed, key=lambda item: item["score"])
            best_neighbor_score = score_tuple(best_neighbor["score"])
            current[best_neighbor["aircraft"]] = best_neighbor["events"]
            availability = best_neighbor["availability"]
            current_score = best_neighbor_score
            improved = True
            history.append({
                "iteration": iteration + 1,
                "min": current_score[0],
                "std": -current_score[1],
                "avg": current_score[2],
                "shifts": shifts,
            })
            print(
                f"Polish iter {iteration + 1} shifts={shifts} "
                f"score={current_score}"
            )
            break

        if not improved:
            print(f"Polish stopped after {iteration} improving iterations.")
            break

    return current, current_score, availability, history


def savn_optimise(
    initial_schedule,
    max_iters=400,
    t0=1.0,
    cooling_rate=0.95,
    warm_start=True,
    random_seed=42,
    baseline_max_iters=None,
):
    """Classic cooling SA. Optional baseline hill-climb warm start.

    Rotates the VNS shift sets, picks one random feasible neighbour,
    applies staged Metropolis, then ``T *= cooling_rate``.
    """

    horizon = baseline.get_forecast_horizon(initial_schedule)
    if not baseline.is_rule_compliant_schedule(initial_schedule, horizon):
        raise ValueError(
            "Initial schedule violates maintenance rules or contains overlap."
        )

    rng = random.Random(random_seed)
    polish_iters = (
        max_iters if baseline_max_iters is None else baseline_max_iters
    )

    if warm_start:
        print(
            f"Classic SA warm-start via baseline hill-climb "
            f"(max_iters={polish_iters})"
        )
        current, current_score, _history = baseline.savn_optimise(
            initial_schedule,
            max_iters=polish_iters,
        )
        current_score = score_tuple(current_score)
    else:
        current = copy.deepcopy(initial_schedule)
        current_score = score_tuple(
            baseline.evaluate_schedule(current, horizon)
        )

    availability = baseline.compute_availability(current, horizon)
    best = copy.deepcopy(current)
    best_score = current_score
    temperature = float(t0)

    print(
        f"Classic SA start score={current_score} T0={temperature} "
        f"cooling={cooling_rate} seed={random_seed}"
    )

    history = [{
        "iteration": 0,
        "min": current_score[0],
        "std": -current_score[1],
        "avg": current_score[2],
        "temperature": temperature,
    }]

    for iteration in range(max_iters):
        shifts = VNS_SHIFT_SETS[iteration % len(VNS_SHIFT_SETS)]
        neighbors = generate_feasible_neighbors(
            current,
            availability,
            horizon,
            shifts,
        )
        if neighbors:
            neighbor = neighbors[rng.randrange(len(neighbors))]
            if accept_candidate(
                current_score,
                neighbor["score"],
                temperature,
                rng,
            ):
                availability, current_score = _apply_neighbor(current, neighbor)
                history.append({
                    "iteration": iteration + 1,
                    "min": current_score[0],
                    "std": -current_score[1],
                    "avg": current_score[2],
                    "temperature": temperature,
                    "shifts": shifts,
                })
                if current_score > best_score:
                    best = copy.deepcopy(current)
                    best_score = current_score
                    print(
                        f"SA iter {iteration + 1} new best {best_score} "
                        f"T={temperature:.5f}"
                    )

        temperature *= cooling_rate

    if not baseline.is_rule_compliant_schedule(best, horizon):
        raise RuntimeError(
            "Classic SA produced a rule-invalid or overlapping schedule."
        )

    return best, best_score, {
        "horizon": horizon,
        "best_score": best_score,
        "history": history,
        "params": {
            "max_iters": max_iters,
            "t0": t0,
            "cooling_rate": cooling_rate,
            "warm_start": warm_start,
            "random_seed": random_seed,
        },
    }


def basin_hopping_optimise(
    initial_schedule,
    escape_cycles=15,
    plateau_moves=30,
    escape_temperature=1.5,
    baseline_max_iters=400,
    random_seed=99,
    deadline_monotonic=None,
):
    """Greedy polish, then hops from the protected best-so-far.

    Each cycle forbids the best start vector, forces one floor-drop,
    walks ``plateau_moves`` Metropolis steps, polishes with that tabu,
    and keeps the lexicographic best.
    """

    horizon = baseline.get_forecast_horizon(initial_schedule)
    if not baseline.is_rule_compliant_schedule(initial_schedule, horizon):
        raise ValueError(
            "Initial schedule violates maintenance rules or contains overlap."
        )

    rng = random.Random(random_seed)

    print(
        f"Warm-start greedy polish (max_iters={baseline_max_iters}) "
        f"on fixed horizon={horizon}"
    )
    current, current_score, _, polish_history = greedy_polish(
        initial_schedule,
        horizon,
        max_iters=baseline_max_iters,
    )
    if not baseline.is_rule_compliant_schedule(current, horizon):
        raise RuntimeError("Warm-start polish produced an invalid schedule.")

    best = copy.deepcopy(current)
    best_score = current_score
    cycle_minima = [current_score[0]]
    cycle_details = [{
        "cycle": 0,
        "kind": "warm_start",
        "score": current_score,
        "polish_iters": max(0, len(polish_history) - 1),
    }]

    print(f"Warm-start score: {current_score}")

    skipped_cycles = 0
    timed_out = False

    for cycle in range(1, escape_cycles + 1):
        if (
            deadline_monotonic is not None
            and time.monotonic() >= deadline_monotonic
        ):
            timed_out = True
            print(f"Deadline reached before escape cycle {cycle}.")
            break

        # Always hop from the protected best-so-far, not the last basin.
        escaped = copy.deepcopy(best)
        escaped_availability = baseline.compute_availability(escaped, horizon)
        escaped_score = score_tuple(
            baseline.score_availability(escaped_availability)
        )
        forbidden = {start_vector(best)}

        accepted, escaped, escaped_availability, escaped_score, first_info = (
            select_escape_candidate(
                escaped,
                escaped_availability,
                escaped_score,
                horizon,
                escape_temperature,
                rng,
                require_lower_minimum=True,
            )
        )
        if not accepted:
            skipped_cycles += 1
            cycle_details.append({
                "cycle": cycle,
                "kind": "skipped_first_escape",
                "first_escape": first_info,
            })
            print(
                f"Cycle {cycle}: first floor-drop escape failed "
                f"(eligible={first_info['eligible']}). Skipping."
            )
            continue

        extra_accepted = 0
        extra_infos = []
        for extra in range(plateau_moves):
            shifts = VNS_SHIFT_SETS[extra % len(VNS_SHIFT_SETS)]
            extra_ok, escaped, escaped_availability, escaped_score, extra_info = (
                select_escape_candidate(
                    escaped,
                    escaped_availability,
                    escaped_score,
                    horizon,
                    escape_temperature,
                    rng,
                    require_lower_minimum=False,
                    shifts=shifts,
                )
            )
            extra_infos.append(extra_info)
            if extra_ok:
                extra_accepted += 1

        escaped_min = escaped_score[0]
        polished, polished_score, _, polished_history = greedy_polish(
            escaped,
            horizon,
            max_iters=baseline_max_iters,
            tabu_vectors=forbidden,
        )
        if not baseline.is_rule_compliant_schedule(polished, horizon):
            raise RuntimeError(
                f"Cycle {cycle} polish produced an invalid schedule."
            )

        cycle_minima.append(polished_score[0])
        improved_best = polished_score > best_score
        if improved_best:
            best = copy.deepcopy(polished)
            best_score = polished_score

        detail = {
            "cycle": cycle,
            "kind": "polished",
            "escaped_min": escaped_min,
            "score": polished_score,
            "improved_best": improved_best,
            "first_escape": first_info,
            "extra_accepted": extra_accepted,
            "plateau_moves": plateau_moves,
            "extra_moves": extra_infos,
            "polish_iters": max(0, len(polished_history) - 1),
        }
        cycle_details.append(detail)
        print(
            f"Cycle {cycle}: escaped_min={escaped_min} "
            f"polished={polished_score} best={best_score}"
        )

    if not baseline.is_rule_compliant_schedule(best, horizon):
        raise RuntimeError(
            "Optimisation produced a rule-invalid or overlapping schedule."
        )

    result = {
        "horizon": horizon,
        "warm_start_score": cycle_details[0]["score"],
        "best_score": best_score,
        "cycle_minima": cycle_minima,
        "cycle_details": cycle_details,
        "skipped_cycles": skipped_cycles,
        "timed_out": timed_out,
        "params": {
            "escape_cycles": escape_cycles,
            "plateau_moves": plateau_moves,
            "escape_temperature": escape_temperature,
            "baseline_max_iters": baseline_max_iters,
            "random_seed": random_seed,
        },
    }
    return best, best_score, result


def export_result(
    output_file,
    original_schedule,
    best_schedule,
    original_score,
    best_score,
    base_date,
    horizon,
):
    original_availability = baseline.compute_availability(
        original_schedule,
        horizon,
    )
    best_availability = baseline.compute_availability(best_schedule, horizon)
    export_optimised_to_excel(
        output_file=output_file,
        original_events=schedule_to_events_table(
            original_schedule,
            base_date,
        ),
        best_events=schedule_to_events_table(best_schedule, base_date),
        original_table=make_availability_table(
            original_availability,
            base_date,
        ),
        best_table=make_availability_table(best_availability, base_date),
        original_score=original_score,
        best_score=best_score,
    )
    print(f"Output saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Priority SA / basin-hopping optimiser.",
    )
    parser.add_argument(
        "--mode",
        choices=("basin", "sa"),
        default="basin",
    )
    parser.add_argument("--escape-cycles", type=int, default=15)
    parser.add_argument("--plateau-moves", type=int, default=30)
    parser.add_argument("--escape-moves", type=int, default=None,
                        help="Deprecated alias for --plateau-moves.")
    parser.add_argument("--escape-temperature", type=float, default=1.5)
    parser.add_argument("--baseline-max-iters", type=int, default=400)
    parser.add_argument("--random-seed", type=int, default=99)
    parser.add_argument("--max-iters", type=int, default=400)
    parser.add_argument("--t0", type=float, default=1.0)
    parser.add_argument("--cooling-rate", type=float, default=0.95)
    parser.add_argument("--warm-start", action="store_true", default=True)
    parser.add_argument("--no-warm-start", action="store_false",
                        dest="warm_start")
    parser.add_argument("--file-path", default=FILE_PATH)
    parser.add_argument("--sheet-name", default=SHEET_NAME)
    parser.add_argument("--output-file", default=OUTPUT_FILE)
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()

    plateau_moves = (
        args.escape_moves if args.escape_moves is not None
        else args.plateau_moves
    )

    schedule, base_date = baseline.load_heavy_schedule(
        args.file_path,
        args.sheet_name,
    )
    horizon = baseline.get_forecast_horizon(schedule)
    original_score = score_tuple(
        baseline.evaluate_schedule(schedule, horizon)
    )
    print("Original score:", original_score)
    print(
        f"Fingerprint: aircraft={len(schedule)} "
        f"events={sum(len(events) for events in schedule.values())} "
        f"horizon={horizon} base_date={base_date}"
    )

    started = time.monotonic()
    if args.mode == "sa":
        best_schedule, best_score, result = savn_optimise(
            schedule,
            max_iters=args.max_iters,
            t0=args.t0,
            cooling_rate=args.cooling_rate,
            warm_start=args.warm_start,
            random_seed=args.random_seed,
            baseline_max_iters=args.baseline_max_iters,
        )
    else:
        best_schedule, best_score, result = basin_hopping_optimise(
            schedule,
            escape_cycles=args.escape_cycles,
            plateau_moves=plateau_moves,
            escape_temperature=args.escape_temperature,
            baseline_max_iters=args.baseline_max_iters,
            random_seed=args.random_seed,
        )

    elapsed = time.monotonic() - started
    compliant = baseline.is_rule_compliant_schedule(best_schedule, horizon)
    print("Best score:", best_score)
    print("Rule compliant:", compliant)
    print(f"Elapsed seconds: {elapsed:.3f}")
    if "cycle_minima" in result:
        print("Cycle minima:", result["cycle_minima"])

    if not args.no_export:
        export_result(
            args.output_file,
            schedule,
            best_schedule,
            original_score,
            best_score,
            base_date,
            horizon,
        )


if __name__ == "__main__":
    main()
