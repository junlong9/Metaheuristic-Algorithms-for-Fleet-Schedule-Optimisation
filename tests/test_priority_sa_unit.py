"""Workbook-free unit tests for the recreated priority SA module."""

from __future__ import annotations

import importlib.util
import math
import random
import unittest
from pathlib import Path

import savn_priority_based_selection as baseline
import savn_priority_sa as sa


REPO_ROOT = Path(__file__).resolve().parents[1]
_CHASE_PATH = REPO_ROOT / ".scratch" / "priority-sa-hybrid" / "chase_std.py"
_spec = importlib.util.spec_from_file_location("chase_std", _CHASE_PATH)
chase_std = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chase_std)


class FakeRng:
    def __init__(self, value=0.0):
        self.value = value

    def random(self):
        return self.value


class AcceptCandidateTests(unittest.TestCase):
    def test_always_accepts_better_lex_score(self):
        current = (18.0, -1.41, 21.71)
        better_min = (19.0, -2.00, 21.00)
        better_std = (18.0, -1.30, 21.00)
        self.assertTrue(
            sa.accept_candidate(current, better_min, 0.0, FakeRng(1.0))
        )
        self.assertTrue(
            sa.accept_candidate(current, better_std, 0.0, FakeRng(1.0))
        )

    def test_staged_metropolis_uses_first_differing_component(self):
        current = (18.0, -1.40, 21.71)
        worse_min = (17.0, -1.00, 22.00)
        temperature = 1.5
        threshold = math.exp(-1.0 / temperature)
        self.assertTrue(
            sa.accept_candidate(
                current,
                worse_min,
                temperature,
                FakeRng(threshold - 1e-9),
            )
        )
        self.assertFalse(
            sa.accept_candidate(
                current,
                worse_min,
                temperature,
                FakeRng(threshold + 1e-9),
            )
        )

    def test_equal_score_is_accepted(self):
        score = (18.0, -1.405740, 21.713010)
        self.assertTrue(sa.accept_candidate(score, score, 1.5, FakeRng(1.0)))


class StartVectorTests(unittest.TestCase):
    def test_start_vector_changes_when_a_start_moves(self):
        schedule = {
            "A1": [{"check": "A", "start": 10}],
            "A2": [{"check": "B", "start": 20}],
        }
        moved = {
            "A1": [{"check": "A", "start": 11}],
            "A2": [{"check": "B", "start": 20}],
        }
        self.assertNotEqual(sa.start_vector(schedule), sa.start_vector(moved))
        self.assertEqual(len({sa.start_vector(schedule)}), 1)


class FingerprintTests(unittest.TestCase):
    def test_proxy_fingerprint_is_labelled_proxy(self):
        fingerprint = {
            "original_min": 12.0,
            "original_avg": 21.690497,
            "n_events": 279,
            "horizon": 4503,
            "base_date": "2026-01-15",
        }
        klass, reason = chase_std.classify_instance(
            fingerprint,
            hillclimb_min=16.0,
        )
        self.assertEqual(klass, "PROXY")
        self.assertIn("seed-42", reason)

    def test_real_fingerprint_is_labelled_real(self):
        fingerprint = {
            "original_min": 15.0,
            "original_avg": 21.713010,
            "n_events": 278,
            "horizon": 4480,
            "base_date": "2026-01-21",
        }
        klass, reason = chase_std.classify_instance(
            fingerprint,
            hillclimb_min=18.0,
        )
        self.assertEqual(klass, "REAL")
        self.assertIn("278", reason)


class ToyScheduleTests(unittest.TestCase):
    def _toy_aircraft(self, first_due, n_events, horizon):
        seed = []
        start = first_due
        for index in range(n_events):
            seed.append({
                "check": "A",
                "start": start,
                "duration": 14,
                "earliest_start": 0,
                "latest_start": first_due if index == 0 else first_due + 8000,
            })
            start += 220
        rebuilt = baseline.rebuild_aircraft_schedule(seed, horizon)
        self.assertIsNotNone(rebuilt)
        return rebuilt

    def test_feasible_neighbors_and_polish_on_toy_instance(self):
        horizon = 3000
        schedule = {
            "AC1": self._toy_aircraft(100, 4, horizon),
            "AC2": self._toy_aircraft(180, 4, horizon),
            "AC3": self._toy_aircraft(250, 4, horizon),
        }
        self.assertTrue(baseline.is_rule_compliant_schedule(schedule, horizon))
        availability = baseline.compute_availability(schedule, horizon)
        neighbors = sa.generate_feasible_neighbors(
            schedule,
            availability,
            horizon,
            (-28, 28),
        )
        self.assertTrue(neighbors)
        polished, score, _, _ = sa.greedy_polish(
            schedule,
            horizon,
            max_iters=20,
            tabu_vectors={sa.start_vector(schedule)},
        )
        self.assertTrue(baseline.is_rule_compliant_schedule(polished, horizon))
        self.assertEqual(len(score), 3)

        rng = random.Random(0)
        accepted, escaped, _, escaped_score, info = sa.select_escape_candidate(
            schedule,
            availability,
            sa.score_tuple(baseline.score_availability(availability)),
            horizon,
            temperature=2.0,
            rng=rng,
            require_lower_minimum=False,
        )
        self.assertIn("accepted", info)
        if accepted:
            self.assertTrue(
                baseline.is_rule_compliant_schedule(escaped, horizon)
            )
            self.assertEqual(len(escaped_score), 3)


if __name__ == "__main__":
    unittest.main()
