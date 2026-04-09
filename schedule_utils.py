import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FILE_PATH = "Simple Random Fleet Plans.xlsx"
SHEET_NAME = "MxEvents"


def load_schedule(file_path, sheet_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = df.columns.str.strip()

    df["Start"] = pd.to_datetime(df["Start"])
    base_date = df["Start"].min()
    df["Start_day"] = (df["Start"] - base_date).dt.days

    schedule = {}
    for aircraft, group in df.groupby("Aircraft"):
        group = group.sort_values("Start")
        aircraft_events = []
    
        for _, row in group.iterrows():
            entry = {
            "id": f"{aircraft}_event_{len(aircraft_events)}",
            "start": int(row["Start_day"]),
            "duration": int(row["Duration"]),
            }
            aircraft_events.append(entry)
        schedule[aircraft] = aircraft_events

    return schedule, base_date


def compute_availability(schedule):
    num_aircraft = len(schedule)

    last_day = 0
    for checks in schedule.values():
        for event in checks:
            last_day = max(last_day, event["start"] + event["duration"])

    maintenance_counts = np.zeros(last_day + 1)

    for checks in schedule.values():
        for event in checks:
            start = event["start"]
            end = event["start"] + event["duration"]
            
            maintenance_counts[start:end] += 1

    availability = num_aircraft - maintenance_counts
    return np.array(availability)


def make_availability_table(availability, base_date):
    days = np.arange(len(availability))
    dates = [base_date + pd.Timedelta(days=int(day)) for day in days]

    return pd.DataFrame({
        "Date": dates,
        "Day": days,
        "AvailableAircraft": availability
    })


def plot_availability(table):
    plt.figure(figsize=(14, 6))
    plt.plot(table["Date"], table["AvailableAircraft"])
    plt.title("Aircraft Availability Over Time")
    plt.xlabel("Date")
    plt.ylabel("Available Aircraft")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


OUTPUT_FILE = "initial_availability_output.xlsx"
def export_to_excel(table, output_file=OUTPUT_FILE):
    with pd.ExcelWriter(output_file, engine="xlsxwriter", datetime_format="dd/mm/yyyy") as writer:
        table.to_excel(writer, sheet_name="Availability", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Availability"]

        worksheet.set_column("A:A", 15)  # Date
        worksheet.set_column("B:B", 10)  # Day
        worksheet.set_column("C:C", 18)  # AvailableAircraft

        chart = workbook.add_chart({"type": "line"})

        max_row = len(table)

        chart.add_series({
            "name": "Available Aircraft",
            "categories": ["Availability", 1, 0, max_row, 0],
            "values": ["Availability", 1, 2, max_row, 2],
        })

        chart.set_title({"name": "Aircraft Availability Over Time"})
        chart.set_x_axis({
            "name": "Date",
            "date_axis": True,
            "num_format": "dd/mm/yyyy"
        })
        chart.set_y_axis({
            "name": "Available Aircraft",
            "major_gridlines": {"visible": True}
        })
        chart.set_size({"width": 900, "height": 500})

        worksheet.insert_chart("E2", chart)