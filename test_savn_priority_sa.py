import contextlib
import copy
import io
import math
import unittest
from unittest.mock import patch

import numpy as np
import savn_priority_based_selection as baseline
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

    def test_escape_selection_requires_a_lower_minimum(self):
        neighbors = [
            {"score": (18, -2.0, 20.0), "id": "plateau"},
            {"score": (17, -1.0, 20.0), "id": "floor-drop"},
        ]

        selected = annealing.select_escape_candidate(
            current_score=(18, -1.5, 20.0),
            neighbors=neighbors,
            temperature=0.6,
            rng=FakeRng([0.0]),
            require_lower_minimum=True,
        )

        self.assertEqual("floor-drop", selected["id"])

    def test_tightened_escape_skips_a_lower_worst_day(self):
        neighbors = [
            {"score": (17, -1.0, 20.0), "id": "floor-drop"},
        ]

        selected = annealing.select_escape_candidate(
            current_score=(18, -1.5, 20.0),
            neighbors=neighbors,
            temperature=5.0,
            rng=FakeRng([0.0]),
            tightened=True,
        )

        self.assertIsNone(selected)


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

    @patch.object(annealing.baseline, "savn_optimise")
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


class StartVectorTests(unittest.TestCase):
    def test_start_vector_sorts_aircraft_and_keeps_event_list_order(self):
        schedule = {
            "B1": [
                event("A", 40, 14, 0, 50),
                event("B", 10, 28, 0, 50),
            ],
            "A1": [event("C", 5, 84, 0, 20)],
        }

        self.assertEqual(
            (("A1", "C", 5), ("B1", "A", 40), ("B1", "B", 10)),
            annealing.start_vector(schedule),
        )

    def test_neighbor_that_restores_forbidden_starts_is_tabu(self):
        current = {
            "A1": [event("A", 11, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        }
        forbidden = annealing.start_vector({
            "A1": [event("A", 10, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        })
        neighbor = {
            "aircraft": "A1",
            "events": [event("A", 10, 14, 0, 20)],
        }

        self.assertTrue(
            annealing.is_tabu_neighbor(current, neighbor, forbidden),
        )

    def test_neighbor_with_a_different_start_is_not_tabu(self):
        current = {
            "A1": [event("A", 11, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        }
        forbidden = annealing.start_vector({
            "A1": [event("A", 10, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        })
        neighbor = {
            "aircraft": "A1",
            "events": [event("A", 12, 14, 0, 20)],
        }

        self.assertFalse(
            annealing.is_tabu_neighbor(current, neighbor, forbidden),
        )


class BasinHoppingTests(unittest.TestCase):
    @patch.object(annealing, "greedy_polish")
    def test_baseline_warm_start_is_protected_as_best(self, greedy_polish):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        baseline_score = baseline.evaluate_schedule(
            schedule,
            baseline.get_forecast_horizon(schedule),
        )
        greedy_polish.return_value = (
            schedule,
            baseline_score,
            [],
        )

        best, best_score, history = annealing.basin_hopping_optimise(
            schedule,
            escape_cycles=0,
            random_seed=42,
        )

        self.assertEqual(schedule, best)
        self.assertEqual(baseline_score, best_score)
        self.assertEqual("baseline", history[0]["phase"])

    @patch.object(annealing, "select_escape_candidate")
    @patch.object(annealing, "generate_vns_neighbors")
    @patch.object(annealing, "greedy_polish")
    def test_next_cycle_starts_from_protected_best_not_worse_local(
        self,
        greedy_polish,
        generate_vns_neighbors,
        select_escape_candidate,
    ):
        events = compliant_events()
        best_schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        worse_schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        worse_schedule["A1"][0]["start"] = 77
        cycle_starts = []

        def fake_polish(schedule, horizon, max_iters=400, tabu_vectors=(), **kwargs):
            if len(greedy_polish.mock_calls) == 1:
                return copy.deepcopy(best_schedule), (18.0, -1.0, 20.0), []
            return copy.deepcopy(worse_schedule), (18.0, -2.0, 20.0), []

        def fake_neighbors(schedule, availability, horizon, **kwargs):
            cycle_starts.append(schedule["A1"][0]["start"])
            return [{"score": (17.0, -1.0, 20.0)}]

        def fake_select(
            current_score,
            neighbors,
            temperature,
            rng,
            require_lower_minimum=False,
            **kwargs,
        ):
            if require_lower_minimum:
                return {
                    "aircraft": "A1",
                    "check": "A",
                    "old_start": 100,
                    "new_start": 90,
                    "events": [item.copy() for item in events],
                    "availability": np.ones(8),
                    "score": (17.0, -1.0, 20.0),
                }
            return None

        greedy_polish.side_effect = fake_polish
        generate_vns_neighbors.side_effect = fake_neighbors
        select_escape_candidate.side_effect = fake_select

        best, best_score, _ = annealing.basin_hopping_optimise(
            best_schedule,
            escape_cycles=2,
            plateau_moves=2,
            random_seed=99,
        )

        self.assertEqual(100, cycle_starts[0])
        self.assertEqual(100, cycle_starts[2])
        self.assertEqual((18.0, -1.0, 20.0), best_score)
        self.assertEqual(100, best["A1"][0]["start"])

    @patch.object(annealing, "select_escape_candidate")
    @patch.object(annealing, "generate_vns_neighbors")
    @patch.object(annealing, "greedy_polish")
    def test_plateau_moves_follow_one_required_floor_drop(
        self,
        greedy_polish,
        generate_vns_neighbors,
        select_escape_candidate,
    ):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        flags = []

        greedy_polish.return_value = (
            schedule,
            (18.0, -1.4, 21.0),
            [],
        )
        generate_vns_neighbors.return_value = [{"score": (17.0, -1.0, 20.0)}]

        def fake_select(
            current_score,
            neighbors,
            temperature,
            rng,
            require_lower_minimum=False,
            **kwargs,
        ):
            flags.append(require_lower_minimum)
            return {
                "aircraft": "A1",
                "check": "A",
                "old_start": 100,
                "new_start": 90,
                "events": [item.copy() for item in events],
                "availability": np.ones(8),
                "score": (17.0, -1.0, 20.0),
            }

        select_escape_candidate.side_effect = fake_select

        annealing.basin_hopping_optimise(
            schedule,
            escape_cycles=1,
            plateau_moves=4,
            random_seed=99,
        )

        self.assertEqual(
            [True, False, False, False, False],
            flags,
        )


class GreedyPolishTests(unittest.TestCase):
    def test_polish_stops_once_the_deadline_has_passed(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }

        _, _, history = annealing.greedy_polish(
            schedule,
            horizon=baseline.get_forecast_horizon(schedule),
            max_iters=3,
            deadline=0,
        )

        self.assertEqual(1, len(history))

    def test_polish_keeps_the_supplied_forecast_horizon(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        horizon = baseline.get_forecast_horizon(schedule)

        best, _, _ = annealing.greedy_polish(
            schedule,
            horizon=horizon,
            max_iters=1,
        )

        self.assertTrue(
            baseline.is_rule_compliant_schedule(best, horizon),
        )

    def test_empty_tabu_matches_current_no_tabu_polish(self):
        events = compliant_events()
        schedule = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        horizon = baseline.get_forecast_horizon(schedule)

        default_best, default_score, _ = annealing.greedy_polish(
            schedule,
            horizon=horizon,
            max_iters=1,
        )
        empty_tabu_best, empty_tabu_score, _ = annealing.greedy_polish(
            schedule,
            horizon=horizon,
            max_iters=1,
            tabu_vectors=(),
        )

        self.assertEqual(default_score, empty_tabu_score)
        self.assertEqual(
            annealing.start_vector(default_best),
            annealing.start_vector(empty_tabu_best),
        )

    @patch.object(annealing.baseline, "is_rule_compliant_schedule", return_value=True)
    @patch.object(annealing.baseline, "generate_neighbors")
    def test_tabu_refuses_restoring_neighbor_and_keeps_another_improve(
        self,
        generate_neighbors,
        _compliant,
    ):
        events = compliant_events()
        escaped = {
            "A1": [item.copy() for item in events],
            "A2": [item.copy() for item in events],
        }
        escaped["A1"][0]["start"] = 90
        horizon = baseline.get_forecast_horizon(escaped)
        current_availability = baseline.compute_availability(escaped, horizon)
        current_score = baseline.score_availability(current_availability)

        restore_events = [item.copy() for item in events]
        other_events = [item.copy() for item in events]
        other_events[0]["start"] = 80
        restore_availability = current_availability + 2
        other_availability = current_availability + 1
        forbidden = annealing.start_vector({
            "A1": restore_events,
            "A2": escaped["A2"],
        })

        generate_neighbors.return_value = [
            {
                "aircraft": "A1",
                "events": restore_events,
                "availability": restore_availability,
                "score": (
                    current_score[0] + 2,
                    current_score[1],
                    current_score[2],
                ),
            },
            {
                "aircraft": "A1",
                "events": other_events,
                "availability": other_availability,
                "score": (
                    current_score[0] + 1,
                    current_score[1],
                    current_score[2],
                ),
            },
        ]

        best, _, _ = annealing.greedy_polish(
            escaped,
            horizon=horizon,
            max_iters=1,
            tabu_vectors=(forbidden,),
        )

        self.assertEqual(80, best["A1"][0]["start"])
        self.assertNotEqual(
            forbidden,
            annealing.start_vector(best),
        )


class MainTests(unittest.TestCase):
    @patch.object(annealing.baseline, "plot_comparison")
    @patch.object(annealing.baseline, "export_optimised_to_excel")
    @patch.object(annealing.baseline, "make_availability_table")
    @patch.object(annealing.baseline, "schedule_to_events_table")
    @patch.object(annealing, "basin_hopping_optimise")
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

        optimise.assert_called_once_with(
            schedule,
            escape_cycles=15,
            plateau_moves=30,
            random_seed=99,
            escape_temperature=1.5,
            baseline_max_iters=400,
        )
        export_excel.assert_called_once()
        plot_comparison.assert_called_once_with(
            "original-table",
            "best-table",
        )


if __name__ == "__main__":
    unittest.main()
