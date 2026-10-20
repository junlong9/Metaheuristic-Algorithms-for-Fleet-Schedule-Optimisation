"""Focused std chase on the local min-18 workbook.

Compatible with the current simulated-annealing and basin-hopping signatures.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import vn_priority_based_selection as baseline
import savn_basin_hopping as basin
import savn_priority_sa as sa

SCRATCH = REPO_ROOT / ".scratch" / "priority-sa-hybrid"
TRIALS_PATH = SCRATCH / "std-chase-trials.json"
REPORT_PATH = SCRATCH / "std-chase-report.md"
LOG_PATH = SCRATCH / "std-chase-local.log"
TARGET_STD = 1.405740

TRIALS = [
    {
        "name": "sa_s99_t1.5",
        "kind": "sa",
        "random_seed": 99,
        "initial_temperature": 1.5,
        "cooling_rate": 0.95,
        "max_iters": 400,
    },
    {
        "name": "sa_s7_t2.0",
        "kind": "sa",
        "random_seed": 7,
        "initial_temperature": 2.0,
        "cooling_rate": 0.95,
        "max_iters": 400,
    },
    {
        "name": "sa_s42_t1.5",
        "kind": "sa",
        "random_seed": 42,
        "initial_temperature": 1.5,
        "cooling_rate": 0.95,
        "max_iters": 400,
    },
    {
        "name": "basin_s7_t2.0_c15_p30",
        "kind": "basin",
        "random_seed": 7,
        "escape_temperature": 2.0,
        "escape_cycles": 15,
        "plateau_moves": 30,
        "baseline_max_iters": 400,
    },
    {
        "name": "basin_s42_t2.0_c15_p30",
        "kind": "basin",
        "random_seed": 42,
        "escape_temperature": 2.0,
        "escape_cycles": 15,
        "plateau_moves": 30,
        "baseline_max_iters": 400,
    },
    {
        "name": "basin_s123_t1.5_c15_p30",
        "kind": "basin",
        "random_seed": 123,
        "escape_temperature": 1.5,
        "escape_cycles": 15,
        "plateau_moves": 30,
        "baseline_max_iters": 400,
    },
    {
        "name": "basin_s99_t2.0_c15_p40",
        "kind": "basin",
        "random_seed": 99,
        "escape_temperature": 2.0,
        "escape_cycles": 15,
        "plateau_moves": 40,
        "baseline_max_iters": 400,
    },
]


def score_list(score):
    return [float(score[0]), float(score[1]), float(score[2])]


def run_trial(schedule, horizon, config):
    started = time.monotonic()
    if config["kind"] == "sa":
        best_schedule, best_score, _ = sa.savn_optimise(
            schedule,
            max_iters=config["max_iters"],
            random_seed=config["random_seed"],
            initial_temperature=config["initial_temperature"],
            cooling_rate=config["cooling_rate"],
            warm_start=True,
        )
    else:
        best_schedule, best_score, _ = basin.basin_hopping_optimise(
            schedule,
            escape_cycles=config["escape_cycles"],
            plateau_moves=config["plateau_moves"],
            random_seed=config["random_seed"],
            escape_temperature=config["escape_temperature"],
            baseline_max_iters=config["baseline_max_iters"],
        )
    elapsed = time.monotonic() - started
    compliant = baseline.is_rule_compliant_schedule(best_schedule, horizon)
    row = {
        "name": config["name"],
        "kind": config["kind"],
        "config": {k: v for k, v in config.items() if k != "name"},
        "min": float(best_score[0]),
        "std": float(-best_score[1]),
        "avg": float(best_score[2]),
        "best_score": score_list(best_score),
        "seconds": elapsed,
        "seed": config["random_seed"],
        "rule_compliant": bool(compliant),
        "label": "REAL",
    }
    return row, best_schedule, best_score


def write_report(payload):
    rows = payload["trials"]
    lines = [
        "# Priority SA std chase (local REAL workbook)",
        "",
        f"Generated: {payload['generated_at']}",
        f"Instance: `{payload['instance_class']}`",
        "",
        f"Original score: `{tuple(payload['original_score'])}`",
        "",
        "| name | kind | seed | min | std | avg | seconds | compliant |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['kind']} | {row['seed']} | "
            f"{row['min']:.6f} | {row['std']:.6f} | {row['avg']:.6f} | "
            f"{row['seconds']:.1f} | {row['rule_compliant']} |"
        )
    best = payload.get("best")
    lines.extend(["", "## Best", ""])
    if best:
        beat = abs(best["min"] - 18.0) < 0.51 and best["std"] < TARGET_STD
        lines.append(f"Best lex score: `{tuple(best['best_score'])}`")
        lines.append("")
        lines.append(
            f"Best std: **{best['std']:.6f}** at min {best['min']:.0f}. "
            f"Beat recorded local basin-hop {TARGET_STD}: **{beat}**."
        )
    else:
        lines.append("No trials.")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    workbook = REPO_ROOT / "heavy_maintenance_forecast.xlsx"
    schedule, base_date = baseline.load_heavy_schedule(
        str(workbook),
        baseline.SHEET_NAME,
    )
    horizon = baseline.get_forecast_horizon(schedule)
    original = baseline.evaluate_schedule(schedule, horizon)
    original_score = score_list(original)
    n_events = sum(len(events) for events in schedule.values())
    print("Original score:", tuple(original_score))
    print("Events:", n_events, "horizon:", horizon, "base:", base_date)
    if abs(original_score[0] - 15.0) > 0.51 or n_events != 278 or horizon != 4480:
        raise SystemExit("Workbook fingerprint is not the local min-18 file.")

    prior = {
        "name": "basin_default_s99_prior",
        "kind": "basin",
        "config": {
            "kind": "basin",
            "random_seed": 99,
            "escape_temperature": 1.5,
            "escape_cycles": 15,
            "plateau_moves": 30,
            "baseline_max_iters": 400,
        },
        "min": 18.0,
        "std": 1.4065339515503619,
        "avg": 21.713010488730195,
        "best_score": [18.0, -1.4065339515503619, 21.713010488730195],
        "seconds": 239.3586152,
        "seed": 99,
        "rule_compliant": True,
        "label": "REAL",
        "source": "local-verification.json",
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instance_class": "REAL",
        "original_score": original_score,
        "horizon": horizon,
        "n_events": n_events,
        "trials": [prior],
        "best": prior,
        "best_score_tuple": prior["best_score"],
        "beat_1_405740": prior["std"] < TARGET_STD,
    }
    TRIALS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_report(payload)

    best_score = tuple(prior["best_score"])
    for config in TRIALS:
        print(f"\n===== REAL trial {config['name']} =====", flush=True)
        row, _schedule, trial_score = run_trial(schedule, horizon, config)
        payload["trials"].append(row)
        if trial_score > tuple(best_score):
            best_score = score_list(trial_score)
            payload["best"] = row
            payload["best_score_tuple"] = row["best_score"]
            payload["beat_1_405740"] = (
                abs(row["min"] - 18.0) < 0.51 and row["std"] < TARGET_STD
            )
        TRIALS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        write_report(payload)
        print(
            f"Trial {config['name']} score: {tuple(row['best_score'])} "
            f"std={row['std']:.6f} seconds={row['seconds']:.1f} "
            f"compliant={row['rule_compliant']}",
            flush=True,
        )

    print("Best score:", tuple(payload["best"]["best_score"]), "REAL")
    print("CHASE_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
