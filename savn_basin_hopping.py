"""Basin-hopping search built on the priority-based annealing proposals."""

import copy
import time

import numpy as np

import savn_iteration2 as study
import savn_priority_sa as annealing
import vn_priority_based_selection as baseline


def select_escape_candidate(
    current_score,
    neighbors,
    temperature,
    rng,
    require_lower_minimum=False,
    tightened=False,
):
    eligible = [
        neighbor
        for neighbor in neighbors
        if (
            neighbor["score"][0] < current_score[0]
            if require_lower_minimum
            else neighbor["score"] <= current_score
        )
    ]

    for index in rng.permutation(len(eligible)):
        candidate = eligible[int(index)]

        if annealing.accept_candidate(
            current_score,
            candidate["score"],
            temperature,
            rng,
            tightened=tightened,
        ):
            return candidate

    return None


DEFAULT_SHIFT_SETS = (
    (-28, 28),
    (-14, 14),
    (-7, 7),
    (-3, 3),
)


def generate_vns_neighbors(
    schedule,
    availability,
    horizon,
    shift_sets=None,
    scenario=None,
    as_loaded=None,
):
    neighbors = []

    for shifts in shift_sets or DEFAULT_SHIFT_SETS:
        neighbors.extend(annealing.generate_feasible_neighbors(
            schedule,
            availability,
            horizon,
            shifts=shifts,
            scenario=scenario,
            as_loaded=as_loaded,
        ))

    return neighbors


def start_vector(schedule):
    return tuple(
        (aircraft, event["check"], event["start"])
        for aircraft in sorted(schedule)
        for event in schedule[aircraft]
    )


def is_tabu_neighbor(schedule, neighbor, forbidden_vector):
    candidate = copy.deepcopy(schedule)
    candidate[neighbor["aircraft"]] = neighbor["events"]
    return start_vector(candidate) == forbidden_vector


def greedy_polish(
    initial_schedule,
    horizon,
    max_iters=400,
    tabu_vectors=(),
    shift_sets=None,
    scenario=None,
    as_loaded=None,
    deadline=None,
):
    if not baseline.is_rule_compliant_schedule(initial_schedule, horizon):
        raise ValueError(
            "Polish schedule violates maintenance rules or contains overlap."
        )

    current = copy.deepcopy(initial_schedule)
    availability = baseline.compute_availability(current, horizon)
    current_score = baseline.score_availability(availability)
    history = [{
        "iteration": 0,
        "min": float(availability.min()),
        "std": float(availability.std()),
        "avg": float(availability.mean()),
    }]
    if shift_sets is None:
        shift_sets = DEFAULT_SHIFT_SETS

    print("Polish initial score:", current_score)

    for iteration in range(max_iters):
        if deadline is not None and time.monotonic() >= deadline:
            print("\nStopped: runtime limit reached.")
            break

        best_neighbor = None

        for shifts in shift_sets:
            neighbors = baseline.generate_neighbors(
                current,
                availability,
                horizon,
                current_score,
                shifts=shifts,
            )

            if not neighbors:
                continue

            legal_neighbors = [
                neighbor
                for neighbor in neighbors
                if not any(
                    is_tabu_neighbor(current, neighbor, forbidden)
                    for forbidden in tabu_vectors
                )
                and study.neighbor_is_legal(
                    current,
                    neighbor,
                    scenario,
                    as_loaded,
                    horizon,
                )
            ]

            if not legal_neighbors:
                continue

            best_neighbor = max(
                legal_neighbors,
                key=lambda item: item["score"],
            )
            break

        if best_neighbor is None:
            print("No polishing improvement found.")
            break

        current[best_neighbor["aircraft"]] = best_neighbor["events"]
        availability = best_neighbor["availability"]
        current_score = best_neighbor["score"]
        history.append({
            "iteration": iteration + 1,
            "min": float(availability.min()),
            "std": float(availability.std()),
            "avg": float(availability.mean()),
        })
        print(
            f"Polish iteration {iteration + 1}, shifts={shifts}: "
            f"{current_score}"
        )

    if not baseline.is_rule_compliant_schedule(current, horizon):
        raise RuntimeError(
            "Polishing produced a rule-invalid or overlapping schedule."
        )

    return current, current_score, history


def basin_hopping_optimise(
    initial_schedule,
    escape_cycles=15,
    plateau_moves=30,
    random_seed=None,
    escape_temperature=1.5,
    baseline_max_iters=400,
    tightened=False,
    shift_sets=None,
    scenario=None,
    as_loaded=None,
    deadline=None,
):
    horizon = baseline.get_forecast_horizon(initial_schedule)

    if not baseline.is_rule_compliant_schedule(initial_schedule, horizon):
        raise ValueError(
            "Initial schedule violates maintenance rules or contains overlap."
        )

    print("\nRunning deterministic baseline warm start...")
    local_schedule, local_score, _ = greedy_polish(
        initial_schedule,
        horizon=horizon,
        max_iters=baseline_max_iters,
        tabu_vectors=(),
        shift_sets=shift_sets,
        scenario=scenario,
        as_loaded=as_loaded,
        deadline=deadline,
    )
    best = copy.deepcopy(local_schedule)
    best_score = local_score
    rng = np.random.default_rng(random_seed)
    history = [{
        "phase": "baseline",
        "cycle": 0,
        "min": float(local_score[0]),
        "std": float(-local_score[1]),
        "avg": float(local_score[2]),
    }]

    for cycle in range(1, escape_cycles + 1):
        if deadline is not None and time.monotonic() >= deadline:
            print("\nStopped: runtime limit reached.")
            break

        print(f"\nEscape cycle {cycle}/{escape_cycles}")
        current = copy.deepcopy(best)
        forbidden = start_vector(best)
        availability = baseline.compute_availability(current, horizon)
        current_score = baseline.score_availability(availability)
        completed_moves = 0

        for move_number in range(1, 2 + plateau_moves):
            if deadline is not None and time.monotonic() >= deadline:
                print("\nStopped: runtime limit reached.")
                break

            neighbors = generate_vns_neighbors(
                current,
                availability,
                horizon,
                shift_sets=shift_sets,
                scenario=scenario,
                as_loaded=as_loaded,
            )
            candidate = select_escape_candidate(
                current_score,
                neighbors,
                escape_temperature,
                rng,
                require_lower_minimum=(move_number == 1),
                tightened=tightened,
            )

            if candidate is None:
                print(
                    f"No accepted escape candidate for move "
                    f"{move_number}."
                )
                break

            print(
                f"Escape move {move_number}: "
                f"aircraft={candidate['aircraft']}, "
                f"check={candidate['check']}, "
                f"start {candidate['old_start']} "
                f"to {candidate['new_start']}"
            )
            print("Score:", current_score, "->", candidate["score"])
            current[candidate["aircraft"]] = candidate["events"]
            availability = candidate["availability"]
            current_score = candidate["score"]
            completed_moves += 1

        if completed_moves == 0:
            continue

        print("\nPolishing escaped schedule with priority search...")
        local_schedule, local_score, _ = greedy_polish(
            current,
            horizon=horizon,
            max_iters=baseline_max_iters,
            tabu_vectors=(forbidden,),
            shift_sets=shift_sets,
            scenario=scenario,
            as_loaded=as_loaded,
            deadline=deadline,
        )
        history.append({
            "phase": "polish",
            "cycle": cycle,
            "min": float(local_score[0]),
            "std": float(-local_score[1]),
            "avg": float(local_score[2]),
        })

        if local_score > best_score:
            best = copy.deepcopy(local_schedule)
            best_score = local_score
            print("New best basin:", best_score)
        else:
            print("Best basin unchanged:", best_score)

    if not baseline.is_rule_compliant_schedule(best, horizon):
        raise RuntimeError(
            "Optimisation produced a rule-invalid or overlapping schedule."
        )

    return best, best_score, history
