import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import copy
import unittest
from unittest.mock import patch

import numpy as np
import savn_basin_hopping as basin
import savn_priority_sa as annealing
import vn_priority_based_selection as baseline


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


class ModuleOwnershipTests(unittest.TestCase):
    def test_algorithm_functions_live_in_their_focused_modules(self):
        self.assertTrue(hasattr(basin, "basin_hopping_optimise"))
        self.assertTrue(hasattr(basin, "greedy_polish"))
        self.assertFalse(hasattr(annealing, "basin_hopping_optimise"))
        self.assertFalse(hasattr(annealing, "greedy_polish"))


class EscapeSelectionTests(unittest.TestCase):
    def test_escape_selection_requires_a_lower_minimum(self):
        neighbors = [
            {"score": (18, -2.0, 20.0), "id": "plateau"},
            {"score": (17, -1.0, 20.0), "id": "floor-drop"},
        ]

        selected = basin.select_escape_candidate(
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

        selected = basin.select_escape_candidate(
            current_score=(18, -1.5, 20.0),
            neighbors=neighbors,
            temperature=5.0,
            rng=FakeRng([0.0]),
            tightened=True,
        )

        self.assertIsNone(selected)


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
            basin.start_vector(schedule),
        )

    def test_neighbor_that_restores_forbidden_starts_is_tabu(self):
        current = {
            "A1": [event("A", 11, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        }
        forbidden = basin.start_vector({
            "A1": [event("A", 10, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        })
        neighbor = {
            "aircraft": "A1",
            "events": [event("A", 10, 14, 0, 20)],
        }

        self.assertTrue(
            basin.is_tabu_neighbor(current, neighbor, forbidden),
        )

    def test_neighbor_with_a_different_start_is_not_tabu(self):
        current = {
            "A1": [event("A", 11, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        }
        forbidden = basin.start_vector({
            "A1": [event("A", 10, 14, 0, 20)],
            "A2": [event("A", 10, 14, 0, 20)],
        })
        neighbor = {
            "aircraft": "A1",
            "events": [event("A", 12, 14, 0, 20)],
        }

        self.assertFalse(
            basin.is_tabu_neighbor(current, neighbor, forbidden),
        )


class BasinHoppingTests(unittest.TestCase):
    @patch.object(basin, "greedy_polish")
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

        best, best_score, history = basin.basin_hopping_optimise(
            schedule,
            escape_cycles=0,
            random_seed=42,
        )

        self.assertEqual(schedule, best)
        self.assertEqual(baseline_score, best_score)
        self.assertEqual("baseline", history[0]["phase"])

    @patch.object(basin, "select_escape_candidate")
    @patch.object(basin, "generate_vns_neighbors")
    @patch.object(basin, "greedy_polish")
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

        best, best_score, _ = basin.basin_hopping_optimise(
            best_schedule,
            escape_cycles=2,
            plateau_moves=2,
            random_seed=99,
        )

        self.assertEqual(100, cycle_starts[0])
        self.assertEqual(100, cycle_starts[2])
        self.assertEqual((18.0, -1.0, 20.0), best_score)
        self.assertEqual(100, best["A1"][0]["start"])

    @patch.object(basin, "select_escape_candidate")
    @patch.object(basin, "generate_vns_neighbors")
    @patch.object(basin, "greedy_polish")
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

        basin.basin_hopping_optimise(
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

        _, _, history = basin.greedy_polish(
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

        best, _, _ = basin.greedy_polish(
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

        default_best, default_score, _ = basin.greedy_polish(
            schedule,
            horizon=horizon,
            max_iters=1,
        )
        empty_tabu_best, empty_tabu_score, _ = basin.greedy_polish(
            schedule,
            horizon=horizon,
            max_iters=1,
            tabu_vectors=(),
        )

        self.assertEqual(default_score, empty_tabu_score)
        self.assertEqual(
            basin.start_vector(default_best),
            basin.start_vector(empty_tabu_best),
        )

    @patch.object(basin.baseline, "is_rule_compliant_schedule", return_value=True)
    @patch.object(basin.baseline, "generate_neighbors")
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
        forbidden = basin.start_vector({
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

        best, _, _ = basin.greedy_polish(
            escaped,
            horizon=horizon,
            max_iters=1,
            tabu_vectors=(forbidden,),
        )

        self.assertEqual(80, best["A1"][0]["start"])
        self.assertNotEqual(
            forbidden,
            basin.start_vector(best),
        )


if __name__ == "__main__":
    unittest.main()
