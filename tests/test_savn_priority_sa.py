import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import contextlib
import io
import math
import unittest
from unittest.mock import call, patch

import numpy as np
import vn_priority_based_selection as baseline
import savn_priority_sa as annealing


def event(check, start, duration, earliest, latest):
    return {
        "check": check,
        "start": start,
        "duration": duration,
        "earliest_start": earliest,
        "latest_start": latest,
    }


def compliant_events():
    return [
        event("A", 100, 14, 58, 100),
        event("B", 430, 28, 395, 465),
        event("A", 800, 14, 781, 823),
        event("C", 1150, 84, 1125, 1195),
        event("A", 1580, 14, 1557, 1599),
        event("B", 1920, 28, 1894, 1964),
        event("A", 2290, 14, 2271, 2313),
        event("D", 2620, 126, 2585, 2655),
    ]


class FakeRng:
    def __init__(self, values):
        self._values = list(values)

    def random(self):
        return self._values.pop(0)

    def permutation(self, length):
        return list(range(length))


class AcceptanceTests(unittest.TestCase):
    def test_always_accepts_better_minimum_availability(self):
        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(16, -3.0, 18.0),
            temperature=0.01,
            rng=FakeRng([0.0]),
        )

        self.assertTrue(accepted)

    def test_rejects_worse_minimum_when_draw_is_above_metropolis(self):
        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(14, -0.1, 22.0),
            temperature=1.0,
            rng=FakeRng([0.9]),
        )

        self.assertFalse(accepted)

    def test_accepts_worse_minimum_when_draw_is_below_metropolis(self):
        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(14, -0.1, 22.0),
            temperature=1.0,
            rng=FakeRng([0.1]),
        )

        self.assertTrue(accepted)

    def test_always_accepts_smoother_plan_when_minimum_is_unchanged(self):
        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(15, -1.5, 19.0),
            temperature=0.01,
            rng=FakeRng([0.0]),
        )

        self.assertTrue(accepted)

    def test_accepts_bumpier_same_minimum_when_draw_is_below_metropolis(self):
        temperature = 1.0
        probability = math.exp(-0.5 / temperature)

        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(15, -2.5, 20.0),
            temperature=temperature,
            rng=FakeRng([probability - 0.01]),
        )

        self.assertTrue(accepted)

    def test_tightened_acceptance_rejects_a_lower_worst_day_even_when_the_draw_would_allow_it(self):
        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(14, -0.1, 22.0),
            temperature=1.0,
            rng=FakeRng([0.0]),
            tightened=True,
        )

        self.assertFalse(accepted)

    def test_rejects_bumpier_same_minimum_when_draw_is_above_metropolis(self):
        temperature = 1.0
        probability = math.exp(-0.5 / temperature)

        accepted = annealing.accept_candidate(
            current_score=(15, -2.0, 20.0),
            candidate_score=(15, -2.5, 20.0),
            temperature=temperature,
            rng=FakeRng([probability + 0.01]),
        )

        self.assertFalse(accepted)


class FeasibleNeighborTests(unittest.TestCase):
    def setUp(self):
        events = compliant_events()
        self.horizon = 2900
        staggered = baseline.rebuild_aircraft_schedule(
            events,
            horizon=self.horizon,
            event_index=1,
            new_start=450,
        )
        self.schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
            "A3": staggered,
        }
        self.availability = baseline.compute_availability(
            self.schedule,
            self.horizon,
        )
        self.current_score = baseline.score_availability(self.availability)

    def test_feasible_neighbors_include_non_improving_moves(self):
        neighbors = annealing.generate_feasible_neighbors(
            self.schedule,
            self.availability,
            self.horizon,
            shifts=(-10, 10),
        )

        self.assertTrue(neighbors)
        self.assertTrue(all(
            baseline.is_aircraft_feasible(item["events"], self.horizon)
            for item in neighbors
        ))
        self.assertTrue(any(
            item["score"] <= self.current_score
            for item in neighbors
        ))


class AnnealingOptimiserTests(unittest.TestCase):
    def test_rejects_invalid_initial_schedule(self):
        invalid = {
            "A1": [
                event("A", 10, 14, 0, 20),
                event("B", 15, 28, 10, 60),
            ],
        }

        with self.assertRaises(ValueError):
            annealing.savn_optimise(invalid)

    @patch.object(annealing.baseline, "vn_optimise")
    def test_warm_start_becomes_the_initial_best(self, baseline_optimise):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        warm_schedule = {
            aircraft: [item.copy() for item in aircraft_events]
            for aircraft, aircraft_events in schedule.items()
        }
        warm_score = baseline.evaluate_schedule(
            warm_schedule,
            baseline.get_forecast_horizon(warm_schedule),
        )
        baseline_optimise.return_value = (
            warm_schedule,
            warm_score,
            [],
        )

        best, best_score, _ = annealing.savn_optimise(
            schedule,
            max_iters=0,
            warm_start=True,
        )

        baseline_optimise.assert_called_once_with(
            schedule,
            max_iters=400,
        )
        self.assertEqual(warm_schedule, best)
        self.assertEqual(warm_score, best_score)

    def test_history_starts_from_the_initial_schedule(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        horizon = baseline.get_forecast_horizon(schedule)
        initial_availability = baseline.compute_availability(schedule, horizon)

        _, _, history = annealing.savn_optimise(
            schedule,
            max_iters=1,
            random_seed=0,
            initial_temperature=1.0,
            cooling_rate=0.9,
            warm_start=False,
        )

        self.assertEqual(0, history[0]["iteration"])
        self.assertEqual(
            float(initial_availability.min()),
            history[0]["min"],
        )

    def test_accepts_an_improving_move_on_the_overlapping_fleet(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        horizon = baseline.get_forecast_horizon(schedule)
        initial_score = baseline.evaluate_schedule(schedule, horizon)

        best, best_score, history = annealing.savn_optimise(
            schedule,
            max_iters=1,
            random_seed=0,
            initial_temperature=1.0,
            cooling_rate=0.9,
            warm_start=False,
        )

        self.assertTrue(baseline.is_rule_compliant_schedule(best, horizon))
        self.assertGreater(best_score, initial_score)
        self.assertEqual(1, history[-1]["iteration"])

    def test_same_seed_returns_the_same_schedule(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        settings = {
            "max_iters": 3,
            "random_seed": 7,
            "initial_temperature": 1.0,
            "cooling_rate": 0.9,
            "warm_start": False,
        }

        first, first_score, _ = annealing.savn_optimise(schedule, **settings)
        second, second_score, _ = annealing.savn_optimise(schedule, **settings)

        self.assertEqual(first_score, second_score)
        self.assertEqual(
            [
                (aircraft, event["start"], event["check"])
                for aircraft, events in sorted(first.items())
                for event in events
            ],
            [
                (aircraft, event["start"], event["check"])
                for aircraft, events in sorted(second.items())
                for event in events
            ],
        )

    def test_prints_each_proposed_move_and_acceptance_result(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            annealing.savn_optimise(
                schedule,
                max_iters=1,
                random_seed=0,
                initial_temperature=1.0,
                cooling_rate=0.9,
                warm_start=False,
            )

        text = output.getvalue()
        self.assertIn("Initial score:", text)
        self.assertIn("Iteration 1, shifts=", text)
        self.assertIn("Temperature:", text)
        self.assertIn("Current score:", text)
        self.assertIn("Candidate score:", text)
        self.assertIn("Proposed move:", text)
        self.assertIn("Accepted.", text)

    def test_cycles_through_all_vns_shift_sizes(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            annealing.savn_optimise(
                schedule,
                max_iters=4,
                random_seed=0,
                initial_temperature=0.0,
                cooling_rate=1.0,
                warm_start=False,
            )

        text = output.getvalue()
        self.assertIn("shifts=(-28, 28)", text)
        self.assertIn("shifts=(-14, 14)", text)
        self.assertIn("shifts=(-7, 7)", text)
        self.assertIn("shifts=(-3, 3)", text)


class MainTests(unittest.TestCase):
    @patch.object(annealing.baseline, "plot_comparison")
    @patch.object(annealing.baseline, "export_optimised_to_excel")
    @patch.object(annealing.baseline, "make_availability_table")
    @patch.object(annealing.baseline, "schedule_to_events_table")
    @patch.object(annealing, "savn_optimise")
    @patch.object(annealing.baseline, "evaluate_schedule")
    @patch.object(annealing.baseline, "compute_availability")
    @patch.object(annealing.baseline, "get_forecast_horizon")
    @patch.object(annealing.baseline, "load_heavy_schedule")
    def test_main_runs_annealing_and_exports_results(
        self,
        load_schedule,
        get_horizon,
        compute_availability,
        evaluate_schedule,
        optimise,
        events_table,
        availability_table,
        export_excel,
        plot_comparison,
    ):
        schedule = {"A1": [event("A", 10, 14, 0, 20)]}
        best = {"A1": [event("A", 11, 14, 0, 20)]}
        original_availability = np.array([1.0, 0.0])
        best_availability = np.array([1.0, 1.0])
        load_schedule.return_value = (schedule, "base-date")
        get_horizon.return_value = 20
        compute_availability.side_effect = [
            original_availability,
            best_availability,
        ]
        evaluate_schedule.return_value = (0.0, -0.5, 0.5)
        optimise.return_value = (
            best,
            (1.0, -0.0, 1.0),
            [{"iteration": 0}, {"iteration": 1}],
        )
        events_table.side_effect = ["original-events", "best-events"]
        availability_table.side_effect = [
            "original-table",
            "best-table",
        ]

        annealing.main()

        optimise.assert_has_calls([
            call(
                schedule,
                max_iters=400,
                random_seed=seed,
                initial_temperature=1.0,
                cooling_rate=0.95,
                warm_start=True,
            )
            for seed in annealing.TRIAL_SEEDS
        ])
        self.assertEqual(len(annealing.TRIAL_SEEDS), optimise.call_count)
        self.assertEqual(3, len(annealing.TRIAL_SEEDS))
        export_excel.assert_called_once()
        plot_comparison.assert_called_once_with(
            "original-table",
            "best-table",
        )


if __name__ == "__main__":
    unittest.main()
