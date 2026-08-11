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

CHECK_RULES = {
    "A": {"duration": 14, "interval": 365, "early": 42},
    "B": {"duration": 28, "interval": 365 * 2, "early": 70},
    "C": {"duration": 84, "interval": 365 * 4, "early": 70},
    "D": {"duration": 126, "interval": 365 * 8, "early": 70},
}
CHECK_SEQUENCE = ("A", "B", "A", "C", "A", "B", "A", "D")


# Load Schedule
def load_heavy_schedule(file_path, sheet_name):
    """
    Loads the heavy maintenance forecast from Excel.
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

def get_forecast_horizon(schedule):
    """
    Returns a fixed inclusive day index used to compare all schedules.
    """

    events = [
        event
        for aircraft_events in schedule.values()
        for event in aircraft_events
    ]

    if not events:
        raise ValueError("Schedule must contain at least one maintenance event.")

    return max(
        event["latest_start"] + event["duration"]
        for event in events
    )


def compute_availability(schedule, horizon=None):
    """
    Fast availability computation using a delta-array method.

    Complexity:
    O(days + events)
    instead of
    O(days × aircraft × events)
    """

    num_aircraft = len(schedule)

    if horizon is None:
        horizon = get_forecast_horizon(schedule)

    if horizon < 0:
        raise ValueError("Forecast horizon cannot be negative.")

    # Delta array
    delta = np.zeros(horizon + 2)

    # Record maintenance start/end changes
    for events in schedule.values():

        for event in events:

            start = event["start"]
            end = event["start"] + event["duration"]

            if start < 0 or end > horizon + 1:
                raise ValueError(
                    f"Maintenance event [{start}, {end}) is outside "
                    f"the forecast horizon [0, {horizon + 1})."
                )

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

def score_availability(availability):
    return (
        np.min(availability),
        -np.std(availability),
        np.mean(availability),
    )


def evaluate_schedule(schedule, horizon=None):
    """
    Higher score is better.

    Priority:
    1. Maximise minimum availability
    2. Minimise standard deviation
    3. Maximise average availability
    """

    availability = compute_availability(schedule, horizon)
    return score_availability(availability)


# ============================================================
# FEASIBILITY CHECK
# ============================================================

def is_aircraft_feasible(events, horizon=None):
    sorted_events = sorted(events, key=lambda x: x["start"])

    for event in sorted_events:
        start = event["start"]
        end = start + event["duration"]

        if start < 0:
            return False

        if start < event["earliest_start"]:
            return False

        if start > event["latest_start"]:
            return False

        if horizon is not None and end > horizon + 1:
            return False

    for i in range(len(sorted_events) - 1):
        current_end = (
            sorted_events[i]["start"] +
            sorted_events[i]["duration"]
        )
        next_start = sorted_events[i + 1]["start"]

        if current_end > next_start:
            return False

    return True


def is_feasible(schedule, horizon=None):
    """
    Checks whether the schedule is feasible.

    Conditions:
    - No event starts before day 0
    - Each event stays within its allowed start window
    - Events for the same aircraft do not overlap
    """

    if not schedule:
        return False

    for events in schedule.values():
        if not is_aircraft_feasible(events, horizon):
            return False

    return True


def _initial_due_dates(first_due):
    return {
        "A": first_due,
        "B": first_due + 365,
        "C": first_due + 365 * 3,
        "D": first_due + 365 * 7,
    }


def _update_due_dates(due_dates, check, end):
    reset_checks = {
        "A": ("A",),
        "B": ("A", "B"),
        "C": ("A", "B", "C"),
        "D": ("A", "B", "C", "D"),
    }

    for reset_check in reset_checks[check]:
        due_dates[reset_check] = (
            end + CHECK_RULES[reset_check]["interval"]
        )


def rebuild_aircraft_schedule(
    events,
    horizon,
    event_index=None,
    new_start=None,
):
    """
    Replays one aircraft's maintenance rules after a proposed move.

    Events before event_index must remain unchanged. The selected event is
    moved exactly to new_start. Later starts are retained as preferences and
    clamped into their recalculated legal windows.
    """

    old_events = sorted(events, key=lambda item: item["start"])

    if not old_events:
        return None

    first_due = old_events[0]["latest_start"]
    due_dates = _initial_due_dates(first_due)
    aircraft_available_from = first_due
    rebuilt = []

    for position, old_event in enumerate(old_events):
        check = CHECK_SEQUENCE[position % len(CHECK_SEQUENCE)]
        rule = CHECK_RULES[check]
        due = due_dates[check]
        earliest_start = due - rule["early"]
        legal_start = max(aircraft_available_from, earliest_start)

        if legal_start > due:
            return None

        if event_index is not None and position < event_index:
            if old_event["check"] != check:
                return None

            start = old_event["start"]

            if start < legal_start or start > due:
                return None

        elif event_index is not None and position == event_index:
            if old_events[position]["check"] != check:
                return None

            start = new_start

            if start < legal_start or start > due:
                return None

        else:
            start = min(max(old_event["start"], legal_start), due)

        end = start + rule["duration"]

        if end > horizon + 1:
            return None

        rebuilt.append({
            "check": check,
            "start": start,
            "duration": rule["duration"],
            "earliest_start": earliest_start,
            "latest_start": due,
        })

        _update_due_dates(due_dates, check, end)
        aircraft_available_from = end

    return rebuilt


def is_rule_compliant_schedule(schedule, horizon):
    """
    Validates overlap, legal windows, check substitutions, and due resets.
    """

    if not is_feasible(schedule, horizon):
        return False

    compared_fields = (
        "check",
        "start",
        "duration",
        "earliest_start",
        "latest_start",
    )

    for events in schedule.values():
        if not events:
            return False

        ordered_events = sorted(events, key=lambda item: item["start"])
        replayed = rebuild_aircraft_schedule(
            ordered_events,
            horizon=horizon,
        )

        if replayed is None or len(replayed) != len(ordered_events):
            return False

        for actual, expected in zip(ordered_events, replayed):
            if any(
                actual[field] != expected[field]
                for field in compared_fields
            ):
                return False

    return True


# ============================================================
# GENERATE NEIGHBOURS
# ============================================================

def prioritise_events(schedule, availability):
    """
    Orders events by the worst availability in their active interval.

    Timeline order, aircraft name, and event index provide deterministic
    tie-breaking.
    """

    priorities = []

    for aircraft in sorted(schedule):
        for index, event in enumerate(schedule[aircraft]):
            priorities.append((
                _priority_level(event, availability),
                event["start"],
                aircraft,
                index,
            ))

    priorities.sort()
    return [
        (aircraft, index)
        for _, _, aircraft, index in priorities
    ]


def availability_with_rebuilt_aircraft(
    availability,
    old_events,
    new_events,
):
    candidate = availability.copy()

    for event in old_events:
        start = event["start"]
        end = start + event["duration"]
        candidate[start:end] += 1

    for event in new_events:
        start = event["start"]
        end = start + event["duration"]
        candidate[start:end] -= 1

    return candidate


def _priority_level(event, availability):
    start = event["start"]
    end = start + event["duration"]
    return np.min(availability[start:end])


def generate_neighbors(
    schedule,
    availability,
    horizon,
    current_score,
    shifts=(-1, 1),
):
    """
    Generates neighbouring schedules by shifting maintenance events.

    Each event can only move within:
    [earliest_start, latest_start]
    """

    ordered_events = prioritise_events(schedule, availability)
    priority_levels = []

    for aircraft, index in ordered_events:
        level = _priority_level(schedule[aircraft][index], availability)

        if level not in priority_levels:
            priority_levels.append(level)

    for level in priority_levels:
        improving_neighbors = []

        for aircraft, index in ordered_events:
            events = schedule[aircraft]
            event = events[index]

            if _priority_level(event, availability) != level:
                continue

            old_start = event["start"]

            for shift in shifts:
                new_start = old_start + shift
                rebuilt_events = rebuild_aircraft_schedule(
                    events,
                    horizon=horizon,
                    event_index=index,
                    new_start=new_start,
                )

                if rebuilt_events is None:
                    continue

                candidate_availability = (
                    availability_with_rebuilt_aircraft(
                        availability,
                        events,
                        rebuilt_events,
                    )
                )
                candidate_score = score_availability(
                    candidate_availability
                )

                if candidate_score <= current_score:
                    continue

                improving_neighbors.append({
                    "aircraft": aircraft,
                    "event_index": index,
                    "check": event["check"],
                    "old_start": old_start,
                    "new_start": new_start,
                    "shift": shift,
                    "events": rebuilt_events,
                    "availability": candidate_availability,
                    "score": candidate_score,
                })

        if improving_neighbors:
            return improving_neighbors

    return []


# ============================================================
# SAVN OPTIMISER
# ============================================================

def savn_optimise(initial_schedule, max_iters=400):
    """
    Simple variable-neighbourhood search optimiser.

    It tries larger shifts first, then smaller shifts.
    """

    horizon = get_forecast_horizon(initial_schedule)

    if not is_rule_compliant_schedule(
        initial_schedule,
        horizon,
    ):
        raise ValueError(
            "Initial schedule violates maintenance rules or contains overlap."
        )

    current = copy.deepcopy(initial_schedule)
    availability = compute_availability(current, horizon)
    current_score = score_availability(availability)

    best = copy.deepcopy(current)
    best_score = current_score
    history = []

    # Larger shifts escape local minima
    shift_sets = [
        (-28, 28),
        (-14, 14),
        (-7, 7),
        (-3, 3)
    ]

    print("Initial score:", current_score)
    history.append({
        "iteration": 0,
        "min": np.min(availability),
        "std": np.std(availability),
        "avg": np.mean(availability)
    })

    for iteration in range(max_iters):
        improved = False

        for shifts in shift_sets:
            neighbors = generate_neighbors(
                current,
                availability,
                horizon,
                current_score,
                shifts=shifts,
            )

            if not neighbors:
                continue

            best_neighbor_data = max(
                neighbors,
                key=lambda item: item["score"],
            )

            best_neighbor_score = best_neighbor_data["score"]

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
                current[best_neighbor_data["aircraft"]] = (
                    best_neighbor_data["events"]
                )
                availability = best_neighbor_data["availability"]
                current_score = best_neighbor_score
                improved = True

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

    if not is_rule_compliant_schedule(best, horizon):
        raise RuntimeError(
            "Optimisation produced a rule-invalid or overlapping schedule."
        )

    return best, best_score, history



# ============================================================
# MAIN
# ============================================================

def main():
    schedule, base_date = load_heavy_schedule(FILE_PATH, SHEET_NAME)
    horizon = get_forecast_horizon(schedule)

    original_availability = compute_availability(schedule, horizon)
    original_score = evaluate_schedule(schedule, horizon)
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

    best_availability = compute_availability(best_schedule, horizon)

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
    