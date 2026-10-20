import json
from collections import Counter, defaultdict
from pathlib import Path

payload = json.loads(Path(__file__).with_name("hyperparameter-results.json").read_text(encoding="utf-8"))
trials = payload["trials"]
print("count", len(trials))
print("elapsed", round(payload["elapsed_seconds"], 1))
print("orig", payload["original_score"])
print("orig_stats", payload["original_stats"])
print("all_compliant", all(trial["rule_compliant"] for trial in trials))
print("mins", Counter(trial["min"] for trial in trials))
print("avgs unique", sorted({round(trial["avg"], 9) for trial in trials}))
print()
print("=== TOP 20 ===")
ranked = sorted(trials, key=lambda trial: trial["score"], reverse=True)
for index, trial in enumerate(ranked[:20], start=1):
    print(
        f"{index:2} {trial['name']:42} "
        f"min={trial['min']:.0f} std={trial['std']:.6f} "
        f"moves={trial['accepted_moves']:3} stop={trial['stopped_at']:3} "
        f"t={trial['elapsed_seconds']:7.1f} {trial['phase']} "
        f"{trial['params']['selection']}"
    )

print()
print("=== BEST PER PHASE ===")
by_phase = defaultdict(list)
for trial in trials:
    by_phase[trial["phase"]].append(trial)
for phase, items in by_phase.items():
    best = max(items, key=lambda trial: trial["score"])
    print(
        f"{phase:22} {best['name']:42} "
        f"min={best['min']:.0f} std={best['std']:.6f} n={len(items)}"
    )

first = [trial for trial in trials if not trial["name"].startswith("refine_")]
print()
print("=== FIRST-PASS MIN 18 ===")
for index, trial in enumerate(
    sorted([trial for trial in first if trial["min"] >= 18], key=lambda item: item["score"], reverse=True),
    start=1,
):
    print(
        f"{index:2} {trial['name']:32} std={trial['std']:.6f} "
        f"moves={trial['accepted_moves']:3} t={trial['elapsed_seconds']:6.1f} "
        f"sel={trial['params']['selection']}"
    )

print()
print("=== FIRST-PASS BELOW 18 ===")
for trial in sorted([item for item in first if item["min"] < 18], key=lambda item: item["score"], reverse=True):
    print(
        f"{trial['name']:32} min={trial['min']:.0f} std={trial['std']:.6f} "
        f"moves={trial['accepted_moves']:3}"
    )
