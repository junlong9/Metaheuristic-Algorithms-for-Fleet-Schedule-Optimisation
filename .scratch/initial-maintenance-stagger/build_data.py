"""Create synthetic maintenance-age inputs without changing maintenance rules.

The original forecast is preserved. Each aircraft's existing maintenance
timeline is translated into an older maintenance phase, replayed from its
historical initial state, and extended through the same forecast horizon.
Workbook authoring is performed separately by build_workbooks.mjs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "heavy_maintenance_forecast.xlsx"
RULES = {
    "A": {"duration": 14, "interval": 365, "early": 42},
    "B": {"duration": 28, "interval": 730, "early": 70},
    "C": {"duration": 84, "interval": 1460, "early": 70},
    "D": {"duration": 126, "interval": 2920, "early": 70},
}
SEQUENCE = ("A", "B", "A", "C", "A", "B", "A", "D")
LEVEL = {check: i for i, check in enumerate(RULES)}
EVENT_COLUMNS = [
    "Aircraft", "Check", "Start", "End", "Duration", "Due_Date",
    "Earliest_Start", "Latest_Start", "Interval_Days",
    "Early_Start_Allowance_Days",
]


def reset(due, check, completion):
    for name, rule in RULES.items():
        if LEVEL[name] <= LEVEL[check]:
            due[name] = completion + rule["interval"]


def make_event(aircraft, check, start, due):
    rule = RULES[check]
    return {
        "aircraft": aircraft, "check": check, "start": int(start),
        "duration": rule["duration"], "earliest_start": int(due - rule["early"]),
        "latest_start": int(due),
    }


def audit_timeline(events, first_due, forecast_end):
    """Independent replay of the existing fixed-sequence maintenance model."""
    due = {name: first_due - 365 + rule["interval"] for name, rule in RULES.items()}
    previous_end = first_due - 365
    for index, event in enumerate(events):
        check = event["check"]
        rule = RULES[check]
        assert check == SEQUENCE[index % 8], (index, check)
        assert event["duration"] == rule["duration"]
        assert event["latest_start"] == due[check]
        assert event["earliest_start"] == due[check] - rule["early"]
        assert previous_end <= event["start"]
        assert event["earliest_start"] <= event["start"] <= due[check]
        assert event["start"] <= forecast_end
        previous_end = event["start"] + event["duration"]
        reset(due, check, previous_end)
    assert due[SEQUENCE[len(events) % 8]] > forecast_end, (events[-1], due, forecast_end)
    return due


def datestr(base, day):
    return (base + pd.Timedelta(days=int(day))).strftime("%Y-%m-%d")


def export_events(base, events):
    return [[
        e["aircraft"], e["check"], datestr(base, e["start"]),
        datestr(base, e["start"] + e["duration"]), e["duration"],
        datestr(base, e["latest_start"]), datestr(base, e["earliest_start"]),
        datestr(base, e["latest_start"]), RULES[e["check"]]["interval"],
        RULES[e["check"]]["early"],
    ] for e in events]


def metrics(events_by_aircraft, base, horizon, operational):
    days = np.arange(horizon + 1)
    occupied = {}
    d_occupied = np.zeros(horizon + 1, dtype=int)
    for aircraft, events in events_by_aircraft.items():
        mask = np.zeros(horizon + 1, dtype=int)
        for event in events:
            start = max(0, event["start"])
            end = min(horizon + 1, event["start"] + event["duration"])
            if end <= start:
                continue
            mask[start:end] += 1
            if event["check"] == "D":
                d_occupied[start:end] += 1
        assert np.max(mask) <= 1
        occupied[aircraft] = mask
    unavailable = sum(occupied.values())
    availability = len(events_by_aircraft) - unavailable
    first_ds = [next(e["start"] for e in events if e["check"] == "D" and
                    e["start"] + e["duration"] > 0)
                for events in events_by_aircraft.values()]
    visible = [e for events in events_by_aircraft.values() for e in events
               if e["start"] <= horizon and e["start"] + e["duration"] > 0]
    result = {
        "worst_day_availability": int(availability.min()),
        "mean_availability": float(availability.mean()),
        "availability_std_population": float(availability.std()),
        "peak_concurrent_D_checks": int(d_occupied.max()),
        "D_aircraft_days": int(d_occupied.sum()),
        "maintenance_aircraft_days": int(unavailable.sum()),
        "first_D_start": datestr(base, min(first_ds)),
        "last_first_D_start": datestr(base, max(first_ds)),
        "aircraft_first_D_before_2030": sum(datestr(base, day) < "2030-01-01" for day in first_ds),
        "visible_check_count": len(visible),
        "visible_D_count": sum(e["check"] == "D" for e in visible),
        "max_D_days_early": max(e["latest_start"] - e["start"] for e in visible if e["check"] == "D"),
        "max_ABC_days_early": {name: max(e["latest_start"] - e["start"] for e in visible if e["check"] == name) for name in "ABC"},
        "operational_scenarios": {},
    }
    for scenario in operational["scenarios"]:
        periods = []
        breaches = []
        for period in scenario["busy_periods"]:
            lo = (pd.Timestamp(period["start"]) - base).days
            hi = (pd.Timestamp(period["end"]) - base).days
            actual = int(availability[lo:hi + 1].min())
            deficit_days = int(np.sum(availability[lo:hi + 1] < period["minimum_availability"]))
            periods.append({**period, "actual_minimum": actual, "breach_days": deficit_days})
            if deficit_days:
                breaches.append(f"Busy period {period['start']} to {period['end']}: {deficit_days} days")
        groups = []
        for group in scenario["dependency_groups"]:
            group_avail = len(group["aircraft"]) - sum(occupied[a] for a in group["aircraft"])
            actual = int(group_avail.min())
            deficit_days = int(np.sum(group_avail < group["minimum_available"]))
            groups.append({**group, "actual_minimum": actual, "breach_days": deficit_days})
            if deficit_days:
                breaches.append(f"Dependency group {group['aircraft']}: {deficit_days} days")
        result["operational_scenarios"][scenario["name"]] = {
            "passes": not breaches, "breaches": breaches,
            "displacement_limit_days": scenario["displacement_limit_days"],
            "displacement_from_this_input_days": 0,
            "busy_periods": periods, "dependency_groups": groups,
        }
    annual = []
    for year in range(base.year, (base + pd.Timedelta(days=horizon)).year + 1):
        lo = max(0, (pd.Timestamp(year, 1, 1) - base).days)
        hi = min(horizon + 1, (pd.Timestamp(year + 1, 1, 1) - base).days)
        year_events = [e for e in visible if datestr(base, e["start"])[:4] == str(year)]
        annual.append([year, sum(e["check"] == "D" for e in year_events),
                       int(d_occupied[lo:hi].max()), int(availability[lo:hi].min())])
    daily = [[datestr(base, day), int(unavailable[day]), int(availability[day]),
              int(d_occupied[day])] for day in days]
    return result, annual, daily


def main():
    source_events = pd.read_excel(SOURCE, sheet_name="MxEvents")
    source_days = pd.read_excel(SOURCE, sheet_name="Availability")
    source_rules = pd.read_excel(SOURCE, sheet_name="CheckRules")
    for row in source_rules.to_dict("records"):
        rule = RULES[row["Check"]]
        assert (row["Duration_Days"], row["Interval_Days"], row["Early_Start_Allowance_Days"]) == (rule["duration"], rule["interval"], rule["early"])
    base = pd.Timestamp(source_days.Date.min())
    horizon = (pd.Timestamp(source_days.Date.max()) - base).days
    operational = json.loads((ROOT / "operational_constraints.json").read_text())
    source_schedule = {}
    for aircraft, frame in source_events.groupby("Aircraft", sort=True):
        source_schedule[aircraft] = [make_event(
            aircraft, row.Check, (row.Start - base).days, (row.Latest_Start - base).days
        ) for row in frame.sort_values("Start").itertuples()]
        audit_timeline(source_schedule[aircraft], source_schedule[aircraft][0]["latest_start"], horizon)
    original_metrics, original_annual, _ = metrics(source_schedule, base, horizon, operational)
    names = sorted(source_schedule)
    permutation = np.random.default_rng(42).permutation(len(names))
    ordered_names = [names[index] for index in permutation]
    variants = []
    for slug, title, age_years in (
        ("moderate", "Moderate maintenance-age stagger", [1, 3, 5] * 8),
        ("wide", "Wide maintenance-age stagger", [1, 2, 3, 4, 5, 6] * 4),
    ):
        phases = {aircraft: int(years * 365) for aircraft, years in zip(ordered_names, age_years)}
        schedules = {}
        fleet = []
        history = []
        for aircraft in names:
            advance = phases[aircraft]
            original = source_schedule[aircraft]
            first_due = original[0]["latest_start"] - advance
            virtual_reset = first_due - 365
            assert virtual_reset <= 0, "Opening synthetic D clock must be anchored in the past."
            due = {check: virtual_reset + rule["interval"] for check, rule in RULES.items()}
            opening_due = due.copy()
            initial_check_index = 0
            events = []
            for position, original_event in enumerate(original):
                event = {**original_event,
                         **{name: original_event[name] - advance for name in ("start", "earliest_start", "latest_start")}}
                if event["start"] > horizon:
                    break
                events.append(event)
                if event["start"] + event["duration"] <= 0:
                    reset(opening_due, event["check"], event["start"] + event["duration"])
                    initial_check_index = position + 1
                reset(due, event["check"], event["start"] + event["duration"])
            rng = np.random.default_rng(1000 + names.index(aircraft))
            while due[SEQUENCE[len(events) % 8]] <= horizon:
                check = SEQUENCE[len(events) % 8]
                previous_end = events[-1]["start"] + events[-1]["duration"]
                lo = max(previous_end, due[check] - RULES[check]["early"])
                hi = min(due[check], horizon)
                assert lo <= hi, (aircraft, check, lo, hi, due)
                start = int(rng.integers(lo, hi + 1))
                event = make_event(aircraft, check, start, due[check])
                events.append(event)
                reset(due, check, start + RULES[check]["duration"])
            audit_timeline(events, first_due, horizon)
            schedules[aircraft] = events
            opening_active = next((e for e in events if e["start"] < 0 < e["start"] + e["duration"]), None)
            first_visible = next(e for e in events if e["start"] + e["duration"] > 0)
            first_d = next(e for e in events if e["check"] == "D" and e["start"] + e["duration"] > 0)
            fleet.append([
                aircraft, datestr(base, first_visible["start"]), advance,
                datestr(base, first_due), datestr(base, virtual_reset),
                *(datestr(base, opening_due[check]) for check in RULES),
                initial_check_index % 8, opening_active["check"] if opening_active else "",
                datestr(base, opening_active["start"] + opening_active["duration"]) if opening_active else None,
                datestr(base, first_d["start"]), datestr(base, first_d["latest_start"]),
                RULES["D"]["interval"] - opening_due["D"], first_visible["check"],
            ])
            history.extend(e for e in events if e["start"] + e["duration"] <= 0)
        result, annual, daily = metrics(schedules, base, horizon, operational)
        visible = [e for aircraft in names for e in schedules[aircraft]
                   if e["start"] + e["duration"] > 0]
        variant = {
            "slug": slug, "title": title,
            "filename": f"heavy_maintenance_forecast_stagger_{slug}.xlsx",
            "metrics": result, "annual": annual,
            "events": export_events(base, visible), "history": export_events(base, history),
            "fleet": fleet, "daily": daily,
            "full_schedule": schedules,
        }
        variants.append(variant)
    payload = {
        "source": SOURCE.name, "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "constraints_sha256": hashlib.sha256((ROOT / "operational_constraints.json").read_bytes()).hexdigest(),
        "forecast_start": datestr(base, 0), "forecast_end": datestr(base, horizon),
        "forecast_days": horizon + 1, "fleet_size": len(names), "seed": 42,
        "rules": RULES, "event_columns": EVENT_COLUMNS,
        "fleet_columns": ["Aircraft", "First_Start", "Maintenance_Phase_Advance_Days",
                          "Historical_First_A_Due", "Assumed_Previous_D_Completion",
                          "Opening_A_Due", "Opening_B_Due", "Opening_C_Due", "Opening_D_Due",
                          "Opening_Sequence_Index", "Opening_Check_In_Progress",
                          "Opening_Check_End", "First_Forecast_D_Start", "First_Forecast_D_Due",
                          "Opening_D_Age_Days", "Opening_Check_Type"],
        "operational_constraints": operational,
        "original_metrics": original_metrics, "original_annual": original_annual,
        "variants": variants,
    }
    (OUT / "schedule-data.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"forecast_start": payload["forecast_start"], "forecast_end": payload["forecast_end"],
                      "original": original_metrics,
                      **{v["slug"]: v["metrics"] for v in variants}}, indent=2))


if __name__ == "__main__":
    main()
