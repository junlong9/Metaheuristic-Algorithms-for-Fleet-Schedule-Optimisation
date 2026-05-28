import pandas as pd
import numpy as np
from datetime import timedelta


INPUT_FILE = "Simple Random Fleet Plans.xlsx"
INPUT_SHEET = "MxEvents"

OUTPUT_FILE = "heavy_maintenance_forecast.xlsx"

FLEET_SIZE = 24         
FORECAST_YEARS = 12
RANDOM_SEED = 42

# The script will preserve the first start date for existing aircraft
# if those aircraft already exist in your dataset.


# ============================================================
# CHECK RULES
# ============================================================

CHECK_RULES = {
    "A": {
        "duration_days": 14,          # 2 weeks
        "interval_days": 365,         # 1 year
        "early_days": 42              # 6 weeks early
    },
    "B": {
        "duration_days": 28,          # 4 weeks
        "interval_days": 365 * 2,     # 2 years
        "early_days": 70              # 10 weeks early
    },
    "C": {
        "duration_days": 84,          # 12 weeks
        "interval_days": 365 * 4,     # 4 years
        "early_days": 70              # 10 weeks early
    },
    "D": {
        "duration_days": 126,         # 18 weeks
        "interval_days": 365 * 8,     # 8 years
        "early_days": 70              # 10 weeks early
    }
}


def load_existing_first_starts(input_file, sheet_name):
    """
    Reads the existing maintenance dataset and extracts the first start date
    for each aircraft.

    Expected columns:
    - Aircraft
    - Start
    """

    df = pd.read_excel(input_file, sheet_name=sheet_name)
    df.columns = df.columns.str.strip()

    if "Aircraft" not in df.columns:
        raise ValueError("Input file must contain an 'Aircraft' column.")

    if "Start" not in df.columns:
        raise ValueError("Input file must contain a 'Start' column.")

    df["Start"] = pd.to_datetime(df["Start"])

    first_starts = (
        df.sort_values("Start")
        .groupby("Aircraft")["Start"]
        .first()
        .to_dict()
    )

    return first_starts


# ============================================================
# CREATE AIRCRAFT LIST
# ============================================================

def create_aircraft_first_starts(existing_first_starts, fleet_size):
    """
    Preserves existing aircraft first start dates.
    If fleet_size is larger than the existing number of aircraft,
    new aircraft are created with staggered first start dates.
    """

    np.random.seed(RANDOM_SEED)

    aircraft_names = list(existing_first_starts.keys())

    if len(aircraft_names) == 0:
        base_date = pd.Timestamp("2026-01-01")
    else:
        base_date = min(existing_first_starts.values())

    aircraft_first_starts = {}

    # Preserve existing aircraft first start dates
    for aircraft in aircraft_names[:fleet_size]:
        aircraft_first_starts[aircraft] = existing_first_starts[aircraft]

    # Add extra aircraft if needed
    existing_count = len(aircraft_first_starts)

    for i in range(existing_count + 1, fleet_size + 1):
        aircraft_name = f"Aircraft {i}"

        random_offset = np.random.randint(0, 730)

        first_start = base_date + timedelta(days=random_offset)

        aircraft_first_starts[aircraft_name] = first_start

    return aircraft_first_starts


# ============================================================
# GENERATE MAINTENANCE EVENTS
# ============================================================

def generate_aircraft_schedule(aircraft, first_start, forecast_end):
    """
    Generates an A/B/C/D maintenance schedule for one aircraft using due dates.

    This version avoids artificially compressing the cycle by always scheduling
    at the earliest allowed start date.

    Logic:
    - A is due 1 year after the end of the last A/B/C/D check
    - B is due 2 years after the end of the last B/C/D check
    - C is due 4 years after the end of the last C/D check
    - D is due 8 years after the end of the last D check

    Larger checks reset smaller checks:
    - B resets A and B
    - C resets A, B, and C
    - D resets A, B, C, and D
    """

    events = []

    # Treat first_start as the first A check in the cycle.
    # This creates an expected pattern close to:
    # A, B, A, C, A, B, A, D
    due_dates = {
        "A": first_start,
        "B": first_start + timedelta(days=365),
        "C": first_start + timedelta(days=365 * 3),
        "D": first_start + timedelta(days=365 * 7),
    }

    priority = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4
    }

    aircraft_available_from = first_start

    while aircraft_available_from <= forecast_end:

        # Find the earliest due date among A/B/C/D
        earliest_due_date = min(due_dates.values())

        # Stop if the next required check is beyond the forecast
        if earliest_due_date > forecast_end:
            break

        candidates = []

        for check_type, due_date in due_dates.items():
            rule = CHECK_RULES[check_type]

            earliest_start = due_date - timedelta(days=rule["early_days"])
            latest_start = due_date

            # If this check can legally be started by the time the earliest
            # required maintenance is due, consider it as a candidate.
            # This allows C to replace B, or D to replace C/B/A, when the
            # larger check is close enough and inside its early-start window.
            if earliest_start <= earliest_due_date:
                candidates.append({
                    "Check": check_type,
                    "Due_Date": due_date,
                    "Earliest_Start": earliest_start,
                    "Latest_Start": latest_start,
                    "Priority": priority[check_type]
                })

        # Choose the highest-level check available.
        # Example: if A and B are both candidates, choose B.
        # If B and C are both candidates, choose C.
        next_check_info = max(candidates, key=lambda x: x["Priority"])

        check_type = next_check_info["Check"]
        rule = CHECK_RULES[check_type]

        # Schedule the check as late as possible while still covering the
        # earliest due maintenance requirement.
        # This avoids always starting at the earliest allowed date, which was
        # causing the cycle to compress and create too many B checks.
        window_start = max(
            aircraft_available_from,
            next_check_info["Earliest_Start"]
        )

        window_end = next_check_info["Latest_Start"]

        if window_start > window_end:
            current_start = window_end
        else:
            random_days = np.random.randint(
                0,
                (window_end - window_start).days + 1
            )

            current_start = window_start + timedelta(days=random_days)

        if current_start > forecast_end:
            break

        duration = rule["duration_days"]
        end_date = current_start + timedelta(days=duration)

        events.append({
            "Aircraft": aircraft,
            "Check": check_type,
            "Start": current_start,
            "End": end_date,
            "Duration": duration,
            "Due_Date": next_check_info["Due_Date"],
            "Earliest_Start": next_check_info["Earliest_Start"],
            "Latest_Start": next_check_info["Latest_Start"],
            "Interval_Days": rule["interval_days"],
            "Early_Start_Allowance_Days": rule["early_days"]
        })

        # Update due dates after completing the selected check
        if check_type == "A":
            due_dates["A"] = end_date + timedelta(days=CHECK_RULES["A"]["interval_days"])

        elif check_type == "B":
            due_dates["A"] = end_date + timedelta(days=CHECK_RULES["A"]["interval_days"])
            due_dates["B"] = end_date + timedelta(days=CHECK_RULES["B"]["interval_days"])

        elif check_type == "C":
            due_dates["A"] = end_date + timedelta(days=CHECK_RULES["A"]["interval_days"])
            due_dates["B"] = end_date + timedelta(days=CHECK_RULES["B"]["interval_days"])
            due_dates["C"] = end_date + timedelta(days=CHECK_RULES["C"]["interval_days"])

        elif check_type == "D":
            due_dates["A"] = end_date + timedelta(days=CHECK_RULES["A"]["interval_days"])
            due_dates["B"] = end_date + timedelta(days=CHECK_RULES["B"]["interval_days"])
            due_dates["C"] = end_date + timedelta(days=CHECK_RULES["C"]["interval_days"])
            due_dates["D"] = end_date + timedelta(days=CHECK_RULES["D"]["interval_days"])

        aircraft_available_from = end_date

    return events


def generate_full_schedule(aircraft_first_starts, forecast_years):
    """
    Generates the full maintenance schedule for all aircraft.
    """

    global_start = min(aircraft_first_starts.values())
    forecast_end = global_start + timedelta(days=365 * forecast_years)

    all_events = []

    for aircraft, first_start in aircraft_first_starts.items():
        aircraft_events = generate_aircraft_schedule(
            aircraft=aircraft,
            first_start=first_start,
            forecast_end=forecast_end
        )
        all_events.extend(aircraft_events)

    df_events = pd.DataFrame(all_events)
    df_events = df_events.sort_values(["Aircraft", "Start"]).reset_index(drop=True)

    return df_events, global_start, forecast_end


# ============================================================
# COMPUTE AVAILABILITY
# ============================================================

def compute_daily_availability(df_events, fleet_size, global_start, forecast_end):
    """
    Computes daily fleet availability.

    Availability = total aircraft - aircraft currently in maintenance
    """

    dates = pd.date_range(global_start, forecast_end, freq="D")

    availability_records = []

    for date in dates:
        in_maintenance = (
            (df_events["Start"] <= date) &
            (df_events["End"] > date)
        ).sum()

        available = fleet_size - in_maintenance

        availability_records.append({
            "Date": date,
            "In_Maintenance": int(in_maintenance),
            "Available": int(available)
        })

    df_availability = pd.DataFrame(availability_records)

    return df_availability


# ============================================================
# SUMMARY METRICS
# ============================================================

def compute_summary(df_availability):
    """
    Computes useful availability metrics for comparison.
    """

    summary = {
        "Mean_Availability": df_availability["Available"].mean(),
        "Min_Availability": df_availability["Available"].min(),
        "Max_Availability": df_availability["Available"].max(),
        "Availability_Variance": df_availability["Available"].var(),
        "Availability_Std": df_availability["Available"].std(),
        "Mean_In_Maintenance": df_availability["In_Maintenance"].mean(),
        "Max_In_Maintenance": df_availability["In_Maintenance"].max()
    }

    return pd.DataFrame([summary])


# ============================================================
# EXPORT TO EXCEL
# ============================================================
def export_to_excel(df_events, df_availability, aircraft_first_starts, df_summary):
    """
    Exports the generated dataset to Excel.
    """

    df_fleet = pd.DataFrame([
        {
            "Aircraft": aircraft,
            "First_Start": first_start
        }
        for aircraft, first_start in aircraft_first_starts.items()
    ])

    df_rules = pd.DataFrame([
        {
            "Check": check,
            "Duration_Days": rule["duration_days"],
            "Interval_Days": rule["interval_days"],
            "Early_Start_Allowance_Days": rule["early_days"]
        }
        for check, rule in CHECK_RULES.items()
    ])

    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:

        df_events.to_excel(writer, sheet_name="MxEvents", index=False)
        df_availability.to_excel(writer, sheet_name="Availability", index=False)
        df_fleet.to_excel(writer, sheet_name="Fleet", index=False)
        df_rules.to_excel(writer, sheet_name="CheckRules", index=False)
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Availability"]

        chart = workbook.add_chart({"type": "line"})

        max_row = len(df_availability)

        # Plot available aircraft
        chart.add_series({
            "name": "Available Aircraft",
            "categories": ["Availability", 1, 0, max_row, 0],
            "values": ["Availability", 1, 2, max_row, 2],
            "line": {
                "width": 1.5
            }
        })

        chart.set_title({
            "name": "12-Year Fleet Availability Forecast"
        })

        chart.set_x_axis({
            "name": "Date",
            "date_axis": True,
            "num_format": "yyyy",
            "major_gridlines": {
                "visible": False
            }
        })

        chart.set_y_axis({
            "name": "Available Aircraft",
            "major_gridlines": {
                "visible": True
            }
        })

        chart.set_legend({
            "position": "bottom"
        })

        chart.set_size({
            "width": 1200,
            "height": 500
        })

        worksheet.insert_chart("F2", chart)


import matplotlib.pyplot as plt

def plot_12_year_availability(df_availability):
    """
    Displays fleet availability across the full 12-year forecast.
    """

    plt.figure(figsize=(16, 6))

    plt.plot(
        df_availability["Date"],
        df_availability["Available"],
        linewidth=1
    )

    plt.title("Fleet Availability Across 12-Year Maintenance Forecast")
    plt.xlabel("Date")
    plt.ylabel("Available Aircraft")

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


# ============================================================
# MAIN
# ============================================================

def main():
    print("Loading existing aircraft first start dates...")

    existing_first_starts = load_existing_first_starts(
        input_file=INPUT_FILE,
        sheet_name=INPUT_SHEET
    )

    print(f"Existing aircraft found: {len(existing_first_starts)}")

    aircraft_first_starts = create_aircraft_first_starts(
        existing_first_starts=existing_first_starts,
        fleet_size=FLEET_SIZE
    )

    print(f"Generating forecast for {FLEET_SIZE} aircraft...")

    df_events, global_start, forecast_end = generate_full_schedule(
        aircraft_first_starts=aircraft_first_starts,
        forecast_years=FORECAST_YEARS
    )

    df_availability = compute_daily_availability(
        df_events=df_events,
        fleet_size=FLEET_SIZE,
        global_start=global_start,
        forecast_end=forecast_end
    )

    plot_12_year_availability(df_availability)

    df_summary = compute_summary(df_availability)

    export_to_excel(
        df_events=df_events,
        df_availability=df_availability,
        aircraft_first_starts=aircraft_first_starts,
        df_summary=df_summary
    )

    print("Done.")
    print(f"Output saved to: {OUTPUT_FILE}")
    print()
    print("Summary:")
    print(df_summary.T)


if __name__ == "__main__":
    main()