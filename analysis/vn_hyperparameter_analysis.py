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

OUTPUT_DIR = ROOT / "docs/reports/2026-10-20-vn-hyperparameter-analysis"
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
                    index
                    for index, strategy in enumerate(STRATEGIES)
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
                item
                for item in trials
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
    "stop_reason",
    "elapsed_seconds",
    "lexicographic_score",
    "dataset_rank",
    "rule_compliant",
    "endpoint_sha256",
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
