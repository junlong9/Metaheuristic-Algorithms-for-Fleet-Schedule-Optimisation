from __future__ import annotations

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import openpyxl
    import pandas as pd
except ImportError as exc:
    raise SystemExit(
        f"Missing analysis dependency: {exc.name}. Install with: "
        "python -m pip install numpy pandas openpyxl matplotlib"
    ) from exc

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
import argparse
import copy
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import vn_priority_based_selection as optimiser

OUTPUT_DIR = ROOT / "docs/reports/2026-10-22-vn-step-size-study"
STATE_PATH = ROOT / ".scratch/initial-maintenance-stagger/schedule-data.json"
FORECAST_START = pd.Timestamp("2026-01-21")
FORECAST_END = pd.Timestamp("2038-01-18")
DATASET_KEYS = ("original", "moderate", "wide")
BUDGETS = (200, 400, 800)
# Run only for dataset/strategy pairs whose largest-budget trial hit its cap.
EXTENSION_BUDGET = 1600


@dataclass(frozen=True)
class Strategy:
    key: str
    label: str
    shift_sets: tuple[tuple[int, ...], ...]


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


def _pairs(*steps: int) -> tuple[tuple[int, int], ...]:
    return tuple((-step, step) for step in steps)


STRATEGIES = (
    Strategy(
        "historical_half_step",
        "Overlapping half-step sets",
        (
            (-28, -14, 14, 28),
            (-14, -7, 7, 14),
            (-7, -3, 3, 7),
            (-3, -1, 1, 3),
        ),
    ),
    Strategy(
        "live_wide_to_fine",
        "Wide-to-fine ladder (±56 to ±1)",
        (
            (-56, 56),
            (-42, 42),
            (-28, 28),
            (-14, 14),
            (-7, 7),
            (-3, 3),
            (-1, 1),
        ),
    ),
    Strategy(
        "dense_pairs",
        "Dense paired ladder",
        (
            (-28, 28),
            (-21, 21),
            (-14, 14),
            (-7, 7),
            (-3, 3),
            (-1, 1),
        ),
    ),
    Strategy(
        "half_step_plus_42",
        "Overlapping half-step sets plus ±42",
        (
            (-42, 42),
            (-28, -14, 14, 28),
            (-14, -7, 7, 14),
            (-7, -3, 3, 7),
            (-3, -1, 1, 3),
        ),
    ),
    Strategy(
        "pairs_28",
        "Baseline (±28, ±14, ±7, ±3, ±1)",
        _pairs(28, 14, 7, 3, 1),
    ),
    Strategy("pairs_14", "Pairs from ±14 (±14 to ±1)", _pairs(14, 7, 3, 1)),
    Strategy("pairs_7", "Pairs from ±7 (±7 to ±1)", _pairs(7, 3, 1)),
    Strategy("pairs_3", "Pairs from ±3 (±3, ±1)", _pairs(3, 1)),
    Strategy("pairs_1", "±1 only", _pairs(1)),
    Strategy(
        "pairs_42",
        "Pairs from ±42 (±42 to ±1)",
        _pairs(42, 28, 14, 7, 3, 1),
    ),
    Strategy(
        "pairs_28_fine_first",
        "Baseline steps, fine first (±1 to ±28)",
        _pairs(1, 3, 7, 14, 28),
    ),
    Strategy(
        "single_set_28",
        "Baseline steps in one set",
        ((-28, -14, -7, -3, -1, 1, 3, 7, 14, 28),),
    ),
    Strategy(
        "overlap_14",
        "Overlapping sets without ±28",
        (
            (-14, -7, 7, 14),
            (-7, -3, 3, 7),
            (-3, -1, 1, 3),
        ),
    ),
)

EXPECTED_MATRIX_SIZE = len(DATASET_KEYS) * len(STRATEGIES) * len(BUDGETS)


def build_trial_matrix() -> list[tuple[str, Strategy, int]]:
    matrix = [
        (dataset, strategy, budget)
        for dataset in DATASET_KEYS
        for strategy in STRATEGIES
        for budget in BUDGETS
    ]
    keys = [(dataset, strategy.key, budget) for dataset, strategy, budget in matrix]
    if (
        len(matrix) != EXPECTED_MATRIX_SIZE
        or len(set(keys)) != EXPECTED_MATRIX_SIZE
        or len({strategy.key for strategy in STRATEGIES}) != len(STRATEGIES)
    ):
        raise ValueError(
            f"Experiment matrix must contain {EXPECTED_MATRIX_SIZE} unique trials."
        )
    return matrix


def build_extension_matrix(
    trials: list[dict[str, object]],
) -> list[tuple[str, Strategy, int]]:
    capped = {
        (item["dataset"], item["strategy_key"])
        for item in trials
        if item["max_iters"] == max(BUDGETS)
        and item["stop_reason"] == "iteration_cap"
    }
    return [
        (dataset, strategy, EXTENSION_BUDGET)
        for dataset in DATASET_KEYS
        for strategy in STRATEGIES
        if (dataset, strategy.key) in capped
    ]


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
            "outputs/initial-stagger-20261013/"
            "heavy_maintenance_forecast_stagger_moderate.xlsx"
        ),
        "wide": root / (
            "outputs/initial-stagger-20261013/"
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


SCHEDULE_FIELDS = (
    "check",
    "start",
    "duration",
    "earliest_start",
    "latest_start",
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
                if left < right
                else float("inf")
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
        schedule,
        availability,
        scoring_start,
        scoring_end,
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
        availability,
        scoring_start,
        scoring_end,
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
        "natural_exhaustion": exhausted,
        "stop_reason": "local_exhaustion" if exhausted else "iteration_cap",
        "elapsed_seconds": float(elapsed),
        "rule_compliant": True,
        "endpoint_sha256": schedule_sha256(current),
        "trace": trace,
    }


def assign_dataset_ranks(trials: list[dict[str, object]]) -> None:
    for dataset in DATASET_KEYS:
        group = [item for item in trials if item["dataset"] == dataset]
        scores = [tuple(item["lexicographic_score"]) for item in group]
        for item in group:
            score = tuple(item["lexicographic_score"])
            item["dataset_rank"] = 1 + sum(other > score for other in scores)


def strategy_complexity(strategy: Strategy) -> int:
    return sum(len(level) for level in strategy.shift_sets)


def choose_recommendations(
    trials: list[dict[str, object]],
) -> dict[str, object]:
    strategies = {strategy.key: strategy for strategy in STRATEGIES}
    strategy_order = {
        strategy.key: index for index, strategy in enumerate(STRATEGIES)
    }
    winners = {
        dataset: min(
            (item for item in trials if item["dataset"] == dataset),
            key=lambda item: (
                item["dataset_rank"],
                item["max_iters"],
                strategy_complexity(strategies[item["strategy_key"]]),
                item["elapsed_seconds"],
                strategy_order[item["strategy_key"]],
            ),
        )["trial_key"]
        for dataset in DATASET_KEYS
    }
    budgets = sorted({int(item["max_iters"]) for item in trials})
    candidates = []
    for strategy in STRATEGIES:
        for budget in budgets:
            rows = [
                item
                for item in trials
                if item["strategy_key"] == strategy.key
                and item["max_iters"] == budget
            ]
            if {item["dataset"] for item in rows} != set(DATASET_KEYS):
                continue
            candidates.append((
                sum(item["dataset_rank"] for item in rows),
                max(item["dataset_rank"] for item in rows),
                budget,
                strategy_complexity(strategy),
                sum(item["elapsed_seconds"] for item in rows),
                strategy_order[strategy.key],
                strategy.key,
            ))
    _, _, budget, _, _, _, strategy_key = min(candidates)
    return {
        "dataset_winners": winners,
        "shared": {
            "strategy_key": strategy_key,
            "max_iters": budget,
        },
    }


CSV_FIELDS = (
    "trial_key",
    "dataset",
    "strategy_key",
    "strategy_label",
    "max_iters",
    "shift_sets",
    "min_availability",
    "availability_std",
    "mean_availability",
    "accepted_moves",
    "outer_passes",
    "natural_exhaustion",
    "stop_reason",
    "elapsed_seconds",
    "lexicographic_score",
    "dataset_rank",
    "rule_compliant",
    "endpoint_sha256",
)


def _run_trials(
    matrix: list[tuple[str, Strategy, int]],
    inputs: StudyInputs,
    trial_runner: Callable[..., dict[str, object]],
    workers: int,
) -> list[dict[str, object]]:
    datasets = {item.key: item for item in inputs.datasets}
    kwargs = {
        "horizon": inputs.horizon,
        "scoring_start": inputs.scoring_start,
        "scoring_end": inputs.scoring_end,
    }

    def fail(dataset_key: str, strategy: Strategy, budget: int, exc: Exception):
        trial_key = f"{dataset_key}:{strategy.key}:{budget}"
        raise RuntimeError(f"{trial_key}: trial failed: {exc}") from exc

    results = []
    if workers <= 1:
        for dataset_key, strategy, budget in matrix:
            try:
                results.append(trial_runner(
                    datasets[dataset_key], strategy, budget, **kwargs
                ))
            except Exception as exc:
                fail(dataset_key, strategy, budget, exc)
        return results
    # Each trial is deterministic and shares no state, so results are
    # collected in matrix order regardless of completion order.
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                trial_runner, datasets[dataset_key], strategy, budget, **kwargs
            )
            for dataset_key, strategy, budget in matrix
        ]
        for (dataset_key, strategy, budget), future in zip(matrix, futures):
            try:
                results.append(future.result())
            except Exception as exc:
                fail(dataset_key, strategy, budget, exc)
    return results


def run_study(
    inputs: StudyInputs,
    trial_runner: Callable[..., dict[str, object]] = run_trial,
    *,
    workers: int = 1,
) -> dict[str, object]:
    matrix = build_trial_matrix()
    trials = _run_trials(matrix, inputs, trial_runner, workers)
    extension = build_extension_matrix(trials)
    trials += _run_trials(extension, inputs, trial_runner, workers)
    expected = len(matrix) + len(extension)
    if (
        len(trials) != expected
        or len({item["trial_key"] for item in trials}) != expected
    ):
        raise ValueError(
            f"Study did not produce {expected} unique trial records."
        )
    assign_dataset_ranks(trials)
    return {
        "study": "VN priority step-size study",
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
        "extension_budget": EXTENSION_BUDGET,
        "extension_trials": [
            f"{dataset}:{strategy.key}:{budget}"
            for dataset, strategy, budget in extension
        ],
        "workers": workers,
        "trials": trials,
        "recommendations": choose_recommendations(trials),
    }


def build_summary_rows(
    trials: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for trial in trials:
        row = {field: trial[field] for field in CSV_FIELDS}
        row["shift_sets"] = json.dumps(
            row["shift_sets"],
            separators=(",", ":"),
        )
        row["lexicographic_score"] = json.dumps(
            row["lexicographic_score"],
            separators=(",", ":"),
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
    rows_per_dataset = max(
        sum(item["dataset"] == dataset for item in trials)
        for dataset in DATASET_KEYS
    )
    tall = max(5.0, 0.16 * rows_per_dataset + 1.5)

    figure, axes = plt.subplots(
        1, 3, figsize=(15, tall), constrained_layout=True
    )
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

    colours = plt.get_cmap("tab20")
    budgets = sorted({int(item["max_iters"]) for item in trials})
    figure, axes = plt.subplots(
        1, 3, figsize=(15, 5.5), constrained_layout=True
    )
    for axis, dataset in zip(axes, DATASET_KEYS):
        for strategy_index, strategy in enumerate(STRATEGIES):
            rows = sorted(
                (
                    item
                    for item in trials
                    if item["dataset"] == dataset
                    and item["strategy_key"] == strategy.key
                ),
                key=lambda item: item["max_iters"],
            )
            axis.plot(
                [item["max_iters"] for item in rows],
                [item["accepted_moves"] for item in rows],
                marker="o",
                color=colours(strategy_index % colours.N),
                label=strategy.label,
            )
            for item in rows:
                if item["stop_reason"] == "local_exhaustion":
                    axis.annotate(
                        "local",
                        (item["max_iters"], item["accepted_moves"]),
                        fontsize=6,
                    )
        axis.set_title(next(
            item["dataset_label"]
            for item in trials
            if item["dataset"] == dataset
        ))
        axis.set_xscale("log", base=2)
        axis.set_xticks(budgets, [str(budget) for budget in budgets])
        axis.set_xlabel("max_iters")
        axis.set_ylabel("Accepted moves")
        axis.grid(alpha=0.25)
    figure.legend(
        *axes[-1].get_legend_handles_labels(),
        loc="outside lower center",
        ncols=5,
        fontsize=7,
    )
    figure.savefig(paths["budget_convergence"], dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(
        1, 3, figsize=(15, tall), constrained_layout=True
    )
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


ARTIFACT_NAMES = (
    "results.json",
    "summary.csv",
    "ranked-quality.png",
    "budget-convergence.png",
    "runtime.png",
)


def validate_generated_outputs(
    payload: dict[str, object],
    output_dir: Path,
) -> None:
    missing = [
        name
        for name in ARTIFACT_NAMES
        if not (output_dir / name).is_file()
        or (output_dir / name).stat().st_size == 0
    ]
    if missing:
        raise ValueError(f"Missing or empty artifacts: {', '.join(missing)}")
    saved = json.loads(
        (output_dir / "results.json").read_text(encoding="utf-8")
    )
    with (output_dir / "summary.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    count = len(payload["trials"])
    if len(saved["trials"]) != count or len(rows) != count:
        raise ValueError(f"JSON and CSV must each contain {count} trials.")
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
    transaction = Path(tempfile.mkdtemp(
        prefix=f".{output_dir.name}-",
        dir=output_dir.parent,
    ))
    staging = transaction / "staged"
    backup = transaction / "previous"
    staging.mkdir()
    try:
        if output_dir.exists():
            shutil.copytree(output_dir, staging, dirs_exist_ok=True)
        write_machine_outputs(payload, staging)
        create_charts(payload["trials"], staging)
        validate_generated_outputs(payload, staging)
        had_previous = output_dir.exists()
        if had_previous:
            os.replace(output_dir, backup)
        try:
            os.replace(staging, output_dir)
        except BaseException:
            if had_previous and backup.exists():
                os.replace(backup, output_dir)
            raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the VN priority step-size hyperparameter study."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for results.json, summary.csv and charts.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="Parallel trial processes (1 runs serially).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = load_study_inputs(ROOT)
    payload = run_study(inputs, workers=args.workers)
    publish_outputs(payload, args.output_dir)
    print(
        f"Wrote {len(payload['trials'])} validated trials and analysis "
        f"outputs to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
