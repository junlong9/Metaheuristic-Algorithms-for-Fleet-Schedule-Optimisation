from pathlib import Path
import copy
import csv
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
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
                "pairs_28": (
                    (-28, 28), (-14, 14), (-7, 7), (-3, 3), (-1, 1),
                ),
                "pairs_14": ((-14, 14), (-7, 7), (-3, 3), (-1, 1)),
                "pairs_7": ((-7, 7), (-3, 3), (-1, 1)),
                "pairs_3": ((-3, 3), (-1, 1)),
                "pairs_1": ((-1, 1),),
                "pairs_42": (
                    (-42, 42), (-28, 28), (-14, 14), (-7, 7), (-3, 3), (-1, 1),
                ),
                "pairs_28_fine_first": (
                    (-1, 1), (-3, 3), (-7, 7), (-14, 14), (-28, 28),
                ),
                "single_set_28": (
                    (-28, -14, -7, -3, -1, 1, 3, 7, 14, 28),
                ),
                "overlap_14": (
                    (-14, -7, 7, 14),
                    (-7, -3, 3, 7),
                    (-3, -1, 1, 3),
                ),
            },
        )
        self.assertEqual(study.BUDGETS, (200, 400, 800))
        self.assertEqual(study.EXTENSION_BUDGET, 1600)

    def test_original_strategies_keep_their_keys_and_order(self):
        self.assertEqual(
            [strategy.key for strategy in study.STRATEGIES[:4]],
            [
                "historical_half_step",
                "live_wide_to_fine",
                "dense_pairs",
                "half_step_plus_42",
            ],
        )

    def test_labels_name_the_baseline_and_avoid_live_wording(self):
        labels = {strategy.key: strategy.label for strategy in study.STRATEGIES}
        self.assertEqual(labels["pairs_28"], "Baseline (±28, ±14, ±7, ±3, ±1)")
        self.assertEqual(
            labels["live_wide_to_fine"],
            "Wide-to-fine ladder (±56 to ±1)",
        )
        self.assertEqual(
            labels["historical_half_step"],
            "Overlapping half-step sets",
        )
        for key, label in labels.items():
            self.assertNotRegex(label.lower(), "current|live")
            if key != "pairs_28":
                self.assertNotIn("baseline (", label.lower())

    def test_trial_matrix_has_each_configuration_once(self):
        matrix = study.build_trial_matrix()
        keys = [
            (dataset, strategy.key, budget)
            for dataset, strategy, budget in matrix
        ]
        self.assertEqual(len(keys), 117)
        self.assertEqual(len(set(keys)), 117)
        self.assertEqual(study.EXPECTED_MATRIX_SIZE, 117)
        self.assertEqual(
            {dataset for dataset, _, _ in keys},
            {"original", "moderate", "wide"},
        )

    def test_extension_only_covers_capped_largest_budget_trials(self):
        trials = [
            {
                "dataset": "wide",
                "strategy_key": "pairs_1",
                "max_iters": 800,
                "stop_reason": "iteration_cap",
            },
            {
                "dataset": "wide",
                "strategy_key": "pairs_3",
                "max_iters": 800,
                "stop_reason": "local_exhaustion",
            },
            {
                "dataset": "original",
                "strategy_key": "pairs_3",
                "max_iters": 400,
                "stop_reason": "iteration_cap",
            },
        ]
        extension = study.build_extension_matrix(trials)
        self.assertEqual(
            [(dataset, strategy.key, budget) for dataset, strategy, budget in extension],
            [("wide", "pairs_1", 1600)],
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


class TrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = study.load_study_inputs(ROOT)

    def test_independent_availability_matches_production_calculation(self):
        dataset = self.inputs.datasets[0]
        expected = study.optimiser.compute_availability(
            dataset.schedule,
            self.inputs.horizon,
        )
        actual = study.independent_availability(
            dataset.schedule,
            self.inputs.horizon,
        )
        np.testing.assert_array_equal(actual, expected)

    def test_schedule_hash_ignores_dictionary_insertion_order(self):
        first = {
            "B": [{
                "check": "A",
                "start": 1,
                "duration": 14,
                "earliest_start": 0,
                "latest_start": 2,
            }],
            "A": [{
                "check": "A",
                "start": 2,
                "duration": 14,
                "earliest_start": 0,
                "latest_start": 3,
            }],
        }
        second = {"A": first["A"], "B": first["B"]}
        self.assertEqual(
            study.schedule_sha256(first),
            study.schedule_sha256(second),
        )

    def test_one_iteration_trial_is_real_deterministic_and_compliant(self):
        dataset = self.inputs.datasets[0]
        result = study.run_trial(
            dataset,
            study.STRATEGIES[0],
            1,
            horizon=self.inputs.horizon,
            scoring_start=self.inputs.scoring_start,
            scoring_end=self.inputs.scoring_end,
            clock=iter((10.0, 12.5)).__next__,
        )
        self.assertEqual(result["trial_key"], "original:historical_half_step:1")
        self.assertEqual(result["elapsed_seconds"], 2.5)
        self.assertLessEqual(result["accepted_moves"], 1)
        self.assertTrue(result["rule_compliant"])
        self.assertEqual(
            result["stop_reason"],
            "iteration_cap" if result["accepted_moves"] else "local_exhaustion",
        )
        self.assertEqual(
            result["natural_exhaustion"],
            result["stop_reason"] == "local_exhaustion",
        )
        scores = [tuple(item["score"]) for item in result["trace"]]
        self.assertTrue(
            all(left < right for left, right in zip(scores, scores[1:]))
        )

    def test_repeated_trial_has_identical_deterministic_endpoint(self):
        dataset = self.inputs.datasets[0]
        results = [
            study.run_trial(
                dataset,
                study.STRATEGIES[0],
                1,
                horizon=self.inputs.horizon,
                scoring_start=self.inputs.scoring_start,
                scoring_end=self.inputs.scoring_end,
                clock=iter((10.0, 11.0)).__next__,
            )
            for _ in range(2)
        ]
        self.assertEqual(
            results[0]["endpoint_sha256"],
            results[1]["endpoint_sha256"],
        )
        self.assertEqual(results[0]["lexicographic_score"], results[1]["lexicographic_score"])
        self.assertEqual(results[0]["trace"], results[1]["trace"])


def fake_trial(dataset, strategy, max_iters, **_kwargs):
    strategy_index = next(
        index
        for index, item in enumerate(study.STRATEGIES)
        if item.key == strategy.key
    )
    score = [
        20.0 - strategy_index,
        -(1.0 + min(max_iters, 400) / 10000),
        21.0,
    ]
    return {
        "trial_key": f"{dataset.key}:{strategy.key}:{max_iters}",
        "dataset": dataset.key,
        "dataset_label": dataset.label,
        "strategy_key": strategy.key,
        "strategy_label": strategy.label,
        "shift_sets": [list(level) for level in strategy.shift_sets],
        "max_iters": max_iters,
        "min_availability": int(score[0]),
        "availability_std": -score[1],
        "mean_availability": score[2],
        "lexicographic_score": score,
        "accepted_moves": 2,
        "outer_passes": 3,
        "natural_exhaustion": True,
        "stop_reason": "local_exhaustion",
        "elapsed_seconds": float(max_iters),
        "rule_compliant": True,
        "endpoint_sha256": strategy.key,
        "trace": [{"iteration": 0, "score": score}],
    }


def fake_trial_capped_pairs_1(dataset, strategy, max_iters, **kwargs):
    result = fake_trial(dataset, strategy, max_iters, **kwargs)
    if strategy.key == "pairs_1" and max_iters <= 800:
        result["natural_exhaustion"] = False
        result["stop_reason"] = "iteration_cap"
    return result


class StudyOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = study.load_study_inputs(ROOT)

    def test_run_study_calls_each_of_117_trials_once(self):
        calls = []

        def recording_runner(*args, **kwargs):
            calls.append((args[0].key, args[1].key, args[2]))
            return fake_trial(*args, **kwargs)

        payload = study.run_study(self.inputs, recording_runner)
        self.assertEqual(len(calls), 117)
        self.assertEqual(len(set(calls)), 117)
        self.assertEqual(len(payload["trials"]), 117)
        self.assertEqual(payload["extension_trials"], [])

    def test_capped_800_trials_are_rerun_at_1600(self):
        payload = study.run_study(self.inputs, fake_trial_capped_pairs_1)
        self.assertEqual(
            payload["extension_trials"],
            [
                "original:pairs_1:1600",
                "moderate:pairs_1:1600",
                "wide:pairs_1:1600",
            ],
        )
        self.assertEqual(len(payload["trials"]), 120)
        self.assertTrue(all("dataset_rank" in item for item in payload["trials"]))

    def test_parallel_run_matches_serial_run(self):
        serial = study.run_study(self.inputs, fake_trial, workers=1)
        parallel = study.run_study(self.inputs, fake_trial, workers=2)
        self.assertEqual(serial["trials"], parallel["trials"])
        self.assertEqual(serial["recommendations"], parallel["recommendations"])

    def test_shared_recommendation_needs_all_three_datasets(self):
        trials = []
        for dataset in study.DATASET_KEYS:
            for budget, rank in ((400, 2), (1600, 1)):
                trials.append({
                    "trial_key": f"{dataset}:pairs_28:{budget}",
                    "dataset": dataset,
                    "strategy_key": "pairs_28",
                    "max_iters": budget,
                    "dataset_rank": rank,
                    "elapsed_seconds": 1.0,
                })
        trials = [
            item for item in trials
            if not (item["max_iters"] == 1600 and item["dataset"] == "wide")
        ]
        recommendations = study.choose_recommendations(trials)
        self.assertEqual(
            recommendations["shared"],
            {"strategy_key": "pairs_28", "max_iters": 400},
        )
        self.assertEqual(
            recommendations["dataset_winners"]["original"],
            "original:pairs_28:1600",
        )

    def test_exact_ties_prefer_the_simpler_strategy(self):
        trials = [
            {
                "trial_key": f"{dataset}:{key}:400",
                "dataset": dataset,
                "strategy_key": key,
                "max_iters": 400,
                "dataset_rank": 1,
                "elapsed_seconds": seconds,
            }
            for dataset in study.DATASET_KEYS
            for key, seconds in (("live_wide_to_fine", 1.0), ("pairs_28", 9.0))
        ]
        recommendations = study.choose_recommendations(trials)
        self.assertEqual(recommendations["shared"]["strategy_key"], "pairs_28")

    def test_exact_score_ties_share_competition_rank(self):
        trials = [
            {"dataset": "original", "lexicographic_score": [18, -1.2, 21]},
            {"dataset": "original", "lexicographic_score": [18, -1.2, 21]},
            {"dataset": "original", "lexicographic_score": [17, -1.0, 22]},
        ]
        study.assign_dataset_ranks(trials)
        self.assertEqual([item["dataset_rank"] for item in trials], [1, 1, 3])

    def test_json_and_csv_cover_the_same_117_trials(self):
        payload = study.run_study(self.inputs, fake_trial)
        with tempfile.TemporaryDirectory() as directory:
            paths = study.write_machine_outputs(payload, Path(directory))
            saved = json.loads(paths["json"].read_text(encoding="utf-8"))
            with paths["csv"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(saved["trials"]), 117)
        self.assertEqual(len(rows), 117)
        self.assertTrue(
            all("natural_exhaustion" in trial for trial in saved["trials"])
        )
        self.assertTrue(
            all("natural_exhaustion" in row for row in rows)
        )
        self.assertEqual(
            {row["trial_key"] for row in rows},
            {trial["trial_key"] for trial in saved["trials"]},
        )


class PresentationOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inputs = study.load_study_inputs(ROOT)
        cls.payload = study.run_study(inputs, fake_trial)

    def test_matplotlib_is_headless(self):
        self.assertEqual(study.matplotlib.get_backend().lower(), "agg")

    def test_create_charts_writes_three_nonempty_png_files(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = study.create_charts(
                self.payload["trials"],
                Path(directory),
            )
            self.assertEqual(
                set(paths),
                {"ranked_quality", "budget_convergence", "runtime"},
            )
            for path in paths.values():
                self.assertEqual(path.suffix, ".png")
                self.assertGreater(path.stat().st_size, 1_000)

    def test_analysis_module_has_no_report_writer(self):
        self.assertFalse(hasattr(study, "build_report"))
        self.assertNotIn(
            "vn-hyperparameter-analysis.docx",
            study.ARTIFACT_NAMES,
        )


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inputs = study.load_study_inputs(ROOT)
        cls.payload = study.run_study(inputs, fake_trial)

    def test_trial_error_names_the_configuration(self):
        inputs = study.load_study_inputs(ROOT)

        def fail(*_args, **_kwargs):
            raise ValueError("deliberate failure")

        with self.assertRaisesRegex(
            RuntimeError,
            "original:historical_half_step:200: trial failed",
        ):
            study.run_study(inputs, fail)

    def test_publish_does_not_leave_partial_outputs_on_chart_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "published"
            with patch.object(
                study,
                "create_charts",
                side_effect=RuntimeError("chart failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "chart failed"):
                    study.publish_outputs(self.payload, output)
            self.assertFalse(output.exists())

    def test_mid_publication_failure_restores_previous_artifact_set(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            output = parent / "published"
            previous = copy.deepcopy(self.payload)
            previous["study"] = "previous complete publication"
            previous["trials"][0]["elapsed_seconds"] = -1.0
            study.publish_outputs(previous, output)
            before = {
                path.name: path.read_bytes()
                for path in output.iterdir()
            }

            real_replace = os.replace
            failed = False

            def fail_output_promotion(source, destination):
                nonlocal failed
                if Path(destination) == output and not failed:
                    failed = True
                    raise OSError("simulated replacement failure")
                return real_replace(source, destination)

            with patch.object(
                study.os,
                "replace",
                side_effect=fail_output_promotion,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "simulated replacement failure",
                ):
                    study.publish_outputs(self.payload, output)

            after = {
                path.name: path.read_bytes()
                for path in output.iterdir()
            }
            self.assertEqual(after, before)
            self.assertEqual(
                list(parent.glob(f".{output.name}-*")),
                [],
            )

    def test_publish_writes_exactly_five_analysis_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "published"
            study.publish_outputs(self.payload, output)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "results.json",
                    "summary.csv",
                    "ranked-quality.png",
                    "budget-convergence.png",
                    "runtime.png",
                },
            )
            study.validate_generated_outputs(self.payload, output)

    def test_publish_preserves_existing_static_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "published"
            output.mkdir()
            report = output / "vn-hyperparameter-analysis.docx"
            report.write_bytes(b"existing static report")

            study.publish_outputs(self.payload, output)

            self.assertEqual(report.read_bytes(), b"existing static report")
            self.assertEqual(
                {path.name for path in output.iterdir()},
                set(study.ARTIFACT_NAMES) | {report.name},
            )

    def test_default_output_dir_is_the_step_size_study_folder(self):
        self.assertEqual(
            study.OUTPUT_DIR,
            ROOT / "docs/reports/vn-step-size-study",
        )
        self.assertEqual(study.parse_args([]).output_dir, study.OUTPUT_DIR)

    def test_main_runs_study_and_publishes_outputs(self):
        with (
            patch.object(study, "load_study_inputs", return_value="inputs") as load,
            patch.object(study, "run_study", return_value=self.payload) as run,
            patch.object(study, "publish_outputs") as publish,
        ):
            self.assertEqual(study.main(["--workers", "3"]), 0)
        load.assert_called_once_with(study.ROOT)
        run.assert_called_once_with("inputs", workers=3)
        publish.assert_called_once_with(self.payload, study.OUTPUT_DIR)

    def test_main_accepts_an_output_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(study, "load_study_inputs", return_value="inputs"),
                patch.object(study, "run_study", return_value=self.payload),
                patch.object(study, "publish_outputs") as publish,
            ):
                study.main(["--output-dir", directory, "--workers", "1"])
        publish.assert_called_once_with(self.payload, Path(directory))


if __name__ == "__main__":
    unittest.main()
