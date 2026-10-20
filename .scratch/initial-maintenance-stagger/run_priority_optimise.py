"""Optimise a stagger workbook with the priority-based selection optimiser.

The optimiser replays every aircraft from sequence position 0. These inputs
open later in the A/B/A/C/A/B/A/D cycle, so this runner supplies each
aircraft's saved opening sequence index and due clocks, then calls the
unchanged search.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import vn_priority_based_selection as optimiser
from export import (
    export_optimised_to_excel,
    make_availability_table,
    schedule_to_events_table,
)

DATA = Path(__file__).resolve().parent / "schedule-data.json"
SOURCE_DIR = ROOT / "outputs" / "initial-stagger-20261013"


def rebuild_from_opening_state(
    events,
    horizon,
    event_index=None,
    new_start=None,
):
    """Replay one aircraft from its saved opening sequence and due clocks."""

    old_events = sorted(events, key=lambda item: item["start"])
    if not old_events:
        return None

    origin = old_events[0].get("_origin")
    opening = old_events[0].get("_opening")
    if origin is None or opening is None:
        raise ValueError("Stagger event is missing its opening maintenance state.")

    due_dates = dict(opening)
    first_check = optimiser.CHECK_SEQUENCE[origin % len(optimiser.CHECK_SEQUENCE)]
    aircraft_available_from = (
        due_dates[first_check] - optimiser.CHECK_RULES[first_check]["early"]
    )
    rebuilt = []

    for position, old_event in enumerate(old_events):
        check = optimiser.CHECK_SEQUENCE[
            (origin + position) % len(optimiser.CHECK_SEQUENCE)
        ]
        rule = optimiser.CHECK_RULES[check]
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
            if old_event["check"] != check:
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
            "_origin": origin,
            "_opening": opening,
        })
        optimiser._update_due_dates(due_dates, check, end)
        aircraft_available_from = end

    return rebuilt


def attach_opening_state(schedule, base_date, fleet_rows):
    fleet = {row[0]: row for row in fleet_rows}
    for aircraft, events in schedule.items():
        row = fleet[aircraft]
        origin = int(row[9])
        opening = {
            check: (pd.Timestamp(row[5 + index]) - base_date).days
            for index, check in enumerate("ABCD")
        }
        for event in events:
            event["_origin"] = origin
            event["_opening"] = opening


def main(slug):
    if slug not in {"moderate", "wide"}:
        raise SystemExit(f"Unknown stagger variant: {slug}")

    source = SOURCE_DIR / f"heavy_maintenance_forecast_stagger_{slug}.xlsx"
    output = SOURCE_DIR / f"optimised_heavy_maintenance_output_{slug}.xlsx"
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    variant = next(item for item in payload["variants"] if item["slug"] == slug)

    optimiser.rebuild_aircraft_schedule = rebuild_from_opening_state
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / source.name
        shutil.copy2(source, snapshot)
        schedule, base_date = optimiser.load_heavy_schedule(snapshot, "MxEvents")
    attach_opening_state(schedule, base_date, variant["fleet"])
    horizon = optimiser.get_forecast_horizon(schedule)

    if not optimiser.is_rule_compliant_schedule(schedule, horizon):
        raise RuntimeError(f"{slug} input is not rule-compliant after opening-state replay.")

    original_score = optimiser.evaluate_schedule(schedule, horizon)
    print(f"{slug} original score: {original_score}", flush=True)
    best_schedule, best_score, _history = optimiser.vn_optimise(schedule)
    print(f"{slug} best score: {best_score}", flush=True)

    original_availability = optimiser.compute_availability(schedule, horizon)
    best_availability = optimiser.compute_availability(best_schedule, horizon)
    export_optimised_to_excel(
        output_file=output,
        original_events=schedule_to_events_table(schedule, base_date),
        best_events=schedule_to_events_table(best_schedule, base_date),
        original_table=make_availability_table(original_availability, base_date),
        best_table=make_availability_table(best_availability, base_date),
        original_score=original_score,
        best_score=best_score,
    )
    print(f"{slug} saved: {output}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
