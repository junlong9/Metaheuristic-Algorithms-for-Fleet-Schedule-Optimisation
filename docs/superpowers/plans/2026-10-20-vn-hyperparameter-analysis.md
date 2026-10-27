# VN Priority Hyperparameter Analysis Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a small deterministic analysis that runs 36 VN hyperparameter trials across three maintenance datasets and produces machine-readable results, three charts, and an approximately ten-page Word report.

**Architecture:** One importable command-line script, `analysis/vn_hyperparameter_analysis.py`, owns configuration, matched-window dataset loading, the injectable study loop, validation, ranking, output generation, and report writing. One `unittest` module drives the implementation test-first; the script reuses scheduling primitives from `vn_priority_based_selection.py` without editing that production module.

**Tech Stack:** Python 3, standard-library `unittest`, NumPy, pandas, openpyxl, Matplotlib with the `Agg` backend, and python-docx.

## Global Constraints

- Do not modify `vn_priority_based_selection.py`, any input workbook, or `.scratch/initial-maintenance-stagger/schedule-data.json`.
- Add no package manifest: this repository has none. Check the existing environment first and install NumPy, pandas, openpyxl, Matplotlib, or python-docx only when an import is missing.
- Keep all implementation in one focused script and all automated tests in one focused test file; do not introduce a framework or helper package.
- Run exactly one deterministic quality run for each of four shift strategies × three iteration budgets × three datasets. Do not vary selection policy or add repeated trials.
- Use the common reporting window 2026-01-21 through 2038-01-18, inclusive, while retaining full crossing checks in the model horizon.
- Preserve saved opening clocks and sequence positions for moderate and wide stagger, and freeze checks commenced before the reporting window.
- Rank by `(minimum availability, -population standard deviation, mean availability)`. Runtime is one observed search duration and never outranks schedule quality.
- Publish final artifacts only after all 36 trials and validations succeed.
- Generate only:
  - `analysis/vn_hyperparameter_analysis.py`
  - `tests/test_vn_hyperparameter_analysis.py`
  - files under `docs/reports/vn-hyperparameter-analysis/`
- Use `python3` for repository commands. The missing-dependency error shown to users must contain the spec-required command `python -m pip install numpy pandas openpyxl matplotlib python-docx`.

---

## File map

- Create `analysis/vn_hyperparameter_analysis.py`: configuration, input alignment, deterministic search, validation, ranking, serialization, charts, DOCX generation, atomic publication, and CLI.
- Create `tests/test_vn_hyperparameter_analysis.py`: focused unit and integration tests for every public analysis function and critical failure path.
- Create `docs/reports/vn-hyperparameter-analysis/results.json`: complete metadata, matrix, traces, hashes, 36 trial records, and recommendations.
- Create `docs/reports/vn-hyperparameter-analysis/summary.csv`: one flat row per trial.
- Create `docs/reports/vn-hyperparameter-analysis/ranked-quality.png`: per-dataset ranked smoothness plots labelled with minimum availability.
- Create `docs/reports/vn-hyperparameter-analysis/budget-convergence.png`: per-dataset accepted moves and exhaustion by budget.
- Create `docs/reports/vn-hyperparameter-analysis/runtime.png`: per-dataset single observed runtime.
- Create `docs/reports/vn-hyperparameter-analysis/vn-hyperparameter-analysis.docx`: final 9–11 page report.
- Preserve `vn_priority_based_selection.py` byte-for-byte.

### Shared interfaces

The tasks below define these exact interfaces in
`analysis/vn_hyperparameter_analysis.py`:

- `Strategy(key: str, label: str, shift_sets: tuple[tuple[int, ...], ...])`
- `LoadedDataset(key: str, label: str, schedule: dict[str, list[dict[str, object]]])`
- `StudyInputs(datasets, origin, horizon, scoring_start, scoring_end, input_hashes)`
- `build_trial_matrix() -> list[tuple[str, Strategy, int]]`
- `load_study_inputs(root: Path = ROOT) -> StudyInputs`
- `run_trial(dataset, strategy, max_iters, *, horizon, scoring_start, scoring_end, clock=time.perf_counter) -> dict[str, object]`
- `run_study(inputs, trial_runner=run_trial) -> dict[str, object]`
- `write_machine_outputs(payload, output_dir) -> dict[str, Path]`
- `create_charts(trials, output_dir) -> dict[str, Path]`
- `build_report(payload, charts, output_path) -> None`
- `publish_outputs(payload, output_dir=OUTPUT_DIR) -> None`
- `main() -> int`

## Task 1: Establish configuration and the exact 36-trial matrix

**Files:**
- Create: `tests/test_vn_hyperparameter_analysis.py`
- Create: `analysis/vn_hyperparameter_analysis.py`

**Interfaces:**
- Produces: `Strategy`, `STRATEGIES`, `BUDGETS`, `DATASET_KEYS`, and `build_trial_matrix()`
- Consumes: no implementation from later tasks

- [ ] **Step 1: Check dependencies without adding packaging**

Run:

```bash
python3 -c "import numpy, pandas, openpyxl, matplotlib, docx; print('analysis dependencies available')"
```

Expected: `analysis dependencies available`.

Only if that command fails, run:

```bash
python3 -m pip install numpy pandas openpyxl matplotlib python-docx
```

Do not create or modify a requirements file.

- [ ] **Step 2: Write the failing matrix tests**

Create `tests/test_vn_hyperparameter_analysis.py` with:

```python
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
```

- [ ] **Step 3: Run the tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.MatrixTests -v
```

Expected: ERROR with `ImportError` because
`analysis.vn_hyperparameter_analysis` does not exist.

- [ ] **Step 4: Implement the configuration**

Create `analysis/vn_hyperparameter_analysis.py` with an import guard that raises
`SystemExit` containing the required install command, select `Agg` before
importing `pyplot`, then add:

```python
from __future__ import annotations

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import openpyxl
    import pandas as pd
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Inches, Pt
except ImportError as exc:
    raise SystemExit(
        f"Missing analysis dependency: {exc.name}. Install with: "
        "python -m pip install numpy pandas openpyxl matplotlib python-docx"
    ) from exc

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import copy
import csv
import hashlib
import json
import os
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import vn_priority_based_selection as optimiser

OUTPUT_DIR = ROOT / "docs/reports/vn-hyperparameter-analysis"
STATE_PATH = ROOT / ".scratch/initial-maintenance-stagger/schedule-data.json"
FORECAST_START = pd.Timestamp("2026-01-21")
FORECAST_END = pd.Timestamp("2038-01-18")
DATASET_KEYS = ("original", "moderate", "wide")
BUDGETS = (200, 400, 800)


@dataclass(frozen=True)
class Strategy:
    key: str
    label: str
    shift_sets: tuple[tuple[int, ...], ...]


STRATEGIES = (
    Strategy(
        "historical_half_step",
        "Earlier tuned baseline",
        (
            (-28, -14, 14, 28),
            (-14, -7, 7, 14),
            (-7, -3, 3, 7),
            (-3, -1, 1, 3),
        ),
    ),
    Strategy(
        "live_wide_to_fine",
        "Current live ladder",
        (
            (-56, 56), (-42, 42), (-28, 28), (-14, 14),
            (-7, 7), (-3, 3), (-1, 1),
        ),
    ),
    Strategy(
        "dense_pairs",
        "Dense paired ladder",
        (
            (-28, 28), (-21, 21), (-14, 14),
            (-7, 7), (-3, 3), (-1, 1),
        ),
    ),
    Strategy(
        "half_step_plus_42",
        "Earlier tuned baseline plus ±42",
        (
            (-42, 42),
            (-28, -14, 14, 28),
            (-14, -7, 7, 14),
            (-7, -3, 3, 7),
            (-3, -1, 1, 3),
        ),
    ),
)


def build_trial_matrix() -> list[tuple[str, Strategy, int]]:
    matrix = [
        (dataset, strategy, budget)
        for dataset in DATASET_KEYS
        for strategy in STRATEGIES
        for budget in BUDGETS
    ]
    keys = [(dataset, strategy.key, budget) for dataset, strategy, budget in matrix]
    if len(matrix) != 36 or len(set(keys)) != 36:
        raise ValueError("Experiment matrix must contain 36 unique trials.")
    return matrix
```

- [ ] **Step 5: Run the focused tests to verify GREEN**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.MatrixTests -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 6: Commit the matrix**

```bash
git add analysis/vn_hyperparameter_analysis.py tests/test_vn_hyperparameter_analysis.py
git commit -m "feat: define VN hyperparameter matrix"
```

## Task 2: Load and align all three datasets

**Files:**
- Modify: `analysis/vn_hyperparameter_analysis.py`
- Modify: `tests/test_vn_hyperparameter_analysis.py`

**Interfaces:**
- Produces: `LoadedDataset`, `StudyInputs`, `load_study_inputs()`, and `sha256_file()`
- Consumes: production loader and rule validator; saved stagger opening state

- [ ] **Step 1: Add failing input-loading tests**

Add:

```python
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
```

Also add `import pandas as pd` and `import tempfile` to the test imports.

- [ ] **Step 2: Run the tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.InputLoadingTests -v
```

Expected: FAIL because `load_study_inputs` and its data classes are undefined.

- [ ] **Step 3: Implement matched-window loading**

Add these definitions:

```python
@dataclass
class LoadedDataset:
    key: str
    label: str
    schedule: dict[str, list[dict[str, object]]]


@dataclass
class StudyInputs:
    datasets: tuple[LoadedDataset, ...]
    origin: pd.Timestamp
    horizon: int
    scoring_start: int
    scoring_end: int
    input_hashes: dict[str, str]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _attach_saved_opening_state(
    schedule: dict[str, list[dict[str, object]]],
    payload: dict[str, object],
    slug: str,
    origin: pd.Timestamp,
) -> None:
    columns = {
        name: index
        for index, name in enumerate(payload["fleet_columns"])
    }
    variants = {
        item["slug"]: item
        for item in payload["variants"]
    }
    if slug not in variants:
        raise ValueError(f"{slug}: opening-state record missing")
    variant = variants[slug]
    rows = {
        row[columns["Aircraft"]]: row
        for row in variant["fleet"]
    }
    for aircraft, events in schedule.items():
        row = rows[aircraft]
        opening = {
            check: (
                pd.Timestamp(row[columns[f"Opening_{check}_Due"]]) - origin
            ).days
            for check in "ABCD"
        }
        sequence_origin = int(row[columns["Opening_Sequence_Index"]])
        for event in events:
            event["_origin"] = sequence_origin
            event["_opening"] = opening


def load_study_inputs(root: Path = ROOT) -> StudyInputs:
    state_path = root / ".scratch/initial-maintenance-stagger/schedule-data.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"opening_state: missing input {state_path}")
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    forecast_start = pd.Timestamp(payload["forecast_start"])
    forecast_end = pd.Timestamp(payload["forecast_end"])
    if forecast_start != FORECAST_START or forecast_end != FORECAST_END:
        raise ValueError("Saved reporting dates do not match the approved study.")

    paths = {
        "original": root / "heavy_maintenance_forecast.xlsx",
        "moderate": root / (
            "outputs/initial-stagger/"
            "heavy_maintenance_forecast_stagger_moderate.xlsx"
        ),
        "wide": root / (
            "outputs/initial-stagger/"
            "heavy_maintenance_forecast_stagger_wide.xlsx"
        ),
    }
    labels = {
        "original": "Original",
        "moderate": "Moderate stagger",
        "wide": "Wide stagger",
    }
    loaded = {}
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"{key}: missing input {path}")
        try:
            loaded[key] = optimiser.load_selected_schedule(path)
        except Exception as exc:
            raise RuntimeError(f"{key}: could not load workbook: {exc}") from exc
    origin = min(
        [forecast_start] + [base_date for _, base_date in loaded.values()]
    )
    datasets = []
    for key in DATASET_KEYS:
        schedule, base_date = loaded[key]
        offset = int((base_date - origin).days)
        for events in schedule.values():
            for event in events:
                for field in ("start", "earliest_start", "latest_start"):
                    event[field] = int(event[field]) + offset
        if key != "original":
            _attach_saved_opening_state(schedule, payload, key, origin)
        datasets.append(LoadedDataset(key, labels[key], schedule))

    horizon = max(
        optimiser.get_forecast_horizon(dataset.schedule)
        for dataset in datasets
    )
    for dataset in datasets:
        if not optimiser.is_rule_compliant_schedule(dataset.schedule, horizon):
            raise ValueError(f"{dataset.key}: initial schedule is rule-invalid")

    hashes = {key: sha256_file(path) for key, path in paths.items()}
    hashes["opening_state"] = sha256_file(state_path)
    hashes["production"] = sha256_file(root / "vn_priority_based_selection.py")
    return StudyInputs(
        datasets=tuple(datasets),
        origin=origin,
        horizon=horizon,
        scoring_start=int((forecast_start - origin).days),
        scoring_end=int((forecast_end - origin).days),
        input_hashes=hashes,
    )
```

- [ ] **Step 4: Run matrix and input tests**

Run:

```bash
python3 -m unittest \
  tests.test_vn_hyperparameter_analysis.MatrixTests \
  tests.test_vn_hyperparameter_analysis.InputLoadingTests -v
```

Expected: `Ran 6 tests` and `OK`.

- [ ] **Step 5: Commit input loading**

```bash
git add analysis/vn_hyperparameter_analysis.py tests/test_vn_hyperparameter_analysis.py
git commit -m "feat: load matched VN study datasets"
```

## Task 3: Implement deterministic search and endpoint validation

**Files:**
- Modify: `analysis/vn_hyperparameter_analysis.py`
- Modify: `tests/test_vn_hyperparameter_analysis.py`

**Interfaces:**
- Produces: `visible_score()`, `priority_groups()`,
  `generate_study_neighbors()`, `independent_availability()`,
  `schedule_sha256()`, `validate_endpoint()`, and `run_trial()`
- Consumes: `LoadedDataset`, `Strategy`, production rebuild and score functions

- [ ] **Step 1: Add failing search and validation tests**

Add:

```python
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
        first = {"B": [{"check": "A", "start": 1, "duration": 14,
                        "earliest_start": 0, "latest_start": 2}],
                 "A": [{"check": "A", "start": 2, "duration": 14,
                        "earliest_start": 0, "latest_start": 3}]}
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
        scores = [tuple(item["score"]) for item in result["trace"]]
        self.assertTrue(
            all(left < right for left, right in zip(scores, scores[1:]))
        )
```

Add `import numpy as np`.

- [ ] **Step 2: Run the tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.TrialTests -v
```

Expected: FAIL because the search and validation functions are undefined.

- [ ] **Step 3: Implement visible-window proposals and independent validation**

Add:

```python
SCHEDULE_FIELDS = (
    "check", "start", "duration", "earliest_start", "latest_start",
)


def visible_score(
    availability: np.ndarray,
    scoring_start: int,
    scoring_end: int,
) -> tuple[float, float, float]:
    return optimiser.score_availability(
        availability[scoring_start:scoring_end + 1]
    )


def priority_groups(
    schedule: dict[str, list[dict[str, object]]],
    availability: np.ndarray,
    scoring_start: int,
    scoring_end: int,
) -> list[list[tuple[str, int]]]:
    rows = []
    for aircraft in sorted(schedule):
        for index, event in enumerate(schedule[aircraft]):
            left = max(int(event["start"]), scoring_start)
            right = min(
                int(event["start"]) + int(event["duration"]),
                scoring_end + 1,
            )
            level = (
                float(np.min(availability[left:right]))
                if left < right else float("inf")
            )
            rows.append((level, int(event["start"]), aircraft, index))
    rows.sort()
    grouped: dict[float, list[tuple[str, int]]] = {}
    for level, _, aircraft, index in rows:
        grouped.setdefault(level, []).append((aircraft, index))
    return list(grouped.values())


def generate_study_neighbors(
    schedule: dict[str, list[dict[str, object]]],
    availability: np.ndarray,
    horizon: int,
    scoring_start: int,
    scoring_end: int,
    current_score: tuple[float, float, float],
    shifts: tuple[int, ...],
) -> list[dict[str, object]]:
    for group in priority_groups(
        schedule, availability, scoring_start, scoring_end
    ):
        improving = []
        for aircraft, index in group:
            events = schedule[aircraft]
            event = events[index]
            if int(event["start"]) < scoring_start:
                continue
            for shift in shifts:
                rebuilt = optimiser.rebuild_aircraft_schedule(
                    events,
                    horizon=horizon,
                    event_index=index,
                    new_start=int(event["start"]) + shift,
                )
                if rebuilt is None or int(rebuilt[index]["start"]) < scoring_start:
                    continue
                candidate_availability = (
                    optimiser.availability_with_rebuilt_aircraft(
                        availability,
                        events,
                        rebuilt,
                    )
                )
                candidate_score = visible_score(
                    candidate_availability,
                    scoring_start,
                    scoring_end,
                )
                if candidate_score > current_score:
                    improving.append({
                        "aircraft": aircraft,
                        "event_index": index,
                        "events": rebuilt,
                        "availability": candidate_availability,
                        "score": candidate_score,
                        "shift": shift,
                    })
        if improving:
            return improving
    return []


def independent_availability(
    schedule: dict[str, list[dict[str, object]]],
    horizon: int,
) -> np.ndarray:
    occupied_count = np.zeros(horizon + 1, dtype=int)
    for events in schedule.values():
        occupied = np.zeros(horizon + 1, dtype=bool)
        for event in events:
            start = int(event["start"])
            end = start + int(event["duration"])
            occupied[start:end] = True
        occupied_count += occupied.astype(int)
    return len(schedule) - occupied_count


def schedule_sha256(
    schedule: dict[str, list[dict[str, object]]],
) -> str:
    canonical = {
        aircraft: [
            {field: event[field] for field in SCHEDULE_FIELDS}
            for event in sorted(events, key=lambda item: int(item["start"]))
        ]
        for aircraft, events in sorted(schedule.items())
    }
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

- [ ] **Step 4: Implement endpoint validation and one trial**

Add:

```python
def validate_endpoint(
    initial: dict[str, list[dict[str, object]]],
    final: dict[str, list[dict[str, object]]],
    incremental_availability: np.ndarray,
    horizon: int,
    scoring_start: int,
) -> None:
    if not optimiser.is_rule_compliant_schedule(final, horizon):
        raise ValueError("endpoint failed maintenance-rule replay")
    exact = optimiser.compute_availability(final, horizon)
    independent = independent_availability(final, horizon)
    if not np.array_equal(incremental_availability, exact):
        raise ValueError("incremental availability differs from full rebuild")
    if not np.array_equal(exact, independent):
        raise ValueError("full availability differs from occupancy mask")
    if set(initial) != set(final):
        raise ValueError("aircraft set changed")
    for aircraft in sorted(initial):
        before = initial[aircraft]
        after = final[aircraft]
        if len(before) != len(after):
            raise ValueError(f"{aircraft}: check count changed")
        for old, new in zip(before, after):
            if old["check"] != new["check"] or old["duration"] != new["duration"]:
                raise ValueError(f"{aircraft}: check identity changed")
            if int(old["start"]) < scoring_start and old != new:
                raise ValueError(f"{aircraft}: commenced check changed")


def run_trial(
    dataset: LoadedDataset,
    strategy: Strategy,
    max_iters: int,
    *,
    horizon: int,
    scoring_start: int,
    scoring_end: int,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, object]:
    initial = copy.deepcopy(dataset.schedule)
    current = copy.deepcopy(dataset.schedule)
    availability = optimiser.compute_availability(current, horizon)
    current_score = visible_score(
        availability, scoring_start, scoring_end
    )
    trace = [{"iteration": 0, "score": [float(v) for v in current_score]}]
    accepted_moves = 0
    outer_passes = 0
    exhausted = False
    started = clock()
    for iteration in range(max_iters):
        outer_passes += 1
        accepted = False
        for shifts in strategy.shift_sets:
            candidates = generate_study_neighbors(
                current,
                availability,
                horizon,
                scoring_start,
                scoring_end,
                current_score,
                shifts,
            )
            if not candidates:
                continue
            best = max(candidates, key=lambda item: item["score"])
            current[best["aircraft"]] = best["events"]
            availability = best["availability"]
            current_score = best["score"]
            accepted_moves += 1
            trace.append({
                "iteration": iteration + 1,
                "score": [float(v) for v in current_score],
                "shift": int(best["shift"]),
            })
            accepted = True
            break
        if not accepted:
            exhausted = True
            break
    elapsed = clock() - started
    validate_endpoint(
        initial,
        current,
        availability,
        horizon,
        scoring_start,
    )
    scores = [tuple(item["score"]) for item in trace]
    if not all(left < right for left, right in zip(scores, scores[1:])):
        raise ValueError("accepted score trace is not strictly improving")
    visible = availability[scoring_start:scoring_end + 1]
    return {
        "trial_key": f"{dataset.key}:{strategy.key}:{max_iters}",
        "dataset": dataset.key,
        "dataset_label": dataset.label,
        "strategy_key": strategy.key,
        "strategy_label": strategy.label,
        "shift_sets": [list(level) for level in strategy.shift_sets],
        "max_iters": max_iters,
        "min_availability": int(np.min(visible)),
        "availability_std": float(np.std(visible)),
        "mean_availability": float(np.mean(visible)),
        "lexicographic_score": [float(value) for value in current_score],
        "accepted_moves": accepted_moves,
        "outer_passes": outer_passes,
        "stop_reason": "local_exhaustion" if exhausted else "iteration_cap",
        "elapsed_seconds": float(elapsed),
        "rule_compliant": True,
        "endpoint_sha256": schedule_sha256(current),
        "trace": trace,
    }
```

- [ ] **Step 5: Run the focused trial tests**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.TrialTests -v
```

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 6: Run all analysis tests**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis -v
```

Expected: `Ran 9 tests` and `OK`.

- [ ] **Step 7: Commit the search**

```bash
git add analysis/vn_hyperparameter_analysis.py tests/test_vn_hyperparameter_analysis.py
git commit -m "feat: run and validate VN analysis trials"
```

## Task 4: Rank trials and write JSON/CSV

**Files:**
- Modify: `analysis/vn_hyperparameter_analysis.py`
- Modify: `tests/test_vn_hyperparameter_analysis.py`

**Interfaces:**
- Produces: `assign_dataset_ranks()`, `choose_recommendations()`,
  `run_study()`, `build_summary_rows()`, and `write_machine_outputs()`
- Consumes: exact 36-entry matrix and `run_trial()`

- [ ] **Step 1: Add deterministic fake-trial helpers and failing output tests**

Add:

```python
def fake_trial(dataset, strategy, max_iters, **_kwargs):
    strategy_index = next(
        index for index, item in enumerate(study.STRATEGIES)
        if item.key == strategy.key
    )
    score = [
        20.0 - strategy_index,
        -(1.0 + max_iters / 10000),
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
        "stop_reason": "local_exhaustion",
        "elapsed_seconds": float(max_iters),
        "rule_compliant": True,
        "endpoint_sha256": strategy.key,
        "trace": [{"iteration": 0, "score": score}],
    }


class StudyOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = study.load_study_inputs(ROOT)

    def test_run_study_calls_each_of_36_trials_once(self):
        calls = []

        def recording_runner(*args, **kwargs):
            calls.append((args[0].key, args[1].key, args[2]))
            return fake_trial(*args, **kwargs)

        payload = study.run_study(self.inputs, recording_runner)
        self.assertEqual(len(calls), 36)
        self.assertEqual(len(set(calls)), 36)
        self.assertEqual(len(payload["trials"]), 36)

    def test_exact_score_ties_share_competition_rank(self):
        trials = [
            {"dataset": "original", "lexicographic_score": [18, -1.2, 21]},
            {"dataset": "original", "lexicographic_score": [18, -1.2, 21]},
            {"dataset": "original", "lexicographic_score": [17, -1.0, 22]},
        ]
        study.assign_dataset_ranks(trials)
        self.assertEqual([item["dataset_rank"] for item in trials], [1, 1, 3])

    def test_json_and_csv_cover_the_same_36_trials(self):
        payload = study.run_study(self.inputs, fake_trial)
        with tempfile.TemporaryDirectory() as directory:
            paths = study.write_machine_outputs(payload, Path(directory))
            saved = json.loads(paths["json"].read_text(encoding="utf-8"))
            with paths["csv"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(saved["trials"]), 36)
        self.assertEqual(len(rows), 36)
        self.assertEqual(
            {row["trial_key"] for row in rows},
            {trial["trial_key"] for trial in saved["trials"]},
        )
```

Add `csv` and `json` to the test imports.

- [ ] **Step 2: Run the output tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.StudyOutputTests -v
```

Expected: FAIL because study orchestration, ranking, and writers are undefined.

- [ ] **Step 3: Implement ranking and recommendation selection**

Add:

```python
def assign_dataset_ranks(trials: list[dict[str, object]]) -> None:
    for dataset in DATASET_KEYS:
        group = [item for item in trials if item["dataset"] == dataset]
        scores = [tuple(item["lexicographic_score"]) for item in group]
        for item in group:
            score = tuple(item["lexicographic_score"])
            item["dataset_rank"] = 1 + sum(other > score for other in scores)


def choose_recommendations(
    trials: list[dict[str, object]],
) -> dict[str, object]:
    winners = {
        dataset: min(
            (item for item in trials if item["dataset"] == dataset),
            key=lambda item: (
                item["dataset_rank"],
                item["max_iters"],
                item["elapsed_seconds"],
                next(
                    index for index, strategy in enumerate(STRATEGIES)
                    if strategy.key == item["strategy_key"]
                ),
            ),
        )["trial_key"]
        for dataset in DATASET_KEYS
    }
    strategy_order = {
        strategy.key: index for index, strategy in enumerate(STRATEGIES)
    }
    candidates = []
    for strategy in STRATEGIES:
        for budget in BUDGETS:
            rows = [
                item for item in trials
                if item["strategy_key"] == strategy.key
                and item["max_iters"] == budget
            ]
            candidates.append((
                sum(item["dataset_rank"] for item in rows),
                max(item["dataset_rank"] for item in rows),
                budget,
                sum(item["elapsed_seconds"] for item in rows),
                strategy_order[strategy.key],
                strategy.key,
            ))
    _, _, budget, _, _, strategy_key = min(candidates)
    return {
        "dataset_winners": winners,
        "shared": {
            "strategy_key": strategy_key,
            "max_iters": budget,
        },
    }
```

- [ ] **Step 4: Implement one-pass orchestration and machine outputs**

Add:

```python
CSV_FIELDS = (
    "trial_key", "dataset", "strategy_key", "strategy_label", "max_iters",
    "shift_sets", "min_availability", "availability_std",
    "mean_availability", "accepted_moves", "outer_passes", "stop_reason",
    "elapsed_seconds", "lexicographic_score", "dataset_rank",
    "rule_compliant", "endpoint_sha256",
)


def run_study(
    inputs: StudyInputs,
    trial_runner: Callable[..., dict[str, object]] = run_trial,
) -> dict[str, object]:
    datasets = {item.key: item for item in inputs.datasets}
    trials = []
    for dataset_key, strategy, budget in build_trial_matrix():
        try:
            result = trial_runner(
                datasets[dataset_key],
                strategy,
                budget,
                horizon=inputs.horizon,
                scoring_start=inputs.scoring_start,
                scoring_end=inputs.scoring_end,
            )
        except Exception as exc:
            trial_key = f"{dataset_key}:{strategy.key}:{budget}"
            raise RuntimeError(f"{trial_key}: trial failed: {exc}") from exc
        trials.append(result)
    if len(trials) != 36 or len({item["trial_key"] for item in trials}) != 36:
        raise ValueError("Study did not produce 36 unique trial records.")
    assign_dataset_ranks(trials)
    return {
        "study": "VN priority hyperparameter analysis",
        "forecast_start": str(
            (inputs.origin + pd.Timedelta(days=inputs.scoring_start)).date()
        ),
        "forecast_end": str(
            (inputs.origin + pd.Timedelta(days=inputs.scoring_end)).date()
        ),
        "selection_policy": "first_priority_level_best_candidate",
        "input_hashes": inputs.input_hashes,
        "strategies": [
            {
                "key": item.key,
                "label": item.label,
                "shift_sets": [list(level) for level in item.shift_sets],
            }
            for item in STRATEGIES
        ],
        "budgets": list(BUDGETS),
        "trials": trials,
        "recommendations": choose_recommendations(trials),
    }


def build_summary_rows(
    trials: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for trial in trials:
        row = {field: trial[field] for field in CSV_FIELDS}
        row["shift_sets"] = json.dumps(row["shift_sets"], separators=(",", ":"))
        row["lexicographic_score"] = json.dumps(
            row["lexicographic_score"], separators=(",", ":")
        )
        rows.append(row)
    return rows


def write_machine_outputs(
    payload: dict[str, object],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    csv_path = output_dir / "summary.csv"
    json_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(build_summary_rows(payload["trials"]))
    return {"json": json_path, "csv": csv_path}
```

- [ ] **Step 5: Run the analysis suite**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis -v
```

Expected: `Ran 12 tests` and `OK`.

- [ ] **Step 6: Commit machine-readable outputs**

```bash
git add analysis/vn_hyperparameter_analysis.py tests/test_vn_hyperparameter_analysis.py
git commit -m "feat: rank and serialize VN study results"
```

## Task 5: Generate headless charts and the Word report

**Files:**
- Modify: `analysis/vn_hyperparameter_analysis.py`
- Modify: `tests/test_vn_hyperparameter_analysis.py`

**Interfaces:**
- Produces: `create_charts()` and `build_report()`
- Consumes: the ranked trial payload from `run_study()`

- [ ] **Step 1: Add failing chart and report tests**

Add:

```python
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

    def test_report_has_required_sections_charts_and_page_breaks(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            charts = study.create_charts(self.payload["trials"], folder)
            report = folder / "report.docx"
            study.build_report(self.payload, charts, report)
            document = Document(report)
            headings = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.style.name.startswith("Heading")
            ]
            self.assertEqual(
                headings,
                [
                    "Purpose and recommendation",
                    "Method and datasets",
                    "Parameter choices",
                    "Original dataset",
                    "Moderate stagger",
                    "Wide stagger",
                    "Cross-dataset comparison",
                    "Runtime and convergence",
                    "Limitations",
                    "Practical recommendation and reproduction",
                ],
            )
            self.assertEqual(len(document.inline_shapes), 3)
            xml = document._element.xml
            self.assertEqual(xml.count('w:type="page"'), 9)
            text = "\n".join(p.text.lower() for p in document.paragraphs)
            self.assertIn("one observed run", text)
            self.assertNotIn("statistically significant", text)
            self.assertNotIn("confidence interval", text)
```

Add `from docx import Document` to the test imports.

- [ ] **Step 2: Run the presentation tests to verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_vn_hyperparameter_analysis.PresentationOutputTests -v
```

Expected: FAIL because `create_charts` and `build_report` are undefined.

- [ ] **Step 3: Implement the three chart contracts**

Implement `create_charts()` with these exact filenames and rules:

```python
def create_charts(
    trials: list[dict[str, object]],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "ranked_quality": output_dir / "ranked-quality.png",
        "budget_convergence": output_dir / "budget-convergence.png",
        "runtime": output_dir / "runtime.png",
    }

    figure, axes = plt.subplots(1, 3, figsize=(13, 5), constrained_layout=True)
    for axis, dataset in zip(axes, DATASET_KEYS):
        rows = sorted(
            (item for item in trials if item["dataset"] == dataset),
            key=lambda item: (item["dataset_rank"], item["availability_std"]),
        )
        labels = [
            f'{item["strategy_key"]} / {item["max_iters"]} '
            f'(min {item["min_availability"]})'
            for item in rows
        ]
        positions = np.arange(len(rows))
        axis.scatter(
            [item["availability_std"] for item in rows],
            positions,
            color="black",
        )
        axis.set_yticks(positions, labels, fontsize=7)
        axis.invert_yaxis()
        axis.set_title(rows[0]["dataset_label"])
        axis.set_xlabel("Availability standard deviation (lower is better)")
        axis.grid(axis="x", alpha=0.25)
    figure.savefig(paths["ranked_quality"], dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    for axis, dataset in zip(axes, DATASET_KEYS):
        for strategy in STRATEGIES:
            rows = sorted(
                (
                    item for item in trials
                    if item["dataset"] == dataset
                    and item["strategy_key"] == strategy.key
                ),
                key=lambda item: item["max_iters"],
            )
            axis.plot(
                [item["max_iters"] for item in rows],
                [item["accepted_moves"] for item in rows],
                marker="o",
                label=strategy.label,
            )
            for item in rows:
                if item["stop_reason"] == "local_exhaustion":
                    axis.annotate(
                        "local",
                        (item["max_iters"], item["accepted_moves"]),
                        fontsize=7,
                    )
        axis.set_title(next(
            item["dataset_label"] for item in trials
            if item["dataset"] == dataset
        ))
        axis.set_xlabel("max_iters")
        axis.set_ylabel("Accepted moves")
        axis.grid(alpha=0.25)
    axes[-1].legend(fontsize=7, loc="best")
    figure.savefig(paths["budget_convergence"], dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(1, 3, figsize=(13, 5), constrained_layout=True)
    for axis, dataset in zip(axes, DATASET_KEYS):
        rows = [
            item for item in trials if item["dataset"] == dataset
        ]
        labels = [
            f'{item["strategy_key"]} / {item["max_iters"]}'
            for item in rows
        ]
        positions = np.arange(len(rows))
        axis.barh(
            positions,
            [item["elapsed_seconds"] for item in rows],
            color="#666666",
        )
        axis.set_yticks(positions, labels, fontsize=7)
        axis.invert_yaxis()
        axis.set_title(rows[0]["dataset_label"])
        axis.set_xlabel("One observed search run (seconds)")
        axis.grid(axis="x", alpha=0.25)
    figure.savefig(paths["runtime"], dpi=180)
    plt.close(figure)
    return paths
```

- [ ] **Step 4: Implement the ten-section DOCX**

Implement `build_report()` so the first section shares the title page and each
later section starts after one explicit page break:

```python
REPORT_SECTIONS = (
    "Purpose and recommendation",
    "Method and datasets",
    "Parameter choices",
    "Original dataset",
    "Moderate stagger",
    "Wide stagger",
    "Cross-dataset comparison",
    "Runtime and convergence",
    "Limitations",
    "Practical recommendation and reproduction",
)


def _best_for_dataset(
    payload: dict[str, object],
    dataset: str,
) -> dict[str, object]:
    return min(
        (item for item in payload["trials"] if item["dataset"] == dataset),
        key=lambda item: (
            item["dataset_rank"],
            item["max_iters"],
            item["elapsed_seconds"],
        ),
    )


def _add_table(
    document: Document,
    headers: tuple[str, ...],
    rows: list[tuple[object, ...]],
) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = str(value)


def build_report(
    payload: dict[str, object],
    charts: dict[str, Path],
    output_path: Path,
) -> None:
    document = Document()
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(11)
    document.add_heading("VN priority hyperparameter analysis", 0)
    shared = payload["recommendations"]["shared"]

    section_text = {
        "Purpose and recommendation": (
            "This report compares a deliberately small set of settings for the "
            "deterministic priority-based optimiser. The shared recommendation "
            f'is {shared["strategy_key"]} with max_iters={shared["max_iters"]}. '
            "Each configuration has one observed run; no repeated-run or "
            "statistical claim is made."
        ),
        "Method and datasets": (
            "The same four strategies and three budgets are applied once to "
            "the original, moderate-stagger, and wide-stagger forecasts. "
            "Scores use the common forecast dates and the production "
            "lexicographic objective."
        ),
        "Parameter choices": (
            "The earlier tuned baseline is kept separate from the current live "
            "seven-level ladder. Selection remains the first priority level "
            "with improving candidates, followed by its best candidate."
        ),
        "Cross-dataset comparison": (
            "Ranks are calculated within each dataset. Differences between "
            "datasets describe different starting maintenance states and are "
            "not optimiser gains."
        ),
        "Runtime and convergence": (
            "Runtime is one observed search duration and excludes loading, "
            "validation, charting, and report construction. Local exhaustion "
            "means a complete outer pass found no improving move."
        ),
        "Limitations": (
            "The experiment covers three related forecasts and four grounded "
            "shift strategies. It does not establish global optimality and "
            "does not enforce the saved loose, medium, or tight operational "
            "scenarios during search."
        ),
        "Practical recommendation and reproduction": (
            "Use the shared recommendation when one setting is required across "
            "all three forecasts; use the rank-one dataset result when settings "
            "may differ. Reproduce with: "
            "python3 analysis/vn_hyperparameter_analysis.py"
        ),
    }
    dataset_sections = {
        "Original dataset": "original",
        "Moderate stagger": "moderate",
        "Wide stagger": "wide",
    }

    for index, heading in enumerate(REPORT_SECTIONS):
        if index:
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        document.add_heading(heading, level=1)
        if heading in dataset_sections:
            dataset = dataset_sections[heading]
            best = _best_for_dataset(payload, dataset)
            document.add_paragraph(
                f'The strongest measured configuration is '
                f'{best["strategy_label"]} at max_iters={best["max_iters"]}. '
                f'It reaches minimum availability {best["min_availability"]}, '
                f'standard deviation {best["availability_std"]:.6f}, and mean '
                f'availability {best["mean_availability"]:.6f}. It accepted '
                f'{best["accepted_moves"]} moves and ended by '
                f'{best["stop_reason"].replace("_", " ")}.'
            )
            ranked = sorted(
                (
                    item for item in payload["trials"]
                    if item["dataset"] == dataset
                ),
                key=lambda item: (
                    item["dataset_rank"],
                    item["max_iters"],
                ),
            )
            _add_table(
                document,
                ("Rank", "Strategy", "Budget", "Minimum", "Std", "Moves"),
                [
                    (
                        item["dataset_rank"],
                        item["strategy_label"],
                        item["max_iters"],
                        item["min_availability"],
                        f'{item["availability_std"]:.4f}',
                        item["accepted_moves"],
                    )
                    for item in ranked
                ],
            )
        else:
            document.add_paragraph(section_text[heading])
            if heading == "Parameter choices":
                _add_table(
                    document,
                    ("Strategy", "Ordered shift sets"),
                    [
                        (
                            strategy.label,
                            " | ".join(
                                ",".join(str(value) for value in level)
                                for level in strategy.shift_sets
                            ),
                        )
                        for strategy in STRATEGIES
                    ],
                )

        if heading == "Cross-dataset comparison":
            document.add_picture(
                str(charts["ranked_quality"]), width=Inches(6.4)
            )
        elif heading == "Runtime and convergence":
            document.add_picture(
                str(charts["budget_convergence"]), width=Inches(6.4)
            )
            document.add_picture(
                str(charts["runtime"]), width=Inches(6.4)
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
```

- [ ] **Step 5: Run presentation tests**

Run:

```bash
python3 -m unittest \
  tests.test_vn_hyperparameter_analysis.PresentationOutputTests -v
```

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 6: Run the complete analysis suite**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis -v
```

Expected: `Ran 15 tests` and `OK`.

- [ ] **Step 7: Commit charts and report generation**

```bash
git add analysis/vn_hyperparameter_analysis.py tests/test_vn_hyperparameter_analysis.py
git commit -m "feat: generate VN analysis charts and report"
```

## Task 6: Add failure-safe publication and the CLI

**Files:**
- Modify: `analysis/vn_hyperparameter_analysis.py`
- Modify: `tests/test_vn_hyperparameter_analysis.py`

**Interfaces:**
- Produces: `validate_generated_outputs()`, `publish_outputs()`, and `main()`
- Consumes: machine writers, chart writer, report writer, and full study payload

- [ ] **Step 1: Add failing publication tests**

Add:

```python
from unittest.mock import patch


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

    def test_publish_does_not_leave_partial_outputs_on_report_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "published"
            with patch.object(
                study,
                "build_report",
                side_effect=RuntimeError("report failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "report failed"):
                    study.publish_outputs(self.payload, output)
            self.assertFalse(output.exists())

    def test_publish_writes_exactly_six_valid_artifacts(self):
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
                    "vn-hyperparameter-analysis.docx",
                },
            )
            study.validate_generated_outputs(self.payload, output)
```

- [ ] **Step 2: Run publication tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis.PublicationTests -v
```

Expected: FAIL because publication and artifact validation are undefined.

- [ ] **Step 3: Implement artifact validation and temporary-directory publication**

Add:

```python
ARTIFACT_NAMES = (
    "results.json",
    "summary.csv",
    "ranked-quality.png",
    "budget-convergence.png",
    "runtime.png",
    "vn-hyperparameter-analysis.docx",
)


def validate_generated_outputs(
    payload: dict[str, object],
    output_dir: Path,
) -> None:
    missing = [
        name for name in ARTIFACT_NAMES
        if not (output_dir / name).is_file()
        or (output_dir / name).stat().st_size == 0
    ]
    if missing:
        raise ValueError(f"Missing or empty artifacts: {', '.join(missing)}")
    saved = json.loads(
        (output_dir / "results.json").read_text(encoding="utf-8")
    )
    with (output_dir / "summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    if len(saved["trials"]) != 36 or len(rows) != 36:
        raise ValueError("JSON and CSV must each contain 36 trials.")
    expected = {item["trial_key"] for item in payload["trials"]}
    if {row["trial_key"] for row in rows} != expected:
        raise ValueError("CSV trial keys differ from JSON trial keys.")
    if not all(item["rule_compliant"] for item in saved["trials"]):
        raise ValueError("A saved trial is not rule-compliant.")


def publish_outputs(
    payload: dict[str, object],
    output_dir: Path = OUTPUT_DIR,
) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-",
        dir=output_dir.parent,
    ) as temporary:
        staging = Path(temporary)
        write_machine_outputs(payload, staging)
        charts = create_charts(payload["trials"], staging)
        build_report(
            payload,
            charts,
            staging / "vn-hyperparameter-analysis.docx",
        )
        validate_generated_outputs(payload, staging)
        output_dir.mkdir(parents=True, exist_ok=True)
        for name in ARTIFACT_NAMES:
            os.replace(staging / name, output_dir / name)


def main() -> int:
    inputs = load_study_inputs(ROOT)
    payload = run_study(inputs)
    publish_outputs(payload, OUTPUT_DIR)
    print(f"Wrote 36 validated trials and report to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run publication and full analysis tests**

Run:

```bash
python3 -m unittest tests.test_vn_hyperparameter_analysis -v
```

Expected: `Ran 18 tests` and `OK`.

- [ ] **Step 5: Run syntax checks**

Run:

```bash
python3 -m py_compile \
  analysis/vn_hyperparameter_analysis.py \
  tests/test_vn_hyperparameter_analysis.py
```

Expected: exit code 0 with no output.

- [ ] **Step 6: Commit the CLI**

```bash
git add analysis/vn_hyperparameter_analysis.py tests/test_vn_hyperparameter_analysis.py
git commit -m "feat: publish VN analysis artifacts safely"
```

## Task 7: Run the study once and verify all deliverables

**Files:**
- Create: `docs/reports/vn-hyperparameter-analysis/results.json`
- Create: `docs/reports/vn-hyperparameter-analysis/summary.csv`
- Create: `docs/reports/vn-hyperparameter-analysis/ranked-quality.png`
- Create: `docs/reports/vn-hyperparameter-analysis/budget-convergence.png`
- Create: `docs/reports/vn-hyperparameter-analysis/runtime.png`
- Create: `docs/reports/vn-hyperparameter-analysis/vn-hyperparameter-analysis.docx`

**Interfaces:**
- Consumes: `main()` and all prior functions
- Produces: the final committed study artifacts and verification evidence

- [ ] **Step 1: Record the production optimiser hash**

Run:

```bash
sha256sum vn_priority_based_selection.py > /tmp/vn-priority-before.sha256
```

Expected: exit code 0.

- [ ] **Step 2: Run the complete automated test suite before the long study**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all repository tests pass with final output `OK`.

- [ ] **Step 3: Execute the 36-trial study once**

Run this long command in a persistent terminal session:

```bash
python3 analysis/vn_hyperparameter_analysis.py
```

Expected final line:

```text
Wrote 36 validated trials and report to <repository>/docs/reports/vn-hyperparameter-analysis
```

Do not rerun completed configurations to create timing repetitions. If the
process fails, fix the defect test-first, remove the incomplete output
directory, and restart the single complete study.

- [ ] **Step 4: Verify matrix, metrics, compliance, and output files**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import csv
import json

folder = Path("docs/reports/vn-hyperparameter-analysis")
payload = json.loads((folder / "results.json").read_text(encoding="utf-8"))
with (folder / "summary.csv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
assert len(payload["trials"]) == 36
assert len(rows) == 36
assert len({item["trial_key"] for item in payload["trials"]}) == 36
assert all(item["rule_compliant"] for item in payload["trials"])
assert {item["max_iters"] for item in payload["trials"]} == {200, 400, 800}
assert {item["dataset"] for item in payload["trials"]} == {
    "original", "moderate", "wide",
}
assert len({item["strategy_key"] for item in payload["trials"]}) == 4
assert payload["selection_policy"] == "first_priority_level_best_candidate"
expected = {
    "results.json", "summary.csv", "ranked-quality.png",
    "budget-convergence.png", "runtime.png",
    "vn-hyperparameter-analysis.docx",
}
assert {path.name for path in folder.iterdir()} == expected
assert all((folder / name).stat().st_size > 0 for name in expected)
print("36 validated trials and six artifacts verified")
PY
```

Expected: `36 validated trials and six artifacts verified`.

- [ ] **Step 5: Render and verify report length**

If both LibreOffice and `pdfinfo` are available, run:

```bash
rm -rf /tmp/vn-report-check
mkdir -p /tmp/vn-report-check
libreoffice --headless --convert-to pdf \
  --outdir /tmp/vn-report-check \
  docs/reports/vn-hyperparameter-analysis/vn-hyperparameter-analysis.docx
pages="$(pdfinfo /tmp/vn-report-check/vn-hyperparameter-analysis.pdf | awk '/^Pages:/ {print $2}')"
test "$pages" -ge 9
test "$pages" -le 11
printf 'report pages: %s\n' "$pages"
```

Expected: `report pages: N`, where `N` is 9, 10, or 11.

Open the rendered PDF and inspect every page for clipped tables, blank pages,
unreadable chart labels, awkward page breaks, repeated boilerplate, and
unsupported statistical language. If LibreOffice or `pdfinfo` is unavailable,
open the DOCX in Word, record the displayed page count, and perform the same
page-by-page inspection before continuing.

- [ ] **Step 6: Verify the production optimiser and repository scope**

Run:

```bash
sha256sum --check /tmp/vn-priority-before.sha256
git diff --exit-code origin/main -- vn_priority_based_selection.py
git status --short
```

Expected:

- hash output ends with `OK`;
- `git diff` exits 0 with no output; and
- status lists only the six generated artifacts under
  `docs/reports/vn-hyperparameter-analysis/`; the script and test
  file were committed in Tasks 1–6.

- [ ] **Step 7: Run final tests after artifact generation**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile \
  analysis/vn_hyperparameter_analysis.py \
  tests/test_vn_hyperparameter_analysis.py
```

Expected: all tests pass with final output `OK`; compilation exits 0.

- [ ] **Step 8: Commit the generated study**

```bash
git add \
  docs/reports/vn-hyperparameter-analysis
git commit -m "docs: add VN hyperparameter analysis report"
```

- [ ] **Step 9: Inspect the final committed scope**

Run:

```bash
git show --stat --oneline HEAD
git status --short
```

Expected: the commit contains the six report artifacts; the working tree is
clean. The preceding commits contain the script and test file.
