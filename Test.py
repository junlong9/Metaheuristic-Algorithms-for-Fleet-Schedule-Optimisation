from schedule_utils import export_to_excel, load_schedule, compute_availability, make_availability_table, plot_availability
FILE_PATH = "Simple Random Fleet Plans.xlsx"
SHEET_NAME = "MxEvents"

def main():
    schedule, base_date = load_schedule(FILE_PATH, SHEET_NAME)
    availability = compute_availability(schedule)
    table = make_availability_table(availability, base_date)

    print(table.head(10))
    plot_availability(table)

    export_to_excel(table)
    print("Excel file created: initial_availability_output.xlsx")


if __name__ == "__main__":
    main()