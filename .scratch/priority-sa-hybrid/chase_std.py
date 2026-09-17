#!/usr/bin/env python3
"""Std-chase runner for savn_priority_sa.py.

Refuses to treat a missing or seed-42 regenerated workbook as the user's
min-18 instance. Parent / local machines that have
``heavy_maintenance_forecast.xlsx`` (original min ~15, hill-climb min 18,
278 events, horizon 4480, base 2026-01-21, avg ~21.713) can run:

    python .scratch/priority-sa-hybrid/chase_std.py

Use ``--allow-proxy`` only to smoke-test the SA machinery on a regenerated
file. Every proxy number is labelled PROXY / NOT THE USER FILE.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import savn_priority_based_selection as baseline
import savn_priority_sa as sa


SCRATCH_DIR = REPO_ROOT / ".scratch" / "priority-sa-hybrid"
DEFAULT_WORKBOOK = REPO_ROOT / "heavy_maintenance_forecast.xlsx"
BLOCKED_PATH = SCRATCH_DIR / "std-chase-blocked.md"
REPORT_PATH = SCRATCH_DIR / "std-chase-report.md"
TRIALS_PATH = SCRATCH_DIR / "std-chase-trials.json"
BEST_XLSX = REPO_ROOT / "optimised_priority_sa_output.xlsx"

REAL_EVENTS = 278
REAL_HORIZON = 4480
REAL_BASE_DATE = "2026-01-21"
REAL_AVG = 21.713010
REAL_HILLCLIMB_MIN = 18.0
LOCAL_BASIN_STD = 1.405740
LOCAL_HILLCLIMB_STD = 1.413971

PROXY_EVENTS = 279
PROXY_HORIZON = 4503
PROXY_BASE_DATE = "2026-01-15"
PROXY_AVG = 21.690497


def _iso_date(value):
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def fingerprint_schedule(schedule, base_date, horizon=None):
    horizon = (
        baseline.get_forecast_horizon(schedule) if horizon is None else horizon
    )
    original_score = sa.score_tuple(
        baseline.evaluate_schedule(schedule, horizon)
    )
    n_events = sum(len(events) for events in schedule.values())
    check_counts = {}
    for events in schedule.values():
        for event in events:
            check_counts[event["check"]] = check_counts.get(event["check"], 0) + 1

    return {
        "n_aircraft": len(schedule),
        "n_events": n_events,
        "check_counts": check_counts,
        "horizon": int(horizon),
        "base_date": _iso_date(base_date),
        "original_score": list(original_score),
        "original_min": original_score[0],
        "original_std": -original_score[1],
        "original_avg": original_score[2],
    }


def classify_instance(fingerprint, hillclimb_min=None):
    """Return REAL, PROXY, or UNKNOWN plus a reason."""

    original_min = fingerprint["original_min"]
    avg = fingerprint["original_avg"]
    events = fingerprint["n_events"]
    horizon = fingerprint["horizon"]
    base_date = fingerprint["base_date"]

    looks_proxy = (
        abs(original_min - 12.0) < 0.51
        or (hillclimb_min is not None and abs(hillclimb_min - 16.0) < 0.51)
        or events == PROXY_EVENTS
        or horizon == PROXY_HORIZON
        or base_date == PROXY_BASE_DATE
        or abs(avg - PROXY_AVG) < 0.002
    )
    looks_real = (
        abs(original_min - 15.0) < 0.51
        and events == REAL_EVENTS
        and horizon == REAL_HORIZON
        and base_date == REAL_BASE_DATE
        and abs(avg - REAL_AVG) < 0.01
        and (
            hillclimb_min is None
            or abs(hillclimb_min - REAL_HILLCLIMB_MIN) < 0.51
        )
    )

    if looks_real and not looks_proxy:
        return "REAL", (
            "Original min ~15, 278 events, horizon 4480, base 2026-01-21, "
            f"avg ~21.713, hill-climb min={hillclimb_min}."
        )
    if looks_proxy:
        return "PROXY", (
            "Matches the seed-42 regenerated forecast (min 12→16, 279 events, "
            "horizon 4503, base 2026-01-15, avg ~21.690), not the user file."
        )
    if hillclimb_min is not None and abs(hillclimb_min - 16.0) < 0.51:
        return "PROXY", "Warm-start/polish min is 16, not 18."
    if abs(original_min - 15.0) > 0.51:
        return "PROXY", (
            f"Original min {original_min} is not ~15; treating as PROXY."
        )
    return "UNKNOWN", "Fingerprint does not match the published real or proxy file."


def search_workbooks(extra_paths=None):
    candidates = []
    seen = set()
    search_roots = [REPO_ROOT, Path.cwd()]
    names = (
        "heavy_maintenance_forecast.xlsx",
        "regenerated_heavy_maintenance_forecast.xlsx",
    )
    extra = [Path(p) for p in (extra_paths or [])]
    queued = extra + [
        root / name for root in search_roots for name in names
    ]
    queued.append(SCRATCH_DIR / "regenerated_heavy_maintenance_forecast.xlsx")

    for path in queued:
        resolved = path.resolve() if path.exists() else path
        if resolved in seen:
            continue
        seen.add(resolved)
        candidates.append({
            "path": str(path),
            "exists": path.is_file(),
        })
    return candidates


def planned_trials():
    """Small focused set — not a 146-trial grid."""

    trials = [
        {
            "name": "basin_default_s99",
            "kind": "basin",
            "escape_cycles": 15,
            "plateau_moves": 30,
            "escape_temperature": 1.5,
            "baseline_max_iters": 400,
            "random_seed": 99,
        },
        {
            "name": "sa_s7_t1.5",
            "kind": "sa",
            "max_iters": 400,
            "t0": 1.5,
            "cooling_rate": 0.95,
            "warm_start": True,
            "random_seed": 7,
            "baseline_max_iters": 400,
        },
        {
            "name": "sa_s42_t1.5",
            "kind": "sa",
            "max_iters": 400,
            "t0": 1.5,
            "cooling_rate": 0.95,
            "warm_start": True,
            "random_seed": 42,
            "baseline_max_iters": 400,
        },
        {
            "name": "sa_s99_t1.0",
            "kind": "sa",
            "max_iters": 400,
            "t0": 1.0,
            "cooling_rate": 0.95,
            "warm_start": True,
            "random_seed": 99,
            "baseline_max_iters": 400,
        },
        {
            "name": "sa_s99_t1.5",
            "kind": "sa",
            "max_iters": 400,
            "t0": 1.5,
            "cooling_rate": 0.95,
            "warm_start": True,
            "random_seed": 99,
            "baseline_max_iters": 400,
        },
        {
            "name": "sa_s99_t2.0",
            "kind": "sa",
            "max_iters": 400,
            "t0": 2.0,
            "cooling_rate": 0.95,
            "warm_start": True,
            "random_seed": 99,
            "baseline_max_iters": 400,
        },
        {
            "name": "basin_deep_c20_p40_s99_t1.5",
            "kind": "basin",
            "escape_cycles": 20,
            "plateau_moves": 40,
            "escape_temperature": 1.5,
            "baseline_max_iters": 400,
            "random_seed": 99,
        },
        {
            "name": "basin_deep_c15_p60_s7_t2.0",
            "kind": "basin",
            "escape_cycles": 15,
            "plateau_moves": 60,
            "escape_temperature": 2.0,
            "baseline_max_iters": 400,
            "random_seed": 7,
        },
        {
            "name": "basin_deep_c20_p40_s42_t2.0",
            "kind": "basin",
            "escape_cycles": 20,
            "plateau_moves": 40,
            "escape_temperature": 2.0,
            "baseline_max_iters": 400,
            "random_seed": 42,
        },
        {
            "name": "basin_deep_c15_p40_s123_t1.5",
            "kind": "basin",
            "escape_cycles": 15,
            "plateau_moves": 40,
            "escape_temperature": 1.5,
            "baseline_max_iters": 400,
            "random_seed": 123,
        },
    ]
    return trials


def run_one_trial(schedule, horizon, config, deadline_monotonic=None):
    started = time.monotonic()
    if config["kind"] == "sa":
        best_schedule, best_score, result = sa.savn_optimise(
            schedule,
            max_iters=config["max_iters"],
            t0=config["t0"],
            cooling_rate=config["cooling_rate"],
            warm_start=config.get("warm_start", True),
            random_seed=config["random_seed"],
            baseline_max_iters=config.get("baseline_max_iters", 400),
        )
    else:
        best_schedule, best_score, result = sa.basin_hopping_optimise(
            schedule,
            escape_cycles=config["escape_cycles"],
            plateau_moves=config["plateau_moves"],
            escape_temperature=config["escape_temperature"],
            baseline_max_iters=config.get("baseline_max_iters", 400),
            random_seed=config["random_seed"],
            deadline_monotonic=deadline_monotonic,
        )

    elapsed = time.monotonic() - started
    compliant = baseline.is_rule_compliant_schedule(best_schedule, horizon)
    print("Trial", config["name"], "score:", best_score)
    print("Rule compliant:", compliant)
    print(f"Seconds: {elapsed:.3f}")

    record = {
        "name": config["name"],
        "kind": config["kind"],
        "config": {k: v for k, v in config.items() if k != "name"},
        "min": best_score[0],
        "std": -best_score[1],
        "avg": best_score[2],
        "best_score": list(best_score),
        "seconds": elapsed,
        "seed": config["random_seed"],
        "rule_compliant": bool(compliant),
        "timed_out": bool(result.get("timed_out", False)),
    }
    return record, best_schedule, best_score


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def write_blocked_markdown(path, payload):
    searched = "\n".join(
        f"- `{item['path']}` exists={item['exists']}"
        for item in payload["searched_paths"]
    )
    extra_search = payload.get("extra_search_notes") or (
        "- `origin/main` @ `f9459f4` — `heavy_maintenance_forecast.xlsx` was never committed\n"
        "- `origin/cursor/min16-instance-mismatch-e86d` — labelled regenerated proxy only\n"
        "- `origin/cursor/min19-infeasibility-report-1858` — report only, no workbook\n"
        "- GitHub code search for `savn_priority_sa.py` / `basin_hopping_optimise` — absent on main"
    )
    text = f"""# Std chase blocked: real min-18 workbook is not in this environment

The lowest availability standard deviation that simulated annealing can
reach on the **user's** `heavy_maintenance_forecast.xlsx` was **not
measured here**. Do not treat any number in this folder as that answer
unless a later local run writes `instance_class: REAL`.

## Why this VM cannot answer

`heavy_maintenance_forecast.xlsx` is untracked and is not on `origin/main`
(commit `f9459f4`) or on the other `origin/*` branches checked for this
task (`cursor/min16-instance-mismatch-e86d`,
`cursor/min19-infeasibility-report-1858`). Git history never contained the
file. `savn_priority_sa.py` was also missing from main and was recreated
from the current local snapshot spec.

The published local instance is:

| Field | Real user file | Seed-42 regenerated proxy |
|---|---|---|
| Aircraft | 24 | 24 |
| Original min | **~15** | **12** |
| Hill-climb / polish min | **18** | **16** |
| Events | **278** | **279** |
| Horizon | **4480** | **4503** |
| Base date | **2026-01-21** | **2026-01-15** |
| Average availability | **21.713010** | **21.690497** |
| Hill-climb std | 1.413971 | 1.495149 |
| Recorded local basin-hop std | **1.405740** | n/a (different instance) |

A prior cloud 146-trial grid ran on the proxy and must not be reused as
the std-chase result. This script does **not** call
`generate_extended_dataset.py`.

## Search performed

{searched}

{extra_search}

Classification: `{payload['instance_class']}`
Reason: {payload['reason']}

## What the parent should run locally

Place the real workbook next to `savn_priority_sa.py` (do not regenerate
it) and run:

```bash
python .scratch/priority-sa-hybrid/chase_std.py
```

The runner will print the original score, refuse to continue if the
fingerprint is the seed-42 proxy, and otherwise execute the focused
std-chase (default basin-hop, a few classic SA seeds / T0 values, then
two or three deeper basin-hops). Each trial prints the full lex score
and checks `is_rule_compliant_schedule`.

Success on the real file: `score[0] == 18` and `score[1] > -1.405740`
(i.e. std < 1.405740). The best std is recorded even if it does not beat
that number.

`--allow-proxy` exists only for machinery smoke tests. Every proxy figure
must stay labelled **PROXY / NOT THE USER FILE**.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def write_report(path, payload):
    instance = payload["instance_class"]
    header_note = ""
    if instance != "REAL":
        header_note = (
            "\n\n**This report is not an answer to the user's std-chase.** "
            f"Instance class is `{instance}`. "
            "Do not quote any std below as the local min-18 result.\n"
        )

    rows = payload.get("trials") or []
    if rows:
        table_lines = [
            "| name | kind | seed | min | std | avg | seconds | compliant |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
        for row in rows:
            tag = "" if instance == "REAL" else " PROXY"
            table_lines.append(
                f"| {row['name']}{tag} | {row['kind']} | {row['seed']} | "
                f"{row['min']:.6f} | {row['std']:.6f} | {row['avg']:.6f} | "
                f"{row['seconds']:.1f} | {row['rule_compliant']} |"
            )
        table = "\n".join(table_lines)
    else:
        table = "_No optimiser trials were run. The real workbook is absent._"

    best = payload.get("best_real") or payload.get("best")
    if best and instance == "REAL":
        beat = best["std"] < LOCAL_BASIN_STD and abs(best["min"] - 18.0) < 0.51
        best_block = (
            f"Best lex score: `{tuple(best['best_score'])}`\n\n"
            f"Best std: **{best['std']:.6f}** at min {best['min']:.1f}. "
            f"Beat recorded local basin-hop 1.405740: **{beat}**."
        )
    elif best:
        best_block = (
            f"PROXY best lex score (NOT THE USER FILE): "
            f"`{tuple(best['best_score'])}` — std {best['std']:.6f}."
        )
    else:
        best_block = (
            "No best score. Local parent must run this script on the real "
            "workbook."
        )

    fingerprint = payload.get("fingerprint")
    fingerprint_json = json.dumps(fingerprint, indent=2) if fingerprint else "null"
    expected_real = (
        "Expected REAL fingerprint: original min ~15, polish min 18, "
        "24 aircraft, 278 events, horizon 4480, base 2026-01-21, "
        f"avg {REAL_AVG}."
    )
    if payload.get("best_score_tuple"):
        best_tuple_text = str(tuple(payload["best_score_tuple"]))
    else:
        best_tuple_text = "not obtained"
    text = f"""# Priority SA std chase

Generated: {payload['generated_at']}
Instance class: `{instance}`
Reason: {payload.get('reason', '')}
{header_note}
## Workbook fingerprint

```json
{fingerprint_json}
```

{expected_real}

Local published targets (REAL file only): hill-climb std {LOCAL_HILLCLIMB_STD},
basin-hop std {LOCAL_BASIN_STD}, avg {REAL_AVG}.

If original min is not ~15 or polish min is 16 not 18, the file is the
seed-42 regenerated proxy (ceiling 16). Those stds are not the answer.

## Trials

{table}

## Best

{best_block}

Exact printed best_score tuple: `{best_tuple_text}`.

## How to reproduce locally

```bash
python .scratch/priority-sa-hybrid/chase_std.py
```

`savn_priority_sa.py` on this branch is the recreated local snapshot:
staged Metropolis `accept_candidate`, first-level feasible neighbours,
`select_escape_candidate`, classic `savn_optimise`, tabu `greedy_polish`,
and `basin_hopping_optimise` (15 cycles from best-so-far, one forced
floor-drop, 30 plateau moves, T=1.5, seed 99, polish 400).
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main():
    parser = argparse.ArgumentParser(
        description="Focused std chase for priority SA (real workbook only).",
    )
    parser.add_argument("--file-path", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--sheet-name", default=baseline.SHEET_NAME)
    parser.add_argument("--allow-proxy", action="store_true")
    parser.add_argument("--budget-seconds", type=float, default=90 * 60)
    parser.add_argument("--smoke", action="store_true",
                        help="Run only the default basin-hop config.")
    args = parser.parse_args()

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    searched = search_workbooks([args.file_path])
    file_path = Path(args.file_path)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "searched_paths": searched,
        "instance_class": "MISSING",
        "reason": f"{file_path} is not present.",
        "fingerprint": None,
        "trials": [],
        "best": None,
        "best_real": None,
        "best_score_tuple": None,
        "beat_1_405740": None,
        "label": None,
    }

    if not file_path.is_file():
        write_json(TRIALS_PATH, payload)
        write_blocked_markdown(BLOCKED_PATH, payload)
        write_report(REPORT_PATH, payload)
        print("BLOCKED: real heavy_maintenance_forecast.xlsx is absent.")
        print("Wrote", BLOCKED_PATH)
        print("Wrote", REPORT_PATH)
        print("Wrote", TRIALS_PATH)
        return 2

    schedule, base_date = baseline.load_heavy_schedule(
        str(file_path),
        args.sheet_name,
    )
    horizon = baseline.get_forecast_horizon(schedule)
    fingerprint = fingerprint_schedule(schedule, base_date, horizon)
    print("Original score:", tuple(fingerprint["original_score"]))
    print("Fingerprint:", json.dumps(fingerprint, indent=2))

    # Cheap hill-climb / polish min for classification. Full 400-iter polish
    # is the warm start the trials would run anyway; for classification we
    # only need to know whether the floor is 16 or 18. Use the same polish.
    print("Classification polish (greedy, 400 iters)...")
    _polished, polish_score, _, _ = sa.greedy_polish(
        schedule,
        horizon,
        max_iters=400,
    )
    print("Warm-start / polish score:", polish_score)
    instance, reason = classify_instance(fingerprint, polish_score[0])
    payload["fingerprint"] = fingerprint
    payload["instance_class"] = instance
    payload["reason"] = reason
    payload["polish_score"] = list(polish_score)
    print(f"Instance class: {instance} ({reason})")

    if instance != "REAL" and not args.allow_proxy:
        write_json(TRIALS_PATH, payload)
        write_blocked_markdown(BLOCKED_PATH, payload)
        write_report(REPORT_PATH, payload)
        print(
            "BLOCKED: workbook is not the user's min-18 file. "
            "Refusing to present scores. Use --allow-proxy only for a "
            "labelled PROXY smoke test."
        )
        return 3

    label = "REAL" if instance == "REAL" else "PROXY / NOT THE USER FILE"
    payload["label"] = label
    configs = planned_trials()
    if args.smoke:
        configs = configs[:1]

    deadline = time.monotonic() + args.budget_seconds
    best_row = None
    best_schedule = None
    best_score = None

    for config in configs:
        if time.monotonic() >= deadline:
            print("Budget exhausted; stopping before", config["name"])
            break
        print(f"\n===== {label} trial {config['name']} =====")
        record, trial_schedule, trial_score = run_one_trial(
            schedule,
            horizon,
            config,
            deadline_monotonic=deadline,
        )
        record["label"] = label
        payload["trials"].append(record)
        if best_score is None or trial_score > best_score:
            best_score = trial_score
            best_row = record
            best_schedule = trial_schedule
        write_json(TRIALS_PATH, payload)

    payload["best"] = best_row
    payload["best_score_tuple"] = best_row["best_score"] if best_row else None
    if instance == "REAL":
        payload["best_real"] = best_row
        payload["beat_1_405740"] = bool(
            best_row
            and abs(best_row["min"] - 18.0) < 0.51
            and best_row["std"] < LOCAL_BASIN_STD
        )
        if payload["beat_1_405740"] and best_schedule is not None:
            sa.export_result(
                str(BEST_XLSX),
                schedule,
                best_schedule,
                tuple(fingerprint["original_score"]),
                best_score,
                base_date,
                horizon,
            )
    else:
        print("PROXY / NOT THE USER FILE — scores are not the user result.")

    write_json(TRIALS_PATH, payload)
    if instance != "REAL":
        write_blocked_markdown(BLOCKED_PATH, payload)
    write_report(REPORT_PATH, payload)
    print("Wrote", REPORT_PATH)
    print("Wrote", TRIALS_PATH)
    if best_row:
        print("Best score:", tuple(best_row["best_score"]), label)
    return 0 if instance == "REAL" else 3


if __name__ == "__main__":
    raise SystemExit(main())
