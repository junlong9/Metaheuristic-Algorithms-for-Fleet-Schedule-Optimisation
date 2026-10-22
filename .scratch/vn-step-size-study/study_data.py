"""Shared loading and formatting for the VN step-size study report and workbook."""

from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "docs/reports/2026-10-22-vn-step-size-study"
FIRST_STUDY_DIR = ROOT / "docs/reports/2026-10-20-vn-hyperparameter-analysis"
RESULTS = REPORT_DIR / "results.json"
SHA_CHECK = Path(__file__).with_name("sha-check.json")
DATASETS = ("original", "moderate", "wide")
DATASET_LABELS = {
    "original": "Original",
    "moderate": "Moderate stagger",
    "wide": "Wide stagger",
}
SHORT = {
    "historical_half_step": "Overlapping half-step",
    "live_wide_to_fine": "Wide-to-fine (±56)",
    "dense_pairs": "Dense pairs",
    "half_step_plus_42": "Overlapping + ±42",
    "pairs_28": "Baseline (±28)",
    "pairs_14": "Pairs from ±14",
    "pairs_7": "Pairs from ±7",
    "pairs_3": "Pairs from ±3",
    "pairs_1": "±1 only",
    "pairs_42": "Pairs from ±42",
    "pairs_28_fine_first": "Baseline, fine first",
    "single_set_28": "Single set",
    "overlap_14": "Overlapping, no ±28",
}
QUESTION = {
    "historical_half_step": "First study",
    "live_wide_to_fine": "First study; wide steps",
    "dense_pairs": "First study",
    "half_step_plus_42": "First study; wide step",
    "pairs_28": "Baseline",
    "pairs_14": "Smaller largest step",
    "pairs_7": "Smaller largest step",
    "pairs_3": "Smaller largest step",
    "pairs_1": "Smaller largest step",
    "pairs_42": "Wide step",
    "pairs_28_fine_first": "Search order",
    "single_set_28": "Single set vs ladder",
    "overlap_14": "Overlapping sets",
}
ORIGINAL_KEYS = (
    "historical_half_step",
    "live_wide_to_fine",
    "dense_pairs",
    "half_step_plus_42",
)


def load() -> dict:
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    payload["by_key"] = {item["trial_key"]: item for item in payload["trials"]}
    payload["labels"] = {item["key"]: item["label"] for item in payload["strategies"]}
    payload["sets"] = {item["key"]: item["shift_sets"] for item in payload["strategies"]}
    payload["order"] = [item["key"] for item in payload["strategies"]]
    return payload


def trial(payload: dict, dataset: str, strategy: str, budget: int) -> dict:
    return payload["by_key"][f"{dataset}:{strategy}:{budget}"]


def format_set(level: list[int]) -> str:
    positives = sorted({abs(value) for value in level}, reverse=True)
    symmetric = sorted(level) == sorted(
        [-value for value in positives] + positives
    )
    if symmetric and len(positives) == 1:
        return f"±{positives[0]}"
    if symmetric:
        return "(" + ", ".join(f"±{value}" for value in positives) + ")"
    return "(" + ", ".join(f"{value:+d}" for value in level) + ")"


def format_steps(shift_sets: list[list[int]]) -> str:
    return "; ".join(format_set(level) for level in shift_sets)


def stop_text(item: dict) -> str:
    if item["stop_reason"] == "local_exhaustion":
        return "No improving move"
    return "Iteration limit reached"


def shared_table(payload: dict, budget: int) -> list[dict]:
    rows = []
    for key in payload["order"]:
        cells = [trial(payload, dataset, key, budget) for dataset in DATASETS]
        rows.append({
            "key": key,
            "label": payload["labels"][key],
            "cells": cells,
            "rank_sum": sum(item["dataset_rank"] for item in cells),
            "worst_rank": max(item["dataset_rank"] for item in cells),
        })
    rows.sort(key=lambda row: (row["rank_sum"], row["worst_rank"]))
    return rows
