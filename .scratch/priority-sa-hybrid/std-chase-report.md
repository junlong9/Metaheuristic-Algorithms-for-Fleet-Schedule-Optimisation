# Priority SA std chase

Generated: pending local run
Instance class: `MISSING`
Reason: `heavy_maintenance_forecast.xlsx` is not present on this VM or on `origin/*`.

**This report is not an answer to the user's std-chase.** Instance class is `MISSING`. Do not quote any std below as the local min-18 result.

## Workbook fingerprint

```json
null
```

The real file, when present, must fingerprint as:

- original min ~15
- hill-climb / polish min 18
- 24 aircraft, 278 events
- horizon 4480
- base date 2026-01-21
- average availability 21.713010

Local published targets (REAL file only): hill-climb std 1.413971,
basin-hop std 1.405740, avg 21.713010.

If original min is not ~15 or polish min is 16 not 18, the file is the
seed-42 regenerated proxy (ceiling 16). Those stds are not the answer.

## Trials

_No optimiser trials were run. The real workbook is absent._

## Best

No best score. Local parent must run this script on the real workbook.

Exact printed best_score tuple: **not obtained**.

## How to reproduce locally

```bash
python .scratch/priority-sa-hybrid/chase_std.py
```

`savn_priority_sa.py` was recreated on this branch from the current local
snapshot: staged Metropolis `accept_candidate`, first-level feasible
neighbours, `select_escape_candidate`, classic `savn_optimise`, tabu
`greedy_polish`, and `basin_hopping_optimise` (15 cycles from
best-so-far, one forced floor-drop, 30 plateau moves, T=1.5, seed 99,
polish 400).
