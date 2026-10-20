import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest

import numpy as np

import vn_priority_based_selection as optimiser


def event(check, start, duration, earliest, latest):
    return {
        "check": check,
        "start": start,
        "duration": duration,
        "earliest_start": earliest,
        "latest_start": latest,
    }


class FixedHorizonAndFeasibilityTests(unittest.TestCase):
    def setUp(self):
        self.schedule = {
            "A1": [event("A", 10, 14, 0, 20)],
            "A2": [event("A", 40, 14, 30, 50)],
        }

    def test_fixed_horizon_keeps_availability_lengths_comparable(self):
        horizon = optimiser.get_forecast_horizon(self.schedule)
        shifted = {
            "A1": [event("A", 15, 14, 0, 20)],
            "A2": [event("A", 35, 14, 30, 50)],
        }

        original = optimiser.compute_availability(self.schedule, horizon)
        candidate = optimiser.compute_availability(shifted, horizon)

        self.assertEqual(horizon + 1, len(original))
        self.assertEqual(len(original), len(candidate))
        self.assertEqual(64, horizon)

    def test_adjacent_events_are_feasible(self):
        events = [
            event("A", 10, 14, 0, 20),
            event("B", 24, 28, 24, 60),
        ]

        self.assertTrue(optimiser.is_aircraft_feasible(events, horizon=100))

    def test_overlapping_events_are_infeasible(self):
        events = [
            event("A", 10, 14, 0, 20),
            event("B", 23, 28, 20, 60),
        ]

        self.assertFalse(optimiser.is_aircraft_feasible(events, horizon=100))


class RuleAwareRebuildTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            event("A", 100, 14, 58, 100),
            event("B", 430, 28, 395, 465),
            event("A", 800, 14, 781, 823),
            event("C", 1150, 84, 1125, 1195),
            event("A", 1580, 14, 1557, 1599),
            event("B", 1920, 28, 1894, 1964),
            event("A", 2290, 14, 2271, 2313),
            event("D", 2620, 126, 2585, 2655),
        ]

    def test_rebuild_propagates_windows_after_shifted_check(self):
        rebuilt = optimiser.rebuild_aircraft_schedule(
            self.events,
            event_index=1,
            new_start=450,
            horizon=2900,
        )

        self.assertIsNotNone(rebuilt)
        self.assertEqual(450, rebuilt[1]["start"])
        self.assertEqual(801, rebuilt[2]["earliest_start"])
        self.assertEqual(843, rebuilt[2]["latest_start"])
        self.assertTrue(optimiser.is_aircraft_feasible(rebuilt, horizon=2900))

    def test_rebuild_applies_larger_check_substitution(self):
        rebuilt = optimiser.rebuild_aircraft_schedule(
            self.events,
            event_index=1,
            new_start=450,
            horizon=2900,
        )

        self.assertEqual(
            ["A", "B", "A", "C", "A", "B", "A", "D"],
            [item["check"] for item in rebuilt[:8]],
        )

    def test_rebuild_preserves_supplied_event_count(self):
        rebuilt = optimiser.rebuild_aircraft_schedule(
            self.events,
            event_index=1,
            new_start=450,
            horizon=2900,
        )

        self.assertEqual(len(self.events), len(rebuilt))
        self.assertEqual(
            tuple(item["check"] for item in rebuilt),
            optimiser.CHECK_SEQUENCE,
        )


class PrioritySearchTests(unittest.TestCase):
    def setUp(self):
        events = [
            event("A", 100, 14, 58, 100),
            event("B", 430, 28, 395, 465),
            event("A", 800, 14, 781, 823),
            event("C", 1150, 84, 1125, 1195),
            event("A", 1580, 14, 1557, 1599),
            event("B", 1920, 28, 1894, 1964),
            event("A", 2290, 14, 2271, 2313),
            event("D", 2620, 126, 2585, 2655),
        ]
        self.schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        self.horizon = 2900

    def test_priority_order_starts_with_event_covering_global_minimum(self):
        availability = optimiser.compute_availability(
            self.schedule,
            self.horizon,
        )

        ordered = optimiser.prioritise_events(
            self.schedule,
            availability,
        )

        aircraft, index = ordered[0]
        selected = self.schedule[aircraft][index]
        minimum_days = set(
            np.flatnonzero(availability == np.min(availability))
        )
        active_days = set(range(
            selected["start"],
            selected["start"] + selected["duration"],
        ))
        self.assertTrue(minimum_days.intersection(active_days))

    def test_neighbor_generation_is_deterministic_and_overlap_free(self):
        availability = optimiser.compute_availability(
            self.schedule,
            self.horizon,
        )
        current_score = optimiser.score_availability(availability)

        first = optimiser.generate_neighbors(
            self.schedule,
            availability,
            self.horizon,
            current_score,
            shifts=(-10, 10),
        )
        second = optimiser.generate_neighbors(
            self.schedule,
            availability,
            self.horizon,
            current_score,
            shifts=(-10, 10),
        )

        first_moves = [
            (item["aircraft"], item["event_index"], item["new_start"])
            for item in first
        ]
        second_moves = [
            (item["aircraft"], item["event_index"], item["new_start"])
            for item in second
        ]

        self.assertTrue(first)
        self.assertEqual(first_moves, second_moves)
        self.assertTrue(all(
            optimiser.is_aircraft_feasible(
                item["events"],
                self.horizon,
            )
            for item in first
        ))

    def test_complete_rule_validation_rejects_wrong_check_sequence(self):
        self.assertTrue(optimiser.is_rule_compliant_schedule(
            self.schedule,
            self.horizon,
        ))

        invalid = {
            aircraft: [item.copy() for item in events]
            for aircraft, events in self.schedule.items()
        }
        invalid["A1"][2]["check"] = "B"
        invalid["A1"][2]["duration"] = 28

        self.assertFalse(optimiser.is_rule_compliant_schedule(
            invalid,
            self.horizon,
        ))


if __name__ == "__main__":
    unittest.main()
