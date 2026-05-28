import copy
import numpy as np
from schedule_utils import (
    export_to_excel,
    load_schedule,
    compute_availability,
    make_availability_table,
    plot_availability,
)

FILE_PATH = "Simple Random Fleet Plans.xlsx"
SHEET_NAME = "MxEvents"
OUTPUT_FILE = "optimised_availability_output.xlsx"


def evaluate_schedule(schedule):
    # max(neighbors, key=evaluate_schedule) when you do this, prefer min_availbaility, if tied, then larger -standard deviation, if tied, then larger average availability.
    availability = compute_availability(schedule)

    min_avail = np.min(availability)
    std_avail = np.std(availability)
    avg_avail = np.mean(availability)

    # Higher is better
    return (min_avail, -std_avail, avg_avail)


def is_feasible(schedule):
    for aircraft, events in schedule.items():
        sorted_events = sorted(events, key=lambda x: x["start"])

        # Check for negative start times
        for event in sorted_events:
            if event["start"] < 0:
                return False
            
        # Check for overlapping events
        for i in range(len(sorted_events) - 1):
            current_end = sorted_events[i]["start"] + sorted_events[i]["duration"]
            next_start = sorted_events[i + 1]["start"]

            if current_end > next_start:
                return False

    return True

"""
Returns a list of neighboring schedules by shifting the start times of events for each aircraft.
"""
def generate_neighbors(schedule, shifts=(-1, 1)):
    neighbors = []

    for aircraft, events in schedule.items():
        for i in range(len(events)):
            old_start = events[i]["start"]

            for shift in shifts:
                candidate = copy.deepcopy(schedule)
                candidate[aircraft][i]["start"] += shift
                new_start = candidate[aircraft][i]["start"]

                if is_feasible(candidate):
                    neighbors.append({
                        "schedule": candidate,
                        "aircraft": aircraft,
                        "event_index": i,
                        "old_start": old_start,
                        "new_start": new_start,
                        "shift": shift,
                    })

    return neighbors


def savn_optimise(initial_schedule, max_iters=200):
    current = copy.deepcopy(initial_schedule)
    current_score = evaluate_schedule(current)

    best = copy.deepcopy(current)
    best_score = current_score

    shift_sets = [
        (-7, -5, 5, 7),
        (-3, -2, 2, 3),
        (-1, 1),
    ]

    print("Initial score:", current_score)

    for iteration in range(max_iters):
        improved = False

        for shifts in shift_sets:
            neighbors = generate_neighbors(current, shifts=shifts)

            if not neighbors:
                continue
            # Compare candidate schedule with current best schedule.
            best_neighbor_data = max(
                neighbors,
                key=lambda x: evaluate_schedule(x["schedule"])
            )

            best_neighbor = best_neighbor_data["schedule"]
            best_neighbor_score = evaluate_schedule(best_neighbor)

            print(f"\nIteration {iteration + 1}, shifts={shifts}")
            print("Current score:", current_score)
            print("Best neighbor score:", best_neighbor_score)
            print(
                f"Best move: aircraft={best_neighbor_data['aircraft']}, "
                f"start from {best_neighbor_data['old_start']} to {best_neighbor_data['new_start']}"
            )

            if best_neighbor_score > current_score:
                current = best_neighbor
                current_score = best_neighbor_score
                improved = True

                if current_score > best_score:
                    best = copy.deepcopy(current)
                    best_score = current_score

                print("Improved.")
                break

        if not improved:
            print("\nNo improvement found. Stopping.")
            break

    return best, best_score


def main():
    schedule, base_date = load_schedule(FILE_PATH, SHEET_NAME)

    original_availability = compute_availability(schedule)
    original_score = evaluate_schedule(schedule)

    best_schedule, best_score = savn_optimise(schedule)
    best_availability = compute_availability(best_schedule)

    print("\nOriginal score:", original_score)
    print("Best score:", best_score)

    original_table = make_availability_table(original_availability, base_date)
    best_table = make_availability_table(best_availability, base_date)

    export_to_excel(best_table, output_file=OUTPUT_FILE)

    # plot_availability(original_table)
    # plot_availability(best_table)


if __name__ == "__main__":
    main()