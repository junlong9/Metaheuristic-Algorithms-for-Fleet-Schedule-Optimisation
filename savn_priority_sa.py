"""Priority-search proposals with simulated-annealing acceptance."""

import copy
import math
import time

import numpy as np

import savn_iteration2 as study
import savn_priority_based_selection as baseline

OUTPUT_FILE = "optimised_priority_sa_output.xlsx"


def accept_candidate(
    current_score,
    candidate_score,
    temperature,
    rng,
    tightened=False,
):
    if tightened and candidate_score[0] < current_score[0]:
        return False

    if candidate_score > current_score:
        return True

    if temperature <= 0:
        return False

    if candidate_score[0] < current_score[0]:
        loss = current_score[0] - candidate_score[0]
    elif candidate_score[1] < current_score[1]:
        loss = current_score[1] - candidate_score[1]
    else:
        loss = current_score[2] - candidate_score[2]

    return rng.random() < math.exp(-loss / temperature)


def generate_feasible_neighbors(
    schedule,
    availability,
    horizon,
    shifts=(-1, 1),
    scenario=None,
    as_loaded=None,
):
    ordered_events = baseline.prioritise_events(schedule, availability)
    priority_levels = []

    for aircraft, index in ordered_events:
        level = baseline._priority_level(schedule[aircraft][index], availability)

        if level not in priority_levels:
            priority_levels.append(level)

    for level in priority_levels:
        neighbors = []

        for aircraft, index in ordered_events:
            events = schedule[aircraft]
            event = events[index]

            if baseline._priority_level(event, availability) != level:
                continue

            old_start = event["start"]

            for shift in shifts:
                new_start = old_start + shift
                rebuilt_events = baseline.rebuild_aircraft_schedule(
                    events,
                    horizon=horizon,
                    event_index=index,
                    new_start=new_start,
                )

                if rebuilt_events is None:
                    continue

                candidate_availability = (
                    baseline.availability_with_rebuilt_aircraft(
                        availability,
                        events,
                        rebuilt_events,
                    )
                )
                neighbor = {
                    "aircraft": aircraft,
                    "event_index": index,
                    "check": event["check"],
                    "old_start": old_start,
                    "new_start": new_start,
                    "shift": shift,
                    "events": rebuilt_events,
                    "availability": candidate_availability,
                    "score": baseline.score_availability(candidate_availability),
                }

                if scenario and not study.neighbor_is_legal(
                    schedule,
                    neighbor,
                    scenario,
                    as_loaded,
                    horizon,
                ):
                    continue

                neighbors.append(neighbor)

        if neighbors:
            return neighbors

    return []


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

        if accept_candidate(
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
        neighbors.extend(generate_feasible_neighbors(
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


def savn_optimise(
    initial_schedule,
    max_iters=400,
    random_seed=None,
    initial_temperature=1.0,
    cooling_rate=0.95,
    warm_start=True,
):
    horizon = baseline.get_forecast_horizon(initial_schedule)

    if not baseline.is_rule_compliant_schedule(initial_schedule, horizon):
        raise ValueError(
            "Initial schedule violates maintenance rules or contains overlap."
        )

    if warm_start:
        print("\nRunning deterministic baseline warm start...")
        current, _, _ = baseline.savn_optimise(
            initial_schedule,
            max_iters=400,
        )
    else:
        current = copy.deepcopy(initial_schedule)

    availability = baseline.compute_availability(current, horizon)
    current_score = baseline.score_availability(availability)
    best = copy.deepcopy(current)
    best_score = current_score
    history = [{
        "iteration": 0,
        "min": float(availability.min()),
        "std": float(availability.std()),
        "avg": float(availability.mean()),
    }]
    rng = np.random.default_rng(random_seed)
    temperature = initial_temperature
    shift_sets = [
        (-28, 28),
        (-14, 14),
        (-7, 7),
        (-3, 3),
    ]

    print("Initial score:", current_score)

    for iteration in range(max_iters):
        proposed = None
        shift_index = iteration % len(shift_sets)
        ordered_shift_sets = (
            shift_sets[shift_index:] + shift_sets[:shift_index]
        )

        for shifts in ordered_shift_sets:
            neighbors = generate_feasible_neighbors(
                current,
                availability,
                horizon,
                shifts=shifts,
            )

            if not neighbors:
                continue

            proposed = neighbors[int(rng.integers(len(neighbors)))]
            break

        if proposed is None:
            print("\nNo feasible move found. Stopping.")
            break

        print(f"\nIteration {iteration + 1}, shifts={shifts}")
        print(f"Temperature: {temperature:.6f}")
        print("Current score:", current_score)
        print("Candidate score:", proposed["score"])
        print(
            f"Proposed move: aircraft={proposed['aircraft']}, "
            f"check={proposed['check']}, "
            f"start from {proposed['old_start']} "
            f"to {proposed['new_start']}"
        )

        accepted = accept_candidate(
            current_score,
            proposed["score"],
            temperature,
            rng,
        )

        if accepted:
            current[proposed["aircraft"]] = proposed["events"]
            availability = proposed["availability"]
            current_score = proposed["score"]
            history.append({
                "iteration": iteration + 1,
                "min": float(availability.min()),
                "std": float(availability.std()),
                "avg": float(availability.mean()),
            })

            if current_score > best_score:
                best = copy.deepcopy(current)
                best_score = current_score

            print("Accepted.")
        else:
            print("Rejected.")

        temperature *= cooling_rate

    if not baseline.is_rule_compliant_schedule(best, horizon):
        raise RuntimeError(
            "Optimisation produced a rule-invalid or overlapping schedule."
        )

    return best, best_score, history


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


def main():
    schedule, base_date = baseline.load_heavy_schedule(
        baseline.FILE_PATH,
        baseline.SHEET_NAME,
    )
    horizon = baseline.get_forecast_horizon(schedule)
    original_availability = baseline.compute_availability(schedule, horizon)
    original_score = baseline.evaluate_schedule(schedule, horizon)

    print("\nRunning priority-based simulated annealing...")
    best_schedule, best_score, history = basin_hopping_optimise(
        schedule,
        escape_cycles=15,
        plateau_moves=30,
        random_seed=99,
        escape_temperature=1.5,
        baseline_max_iters=400,
    )
    best_availability = baseline.compute_availability(
        best_schedule,
        horizon,
    )

    print("\nOriginal score:", original_score)
    print("Best score:", best_score)
    print("Completed escape cycles:", len(history) - 1)

    original_events = baseline.schedule_to_events_table(
        schedule,
        base_date,
    )
    best_events = baseline.schedule_to_events_table(
        best_schedule,
        base_date,
    )
    original_table = baseline.make_availability_table(
        original_availability,
        base_date,
    )
    best_table = baseline.make_availability_table(
        best_availability,
        base_date,
    )

    baseline.export_optimised_to_excel(
        output_file=OUTPUT_FILE,
        original_events=original_events,
        best_events=best_events,
        original_table=original_table,
        best_table=best_table,
        original_score=original_score,
        best_score=best_score,
    )
    baseline.plot_comparison(original_table, best_table)
    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
