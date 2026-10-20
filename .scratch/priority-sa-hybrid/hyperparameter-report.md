# Basin-hopping hyperparameter study

## Verdict

**Minimum availability 19 was not found.** The cloud study cannot answer the 18→19 question on your local workbook.

[SA hyperparameter search](bc-06aed119-038e-4ffa-bc9a-b92863a71dc0) ran 146 trials in 3183.7 seconds (~53 minutes) on a **regenerated** `heavy_maintenance_forecast.xlsx`. The original local file was not on `origin/main`, so the remote worktree rebuilt the forecast with `generate_extended_dataset.py`. On that file, greedy polish warm-starts at **min 16**, not 18. Every trial returned min 16.

## Objective and stopping rule

- Primary success: `best_score[0] >= 19`
- Secondary: lexicographic improvement over published baseline `(18.0, -1.413971, 21.713010)`
- Stop at min 19 or after 3600 seconds from first trial

## Baselines

| Source | Score `(min, -std, avg)` | Std |
|---|---|---|
| Published local hill-climb (your workbook) | `(18.0, -1.413971, 21.713010)` | 1.413971 |
| Cloud file warm-start (400-iter polish) | `(16.0, -1.495149, 21.690497)` | 1.495149 |
| Best cloud trial | `(16.0, -1.479924, 21.690497)` | 1.479924 |

Previous local basin-hop (seed 42, T=0.6, 3 moves, 10 cycles) on **your** file: min 18, std 1.413024. That result is still the only evidence on the real workbook.

## Best configuration on the regenerated file

Tied three times at std **1.479924**:

```python
{'escape_cycles': 15, 'escape_moves': 8, 'escape_temperature': 1.5, 'baseline_max_iters': 400, 'random_seed': 99}
```

Also tied: seed 123 with T=2.0 or T=1.5, same depth.

On the regenerated file this is about a **1% std cut** versus the file warm-start. It is **not** a floor improvement and is **not** comparable to the local min-18 baseline.

## What the knobs did

- **Temperature:** mean std T=2.0 (1.488) < 1.5 (1.489) < 1.0 (1.491) < 0.6 (1.494). T=0.6 skipped many first hops (P(accept Δmin=−1)≈0.19).
- **Escape moves:** 8 (mean std 1.485) beat 1 (1.495). Deeper perturbation helped smoothness only.
- **Cycles:** 15 better than 5.
- **Polish iters:** 200 never finished the warm-start and was uniformly worse.

## Failure mode

1213 accepted escape cycles all dropped to **min 15**, then `greedy_polish` snapped back to a **min 16** basin. At the 16-opt there were 1393 feasible VNS-union neighbours and only 3 with min 15; none with min ≥ 17. Same “leave then snap back” pattern as the local 18→17→18 hops, but the attractor here is 16.

322 first-move escapes were skipped (Metropolis rejected every floor-drop neighbour), mostly at T=0.6.

## Best 10 (all still min 16)

| Rank | Name | T | Moves | Cycles | Seed | Std |
|---:|---|---:|---:|---:|---:|---:|
| 1 | seed99_T1.5_m8_c15_it400 | 1.5 | 8 | 15 | 99 | 1.479924 |
| 2 | seed123_T2_m8_c15_it400 | 2.0 | 8 | 15 | 123 | 1.479924 |
| 3 | seed123_T1.5_m8_c15_it400 | 1.5 | 8 | 15 | 123 | 1.479924 |
| 4 | seed123_T1_m8_c15_it400 | 1.0 | 8 | 15 | 123 | 1.480074 |
| 5–7 | seed123 m8 c10 (T 1.0–2.0) | 1–2 | 8 | 10 | 123 | 1.480374 |
| 8 | seed99_T2_m8_c15_it400 | 2.0 | 8 | 15 | 99 | 1.480824 |
| 9 | seed7_T2_m8_c15_it400 | 2.0 | 8 | 15 | 7 | 1.482622 |
| 10 | seed99_T2_m8_c10_it400 | 2.0 | 8 | 10 | 99 | 1.483072 |

All 146 trials are listed in the cloud worktree JSON (27 189 lines). A compact copy is in `hyperparameter-results.json` in this folder.

## Recommended next step

Rerun the high-T / 8-move / 15-cycle slice **locally** on your existing `heavy_maintenance_forecast.xlsx` (the one that already reaches min 18). Until that happens, do not treat this study as evidence that 19 is unreachable.

If that local rerun still snaps 18→17→18:

1. Hop from protected best-so-far, not from every newly polished basin.
2. After the forced floor-drop, take a longer plateau walk (20–40 Metropolis moves) before polish.
3. Tabu the exact pre-escape start so polish cannot walk straight back through the same door.

## Reproduce (only valid on the regenerated remote file)

```bash
python savn_priority_sa.py
```

Best cloud settings, if wired into `basin_hopping_optimise`:

```python
basin_hopping_optimise(
    schedule,
    escape_cycles=15,
    escape_moves=8,
    escape_temperature=1.5,
    baseline_max_iters=400,
    random_seed=99,
)
```
