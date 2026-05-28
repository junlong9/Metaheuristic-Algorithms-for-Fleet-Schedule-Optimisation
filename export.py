import pandas as pd

# ============================================================
# CONVERT SCHEDULE BACK TO TABLE
# ============================================================

def schedule_to_events_table(schedule, base_date):
    """
    Converts schedule dictionary back into a DataFrame.
    """

    records = []

    for aircraft, events in schedule.items():
        for event in events:
            start_date = base_date + pd.Timedelta(days=event["start"])
            end_date = start_date + pd.Timedelta(days=event["duration"])
            earliest_start = base_date + pd.Timedelta(days=event["earliest_start"])
            latest_start = base_date + pd.Timedelta(days=event["latest_start"])

            records.append({
                "Aircraft": aircraft,
                "Check": event["check"],
                "Start": start_date,
                "End": end_date,
                "Duration": event["duration"],
                "Earliest_Start": earliest_start,
                "Latest_Start": latest_start,
            })

    df = pd.DataFrame(records)
    df = df.sort_values(["Aircraft", "Start"]).reset_index(drop=True)

    return df


# ============================================================
# AVAILABILITY TABLE
# ============================================================

def make_availability_table(availability, base_date):
    """
    Converts availability array into a date table.
    """

    dates = [
        base_date + pd.Timedelta(days=i)
        for i in range(len(availability))
    ]

    return pd.DataFrame({
        "Date": dates,
        "Available": availability
    })


# ============================================================
# EXPORT RESULTS TO EXCEL
# ============================================================

def export_optimised_to_excel(
    output_file,
    original_events,
    best_events,
    original_table,
    best_table,
    original_score,
    best_score
):
    """
    Exports original and optimised schedules to Excel,
    including a comparison availability chart.
    """

    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        original_events.to_excel(writer, sheet_name="Original_MxEvents", index=False)
        best_events.to_excel(writer, sheet_name="Optimised_MxEvents", index=False)
        original_table.to_excel(writer, sheet_name="Original_Availability", index=False)
        best_table.to_excel(writer, sheet_name="Optimised_Availability", index=False)

        summary = pd.DataFrame([
            {
                "Schedule": "Original",
                "Min_Availability": original_score[0],
                "Availability_Std": -original_score[1],
                "Average_Availability": original_score[2],
            },
            {
                "Schedule": "Optimised",
                "Min_Availability": best_score[0],
                "Availability_Std": -best_score[1],
                "Average_Availability": best_score[2],
            }
        ])

        summary.to_excel(writer, sheet_name="Summary", index=False)

        workbook = writer.book
        summary_sheet = writer.sheets["Summary"]

        chart = workbook.add_chart({"type": "line"})

        original_max_row = len(original_table)
        best_max_row = len(best_table)

        chart.add_series({
            "name": "Original Availability",
            "categories": ["Original_Availability", 1, 0, original_max_row, 0],
            "values": ["Original_Availability", 1, 1, original_max_row, 1],
            "line": {"width": 1.25},
        })

        chart.add_series({
            "name": "Optimised Availability",
            "categories": ["Optimised_Availability", 1, 0, best_max_row, 0],
            "values": ["Optimised_Availability", 1, 1, best_max_row, 1],
            "line": {"width": 1.25},
        })

        chart.set_title({"name": "Original vs Optimised Fleet Availability"})

        chart.set_x_axis({
            "name": "Date",
            "date_axis": True,
            "num_format": "yyyy"
        })

        chart.set_y_axis({
            "name": "Available Aircraft"
        })

        chart.set_size({
            "width": 1200,
            "height": 500
        })

        chart.set_legend({
            "position": "bottom"
        })

        summary_sheet.insert_chart("A5", chart)