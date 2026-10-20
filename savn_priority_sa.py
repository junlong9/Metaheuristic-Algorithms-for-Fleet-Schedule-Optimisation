"""Priority-search proposals with simulated-annealing acceptance."""

import copy
import math

import numpy as np

import savn_iteration2 as study
import vn_priority_based_selection as baseline

OUTPUT_FILE = baseline.ROOT / "optimised_priority_sa_output.xlsx"
TRIAL_SEEDS = (99, 100, 101)


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
        current, _, _ = baseline.vn_optimise(
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


def main():
    schedule, base_date = baseline.load_selected_schedule(
        baseline.ROOT / baseline.FILE_PATH,
    )
    horizon = baseline.get_forecast_horizon(schedule)
    original_availability = baseline.compute_availability(schedule, horizon)
    original_score = baseline.evaluate_schedule(schedule, horizon)

    print(
        f"\nRunning priority-based simulated annealing "
        f"({len(TRIAL_SEEDS)} trials)..."
    )
    best_schedule = None
    best_score = None

    for trial, seed in enumerate(TRIAL_SEEDS, start=1):
        print(f"\nTrial {trial}/{len(TRIAL_SEEDS)}, seed={seed}")
        candidate, candidate_score, _ = savn_optimise(
            schedule,
            max_iters=400,
            random_seed=seed,
            initial_temperature=1.0,
            cooling_rate=0.95,
            warm_start=True,
        )
        print(f"Trial {trial} score:", candidate_score)

        if best_score is None or candidate_score > best_score:
            best_schedule = candidate
            best_score = candidate_score

    best_availability = baseline.compute_availability(
        best_schedule,
        horizon,
    )

    print("\nOriginal score:", original_score)
    print("Best score:", best_score)
    print("Completed trials:", len(TRIAL_SEEDS))

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
