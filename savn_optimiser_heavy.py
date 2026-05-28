import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from export import (
    schedule_to_events_table,
    make_availability_table,
    export_optimised_to_excel
)

from visualisations import (
    plot_comparison
)

FILE_PATH = "heavy_maintenance_forecast.xlsx"
SHEET_NAME = "MxEvents"
OUTPUT_FILE = "optimised_heavy_maintenance_output.xlsx"


# Load Schedule
def load_heavy_schedule(file_path, sheet_name):
    """
    Loads the heavy maintenance forecast from Excel.

    Expected columns:
    - Aircraft
    - Check
    - Start
    - End
    - Duration
    - Earliest_Start
    - Latest_Start
    """

    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = df.columns.str.strip()

    required_columns = [
        "Aircraft",
        "Check",
        "Start",
        "Duration",
        "Earliest_Start",
        "Latest_Start"
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df["Start"] = pd.to_datetime(df["Start"])
    df["Earliest_Start"] = pd.to_datetime(df["Earliest_Start"])
    df["Latest_Start"] = pd.to_datetime(df["Latest_Start"])

    base_date = df["Start"].min()

    df["start"] = (df["Start"] - base_date).dt.days
    df["duration"] = df["Duration"].astype(int)
    df["earliest_start"] = (df["Earliest_Start"] - base_date).dt.days
    df["latest_start"] = (df["Latest_Start"] - base_date).dt.days

    schedule = {}

    for aircraft, group in df.groupby("Aircraft"):
        group = group.sort_values("Start")

        schedule[aircraft] = []

        for _, row in group.iterrows():
            schedule[aircraft].append({
                "check": row["Check"],
                "start": int(row["start"]),
                "duration": int(row["duration"]),
                "earliest_start": int(row["earliest_start"]),
                "latest_start": int(row["latest_start"]),
            })

    return schedule, base_date


# ============================================================
# COMPUTE AVAILABILITY
# ============================================================

def compute_availability(schedule):
    """
    Fast availability computation using a delta-array method.

    Complexity:
    O(days + events)
    instead of
    O(days × aircraft × events)
    """

    num_aircraft = len(schedule)

    last_day = max(
        event["start"] + event["duration"]
        for events in schedule.values()
        for event in events
    )

    # Delta array
    delta = np.zeros(last_day + 2)

    # Record maintenance start/end changes
    for events in schedule.values():

        for event in events:

            start = event["start"]
            end = event["start"] + event["duration"]

            delta[start] -= 1
            delta[end] += 1

    # Cumulative unavailable aircraft
    unavailable = np.cumsum(delta[:-1])

    # Convert to available aircraft
    availability = num_aircraft + unavailable

    return availability


# ============================================================
# EVALUATE SCHEDULE
# ============================================================

def evaluate_schedule(schedule):
    """
    Higher score is better.

    Priority:
    1. Maximise minimum availability
    2. Minimise standard deviation
    3. Maximise average availability
    """

    availability = compute_availability(schedule)

    min_avail = np.min(availability)
    std_avail = np.std(availability)
    avg_avail = np.mean(availability)

    return (min_avail, -std_avail, avg_avail)


# ============================================================
# FEASIBILITY CHECK
# ============================================================

def is_feasible(schedule):
    """
    Checks whether the schedule is feasible.

    Conditions:
    - No event starts before day 0
    - Each event stays within its allowed start window
    - Events for the same aircraft do not overlap
    """

    for aircraft, events in schedule.items():
        sorted_events = sorted(events, key=lambda x: x["start"])

        for event in sorted_events:

            # Cannot start before forecast begins
            if event["start"] < 0:
                return False

            # Must not start before earliest allowed date
            if event["start"] < event["earliest_start"]:
                return False

            # Must not start after latest allowed date
            if event["start"] > event["latest_start"]:
                return False

        # No overlapping events for the same aircraft
        for i in range(len(sorted_events) - 1):
            current_end = sorted_events[i]["start"] + sorted_events[i]["duration"]
            next_start = sorted_events[i + 1]["start"]

            if current_end > next_start:
                return False

    return True


# ============================================================
# GENERATE NEIGHBOURS
# ============================================================

def generate_neighbors(schedule, shifts=(-1, 1)):
    """
    Generates neighbouring schedules by shifting maintenance events.

    Each event can only move within:
    [earliest_start, latest_start]
    """

    neighbors = []

    for aircraft, events in schedule.items():
        for i in range(len(events)):
            old_start = events[i]["start"]

            for shift in shifts:
                candidate = copy.deepcopy(schedule)

                candidate[aircraft][i]["start"] += shift
                new_start = candidate[aircraft][i]["start"]
                event = candidate[aircraft][i]

                # Quick window check
                if new_start < event["earliest_start"]:
                    continue

                if new_start > event["latest_start"]:
                    continue

                # Full feasibility check
                if is_feasible(candidate):
                    neighbors.append({
                        "schedule": candidate,
                        "aircraft": aircraft,
                        "event_index": i,
                        "check": event["check"],
                        "old_start": old_start,
                        "new_start": new_start,
                        "shift": shift,
                    })

    return neighbors


# ============================================================
# SAVN OPTIMISER
# ============================================================

def savn_optimise(initial_schedule, max_iters=400):
    """
    Simple variable-neighbourhood search optimiser.

    It tries larger shifts first, then smaller shifts.
    """

    current = copy.deepcopy(initial_schedule)
    current_score = evaluate_schedule(current)

    best = copy.deepcopy(current)
    best_score = current_score
    history = []

    # Larger shifts are useful to escape local minima
    shift_sets = [
        (-28, 28),
        (-14, 14),
        (-7, 7),
        (-3, 3)
    ]

    print("Initial score:", current_score)
    availability = compute_availability(current)

    history.append({
        "iteration": 0,
        "min": np.min(availability),
        "std": np.std(availability),
        "avg": np.mean(availability)
    })

    for iteration in range(max_iters):
        improved = False

        for shifts in shift_sets:
            neighbors = generate_neighbors(current, shifts=shifts)

            if not neighbors:
                continue

            if len(neighbors) > 200:
                selected_indices = np.random.choice(len(neighbors), size=200, replace=False)
                neighbors = [neighbors[i] for i in selected_indices]

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
                f"check={best_neighbor_data['check']}, "
                f"start from {best_neighbor_data['old_start']} "
                f"to {best_neighbor_data['new_start']}"
            )

            if best_neighbor_score > current_score:
                current = best_neighbor
                current_score = best_neighbor_score
                improved = True

                availability = compute_availability(current)

                history.append({
                    "iteration": iteration + 1,
                    "min": np.min(availability),
                    "std": np.std(availability),
                    "avg": np.mean(availability)
                })

                if current_score > best_score:
                    best = copy.deepcopy(current)
                    best_score = current_score

                print("Improved.")
                break

        if not improved:
            print("\nNo improvement found. Stopping.")
            break

    return best, best_score, history



# ============================================================
# MAIN
# ============================================================

def main():
    schedule, base_date = load_heavy_schedule(FILE_PATH, SHEET_NAME)

    original_availability = compute_availability(schedule)
    original_score = evaluate_schedule(schedule)
    # plot_comparison(original_table, best_table)

    print("\nRunning optimisation...")
    best_schedule, best_score, history = savn_optimise(schedule)
    # print history plot
    history_df = pd.DataFrame(history)

    plt.figure(figsize=(10,6))

    plt.plot(
        history_df["iteration"],
        history_df["std"],
        marker="o"
    )

    plt.xlabel("Iteration")
    plt.ylabel("Standard Deviation")
    plt.title("Standard Deviation vs Iteration")
    plt.grid(True)

    plt.show()

    best_availability = compute_availability(best_schedule)

    print("\nOriginal score:", original_score)
    print("Best score:", best_score)

    original_events = schedule_to_events_table(schedule, base_date)
    best_events = schedule_to_events_table(best_schedule, base_date)

    original_table = make_availability_table(original_availability, base_date)
    best_table = make_availability_table(best_availability, base_date)

    export_optimised_to_excel(
        output_file=OUTPUT_FILE,
        original_events=original_events,
        best_events=best_events,
        original_table=original_table,
        best_table=best_table,
        original_score=original_score,
        best_score=best_score
    )

    plot_comparison(original_table, best_table)

    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    