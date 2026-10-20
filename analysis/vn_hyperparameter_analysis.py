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
