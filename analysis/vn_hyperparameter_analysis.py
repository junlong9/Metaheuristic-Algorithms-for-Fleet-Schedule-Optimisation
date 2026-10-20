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
