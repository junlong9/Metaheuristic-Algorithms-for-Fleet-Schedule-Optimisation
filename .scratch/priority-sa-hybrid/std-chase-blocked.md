# Std chase blocked: real min-18 workbook is not in this environment

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

- Worktree `/workspace` — no `heavy_maintenance_forecast.xlsx`
- `origin/main` @ `f9459f4` — file never committed
- `origin/cursor/min16-instance-mismatch-e86d` — only a labelled regenerated proxy under `.scratch/`
- `origin/cursor/min19-infeasibility-report-1858` — report only, no workbook
- GitHub code search for `savn_priority_sa.py` / `basin_hopping_optimise` — no hits on main

Classification: `MISSING`
Reason: the real workbook is not present.

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
