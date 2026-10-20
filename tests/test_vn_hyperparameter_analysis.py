from pathlib import Path
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
