from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis import vn_hyperparameter_analysis as study


class MatrixTests(unittest.TestCase):
    def test_strategy_definitions_match_the_approved_matrix(self):
        actual = {
            strategy.key: strategy.shift_sets
            for strategy in study.STRATEGIES
        }
        self.assertEqual(
            actual,
            {
                "historical_half_step": (
                    (-28, -14, 14, 28),
                    (-14, -7, 7, 14),
                    (-7, -3, 3, 7),
                    (-3, -1, 1, 3),
                ),
                "live_wide_to_fine": (
                    (-56, 56),
                    (-42, 42),
                    (-28, 28),
                    (-14, 14),
                    (-7, 7),
                    (-3, 3),
                    (-1, 1),
                ),
                "dense_pairs": (
                    (-28, 28),
                    (-21, 21),
                    (-14, 14),
                    (-7, 7),
                    (-3, 3),
                    (-1, 1),
                ),
                "half_step_plus_42": (
                    (-42, 42),
                    (-28, -14, 14, 28),
                    (-14, -7, 7, 14),
                    (-7, -3, 3, 7),
                    (-3, -1, 1, 3),
                ),
            },
        )
        self.assertEqual(study.BUDGETS, (200, 400, 800))

    def test_trial_matrix_has_each_configuration_once(self):
        matrix = study.build_trial_matrix()
        keys = [
            (dataset, strategy.key, budget)
            for dataset, strategy, budget in matrix
        ]
        self.assertEqual(len(keys), 36)
        self.assertEqual(len(set(keys)), 36)
        self.assertEqual(
            {dataset for dataset, _, _ in keys},
            {"original", "moderate", "wide"},
        )


class InputLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = study.load_study_inputs(ROOT)

    def test_inputs_use_the_common_reporting_window(self):
        inputs = self.inputs
        self.assertEqual(
            inputs.origin + pd.Timedelta(days=inputs.scoring_start),
            pd.Timestamp("2026-01-21"),
        )
        self.assertEqual(
            inputs.origin + pd.Timedelta(days=inputs.scoring_end),
            pd.Timestamp("2038-01-18"),
        )
        self.assertEqual(
            tuple(dataset.key for dataset in inputs.datasets),
            ("original", "moderate", "wide"),
        )

    def test_stagger_inputs_keep_saved_opening_state(self):
        for dataset in self.inputs.datasets[1:]:
            for events in dataset.schedule.values():
                self.assertIn("_origin", events[0])
                self.assertIn("_opening", events[0])

    def test_every_initial_schedule_is_rule_compliant(self):
        for dataset in self.inputs.datasets:
            self.assertTrue(
                study.optimiser.is_rule_compliant_schedule(
                    dataset.schedule,
                    self.inputs.horizon,
                )
            )
        self.assertEqual(
            set(self.inputs.input_hashes),
            {"original", "moderate", "wide", "opening_state", "production"},
        )

    def test_missing_inputs_name_the_missing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                FileNotFoundError,
                "opening_state: missing input",
            ):
                study.load_study_inputs(Path(directory))


if __name__ == "__main__":
    unittest.main()
