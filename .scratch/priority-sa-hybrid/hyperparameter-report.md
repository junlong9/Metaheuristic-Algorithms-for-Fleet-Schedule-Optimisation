# Basin-hopping hyperparameter study

## Objective and stopping rule

Primary objective: raise worst-day (minimum) fleet availability from 18 to **19** on `heavy_maintenance_forecast.xlsx` sheet `MxEvents`.

Primary success: returned `best_score[0] >= 19`.

Secondary (only if 19 is never found): lexicographic improvement over baseline `[18.0, -1.4139714343833762, 21.713010488730195]`, i.e. same min 18 with strictly better `-std` (less variation).

Stopping rule: stop immediately after a trial with min ≥ 19, or when elapsed wall time since the **first trial start** exceeds 3600 seconds. New escape cycles are not started after that deadline.

## Input data note

`heavy_maintenance_forecast.xlsx` was **not present on the remote worktree**. It was regenerated with `generate_extended_dataset.py` (fleet 24, 12 years, seed 42, first starts from `Simple Random Fleet Plans.xlsx`). Warm-start polish on this regenerated file reaches **min 16**, not the previously reported min 18. The published baseline score below is kept for comparison with the earlier local study; this run also treats the observed warm-start score as the file-specific baseline.

## Baseline and previously known result

- Previously reported frozen hill-climb baseline (`savn_priority_based_selection.py` on the missing local workbook): `(min, -std, avg) = [18.0, -1.4139714343833762, 21.713010488730195]` (std = 1.413971434383).
- Previously known basin-hopping default: seed 42, `escape_cycles=10`, `escape_moves=3`, `escape_temperature=0.6`, `baseline_max_iters=400`. Every cycle returned min 18; best std 1.413024 vs baseline 1.413971 (tiny secondary win). Runtime ~42s.
- Earlier continuous SA at T=0.3 / cooling 0.995 never accepted a min drop to 17 (too cold). At the local optimum a large share of neighbours are min=17, so escapes are available if T is high enough.

## Study meta

- Trials recorded: **146** (0 crashes)
- Study wall seconds: **3183.7** (grid finished before the 3600s cap)
- Reached min 19: **no**
- Reached min 17 or 18: **no** — every returned score had min **16**
- File-specific warm-start (400-iter polish): `(16.0, -1.4951485551728732, 21.690497335701597)` (std = 1.495148555173)
- Stop reason: `completed_grid`
- Escape statistics: 1213 polished cycles, all escaped to min **15** then polished to min **16**; 322 first-move escapes skipped (Metropolis rejected every floor-drop neighbour)
- Neighbourhood at the 16 local opt: 1393 feasible VNS-union neighbours, of which only **3** have min 15. There is no min-17/18/19 neighbour of the warm-start.

## Every trial

| name | seed | T | moves | cycles | iters | wall s | min | std | avg | vs baseline | min≥19 | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| seed42_T0.6_m3_c10_it400 | 42 | 0.6 | 3 | 10 | 400 | 16.0 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=8; escaped below 18 then polished back without reaching 19 |
| seed42_T2_m8_c10_it400 | 42 | 2 | 8 | 10 | 400 | 28.5 | 16.0000 | 1.487556 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T2_m8_c15_it400 | 42 | 2 | 8 | 15 | 400 | 36.6 | 16.0000 | 1.486511 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T2_m5_c10_it400 | 42 | 2 | 5 | 10 | 400 | 24.5 | 16.0000 | 1.488302 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed42_T2_m5_c15_it400 | 42 | 2 | 5 | 15 | 400 | 29.0 | 16.0000 | 1.487705 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed42_T2_m3_c10_it400 | 42 | 2 | 3 | 10 | 400 | 22.6 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T2_m3_c15_it400 | 42 | 2 | 3 | 15 | 400 | 23.4 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m8_c10_it400 | 42 | 1.5 | 8 | 10 | 400 | 29.3 | 16.0000 | 1.488451 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m8_c15_it400 | 42 | 1.5 | 8 | 15 | 400 | 38.6 | 16.0000 | 1.488302 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m5_c10_it400 | 42 | 1.5 | 5 | 10 | 400 | 26.8 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m5_c15_it400 | 42 | 1.5 | 5 | 15 | 400 | 28.9 | 16.0000 | 1.491134 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m3_c10_it400 | 42 | 1.5 | 3 | 10 | 400 | 20.7 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m3_c15_it400 | 42 | 1.5 | 3 | 15 | 400 | 27.3 | 16.0000 | 1.486361 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m8_c10_it400 | 42 | 1 | 8 | 10 | 400 | 27.3 | 16.0000 | 1.489346 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m8_c15_it400 | 42 | 1 | 8 | 15 | 400 | 33.7 | 16.0000 | 1.488899 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m5_c10_it400 | 42 | 1 | 5 | 10 | 400 | 22.1 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m5_c15_it400 | 42 | 1 | 5 | 15 | 400 | 26.9 | 16.0000 | 1.491134 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m3_c10_it400 | 42 | 1 | 3 | 10 | 400 | 19.4 | 16.0000 | 1.492771 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m3_c15_it400 | 42 | 1 | 3 | 15 | 400 | 25.7 | 16.0000 | 1.492324 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed7_T2_m8_c10_it400 | 7 | 2 | 8 | 10 | 400 | 31.5 | 16.0000 | 1.489793 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T2_m8_c15_it400 | 7 | 2 | 8 | 15 | 400 | 33.4 | 16.0000 | 1.482622 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T2_m5_c10_it400 | 7 | 2 | 5 | 10 | 400 | 22.7 | 16.0000 | 1.488749 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T2_m5_c15_it400 | 7 | 2 | 5 | 15 | 400 | 29.2 | 16.0000 | 1.488749 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T2_m3_c10_it400 | 7 | 2 | 3 | 10 | 400 | 18.2 | 16.0000 | 1.493514 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed7_T2_m3_c15_it400 | 7 | 2 | 3 | 15 | 400 | 21.8 | 16.0000 | 1.492473 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m8_c10_it400 | 7 | 1.5 | 8 | 10 | 400 | 28.4 | 16.0000 | 1.490240 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m8_c15_it400 | 7 | 1.5 | 8 | 15 | 400 | 30.2 | 16.0000 | 1.488451 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m5_c10_it400 | 7 | 1.5 | 5 | 10 | 400 | 21.3 | 16.0000 | 1.488749 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m5_c15_it400 | 7 | 1.5 | 5 | 15 | 400 | 26.6 | 16.0000 | 1.488749 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m3_c10_it400 | 7 | 1.5 | 3 | 10 | 400 | 18.5 | 16.0000 | 1.494852 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m3_c15_it400 | 7 | 1.5 | 3 | 15 | 400 | 22.9 | 16.0000 | 1.494852 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m8_c10_it400 | 7 | 1 | 8 | 10 | 400 | 28.5 | 16.0000 | 1.486511 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m8_c15_it400 | 7 | 1 | 8 | 15 | 400 | 36.0 | 16.0000 | 1.485764 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m5_c10_it400 | 7 | 1 | 5 | 10 | 400 | 20.1 | 16.0000 | 1.489048 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m5_c15_it400 | 7 | 1 | 5 | 15 | 400 | 23.9 | 16.0000 | 1.489048 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m3_c10_it400 | 7 | 1 | 3 | 10 | 400 | 17.8 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m3_c15_it400 | 7 | 1 | 3 | 15 | 400 | 20.4 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T2_m8_c10_it400 | 99 | 2 | 8 | 10 | 400 | 26.7 | 16.0000 | 1.483072 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed99_T2_m8_c15_it400 | 99 | 2 | 8 | 15 | 400 | 32.6 | 16.0000 | 1.480824 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T2_m5_c10_it400 | 99 | 2 | 5 | 10 | 400 | 22.5 | 16.0000 | 1.485465 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T2_m5_c15_it400 | 99 | 2 | 5 | 15 | 400 | 25.8 | 16.0000 | 1.485315 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T2_m3_c10_it400 | 99 | 2 | 3 | 10 | 400 | 17.2 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T2_m3_c15_it400 | 99 | 2 | 3 | 15 | 400 | 20.9 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m8_c10_it400 | 99 | 1.5 | 8 | 10 | 400 | 27.1 | 16.0000 | 1.483072 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m8_c15_it400 | 99 | 1.5 | 8 | 15 | 400 | 32.9 | 16.0000 | 1.479924 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m5_c10_it400 | 99 | 1.5 | 5 | 10 | 400 | 22.3 | 16.0000 | 1.485465 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m5_c15_it400 | 99 | 1.5 | 5 | 15 | 400 | 27.5 | 16.0000 | 1.485315 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m3_c10_it400 | 99 | 1.5 | 3 | 10 | 400 | 18.6 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m3_c15_it400 | 99 | 1.5 | 3 | 15 | 400 | 19.3 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m8_c10_it400 | 99 | 1 | 8 | 10 | 400 | 23.5 | 16.0000 | 1.486809 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m8_c15_it400 | 99 | 1 | 8 | 15 | 400 | 29.0 | 16.0000 | 1.485614 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m5_c10_it400 | 99 | 1 | 5 | 10 | 400 | 19.0 | 16.0000 | 1.491134 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m5_c15_it400 | 99 | 1 | 5 | 15 | 400 | 23.6 | 16.0000 | 1.488600 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m3_c10_it400 | 99 | 1 | 3 | 10 | 400 | 18.8 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m3_c15_it400 | 99 | 1 | 3 | 15 | 400 | 19.5 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed123_T2_m8_c10_it400 | 123 | 2 | 8 | 10 | 400 | 23.9 | 16.0000 | 1.480374 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T2_m8_c15_it400 | 123 | 2 | 8 | 15 | 400 | 29.7 | 16.0000 | 1.479924 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T2_m5_c10_it400 | 123 | 2 | 5 | 10 | 400 | 23.2 | 16.0000 | 1.486361 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed123_T2_m5_c15_it400 | 123 | 2 | 5 | 15 | 400 | 30.0 | 16.0000 | 1.483521 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed123_T2_m3_c10_it400 | 123 | 2 | 3 | 10 | 400 | 20.0 | 16.0000 | 1.489644 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed123_T2_m3_c15_it400 | 123 | 2 | 3 | 15 | 400 | 23.3 | 16.0000 | 1.489197 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed123_T1.5_m8_c10_it400 | 123 | 1.5 | 8 | 10 | 400 | 29.7 | 16.0000 | 1.480374 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T1.5_m8_c15_it400 | 123 | 1.5 | 8 | 15 | 400 | 34.6 | 16.0000 | 1.479924 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T1.5_m5_c10_it400 | 123 | 1.5 | 5 | 10 | 400 | 24.3 | 16.0000 | 1.488899 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T1.5_m5_c15_it400 | 123 | 1.5 | 5 | 15 | 400 | 30.2 | 16.0000 | 1.487705 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T1.5_m3_c10_it400 | 123 | 1.5 | 3 | 10 | 400 | 20.9 | 16.0000 | 1.489644 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T1.5_m3_c15_it400 | 123 | 1.5 | 3 | 15 | 400 | 23.3 | 16.0000 | 1.487556 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m8_c10_it400 | 123 | 1 | 8 | 10 | 400 | 26.8 | 16.0000 | 1.480374 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m8_c15_it400 | 123 | 1 | 8 | 15 | 400 | 31.5 | 16.0000 | 1.480074 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m5_c10_it400 | 123 | 1 | 5 | 10 | 400 | 20.5 | 16.0000 | 1.488899 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m5_c15_it400 | 123 | 1 | 5 | 15 | 400 | 26.5 | 16.0000 | 1.488004 | 21.690497 | worse_min | no | skipped_cycles=6; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m3_c10_it400 | 123 | 1 | 3 | 10 | 400 | 27.3 | 16.0000 | 1.489197 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m3_c15_it400 | 123 | 1 | 3 | 15 | 400 | 25.4 | 16.0000 | 1.489197 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed2026_T2_m8_c10_it400 | 2026 | 2 | 8 | 10 | 400 | 32.6 | 16.0000 | 1.488004 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed2026_T2_m8_c15_it400 | 2026 | 2 | 8 | 15 | 400 | 35.8 | 16.0000 | 1.487705 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed2026_T2_m5_c10_it400 | 2026 | 2 | 5 | 10 | 400 | 24.0 | 16.0000 | 1.489346 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed2026_T2_m5_c15_it400 | 2026 | 2 | 5 | 15 | 400 | 30.1 | 16.0000 | 1.489197 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed2026_T2_m3_c10_it400 | 2026 | 2 | 3 | 10 | 400 | 26.2 | 16.0000 | 1.493366 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed2026_T2_m3_c15_it400 | 2026 | 2 | 3 | 15 | 400 | 22.3 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed2026_T1.5_m8_c10_it400 | 2026 | 1.5 | 8 | 10 | 400 | 28.8 | 16.0000 | 1.488004 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed2026_T1.5_m8_c15_it400 | 2026 | 1.5 | 8 | 15 | 400 | 40.8 | 16.0000 | 1.483521 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed2026_T1.5_m5_c10_it400 | 2026 | 1.5 | 5 | 10 | 400 | 21.8 | 16.0000 | 1.490389 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed2026_T1.5_m5_c15_it400 | 2026 | 1.5 | 5 | 15 | 400 | 26.8 | 16.0000 | 1.490389 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed2026_T1.5_m3_c10_it400 | 2026 | 1.5 | 3 | 10 | 400 | 21.3 | 16.0000 | 1.493366 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed2026_T1.5_m3_c15_it400 | 2026 | 1.5 | 3 | 15 | 400 | 22.8 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m8_c10_it400 | 2026 | 1 | 8 | 10 | 400 | 28.5 | 16.0000 | 1.485166 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m8_c15_it400 | 2026 | 1 | 8 | 15 | 400 | 32.0 | 16.0000 | 1.484717 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m5_c10_it400 | 2026 | 1 | 5 | 10 | 400 | 22.7 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m5_c15_it400 | 2026 | 1 | 5 | 15 | 400 | 26.0 | 16.0000 | 1.490687 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m3_c10_it400 | 2026 | 1 | 3 | 10 | 400 | 19.6 | 16.0000 | 1.493663 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m3_c15_it400 | 2026 | 1 | 3 | 15 | 400 | 21.9 | 16.0000 | 1.492622 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed42_T0.6_m1_c5_it400 | 42 | 0.6 | 1 | 5 | 400 | 14.7 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T0.6_m1_c10_it400 | 42 | 0.6 | 1 | 10 | 400 | 19.4 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=6; escaped below 18 then polished back without reaching 19 |
| seed42_T0.6_m3_c5_it400 | 42 | 0.6 | 3 | 5 | 400 | 16.5 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T0.6_m5_c5_it400 | 42 | 0.6 | 5 | 5 | 400 | 18.3 | 16.0000 | 1.494703 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed42_T0.6_m5_c10_it400 | 42 | 0.6 | 5 | 10 | 400 | 22.9 | 16.0000 | 1.494703 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m1_c5_it400 | 42 | 1 | 1 | 5 | 400 | 14.3 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed42_T1_m1_c10_it400 | 42 | 1 | 1 | 10 | 400 | 15.7 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed42_T1_m3_c5_it400 | 42 | 1 | 3 | 5 | 400 | 14.0 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T1_m5_c5_it400 | 42 | 1 | 5 | 5 | 400 | 16.2 | 16.0000 | 1.493217 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T0.6_m1_c5_it400 | 7 | 0.6 | 1 | 5 | 400 | 13.7 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed7_T0.6_m1_c10_it400 | 7 | 0.6 | 1 | 10 | 400 | 12.8 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed7_T0.6_m3_c5_it400 | 7 | 0.6 | 3 | 5 | 400 | 11.7 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed7_T0.6_m3_c10_it400 | 7 | 0.6 | 3 | 10 | 400 | 13.6 | 16.0000 | 1.494703 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed7_T0.6_m5_c5_it400 | 7 | 0.6 | 5 | 5 | 400 | 13.7 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed7_T0.6_m5_c10_it400 | 7 | 0.6 | 5 | 10 | 400 | 14.9 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=6; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m1_c5_it400 | 7 | 1 | 1 | 5 | 400 | 14.0 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed7_T1_m1_c10_it400 | 7 | 1 | 1 | 10 | 400 | 14.4 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m3_c5_it400 | 7 | 1 | 3 | 5 | 400 | 14.2 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed7_T1_m5_c5_it400 | 7 | 1 | 5 | 5 | 400 | 15.9 | 16.0000 | 1.489644 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T0.6_m1_c5_it400 | 99 | 0.6 | 1 | 5 | 400 | 13.4 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T0.6_m1_c10_it400 | 99 | 0.6 | 1 | 10 | 400 | 12.4 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=8; escaped below 18 then polished back without reaching 19 |
| seed99_T0.6_m3_c5_it400 | 99 | 0.6 | 3 | 5 | 400 | 13.8 | 16.0000 | 1.494703 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T0.6_m3_c10_it400 | 99 | 0.6 | 3 | 10 | 400 | 15.8 | 16.0000 | 1.492919 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T0.6_m5_c5_it400 | 99 | 0.6 | 5 | 5 | 400 | 15.4 | 16.0000 | 1.490240 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed99_T0.6_m5_c10_it400 | 99 | 0.6 | 5 | 10 | 400 | 18.4 | 16.0000 | 1.490240 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m1_c5_it400 | 99 | 1 | 1 | 5 | 400 | 12.3 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m1_c10_it400 | 99 | 1 | 1 | 10 | 400 | 13.0 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m3_c5_it400 | 99 | 1 | 3 | 5 | 400 | 13.3 | 16.0000 | 1.493811 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed99_T1_m5_c5_it400 | 99 | 1 | 5 | 5 | 400 | 15.3 | 16.0000 | 1.491580 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed123_T0.6_m1_c5_it400 | 123 | 0.6 | 1 | 5 | 400 | 13.1 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T0.6_m1_c10_it400 | 123 | 0.6 | 1 | 10 | 400 | 13.8 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed123_T0.6_m3_c5_it400 | 123 | 0.6 | 3 | 5 | 400 | 14.0 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed123_T0.6_m3_c10_it400 | 123 | 0.6 | 3 | 10 | 400 | 16.2 | 16.0000 | 1.491729 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed123_T0.6_m5_c5_it400 | 123 | 0.6 | 5 | 5 | 400 | 16.5 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed123_T0.6_m5_c10_it400 | 123 | 0.6 | 5 | 10 | 400 | 19.9 | 16.0000 | 1.488899 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m1_c5_it400 | 123 | 1 | 1 | 5 | 400 | 13.9 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed123_T1_m1_c10_it400 | 123 | 1 | 1 | 10 | 400 | 15.2 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed123_T1_m3_c5_it400 | 123 | 1 | 3 | 5 | 400 | 15.9 | 16.0000 | 1.489644 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed123_T1_m5_c5_it400 | 123 | 1 | 5 | 5 | 400 | 16.4 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed2026_T0.6_m1_c5_it400 | 2026 | 0.6 | 1 | 5 | 400 | 12.8 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed2026_T0.6_m1_c10_it400 | 2026 | 0.6 | 1 | 10 | 400 | 13.4 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=6; escaped below 18 then polished back without reaching 19 |
| seed2026_T0.6_m3_c5_it400 | 2026 | 0.6 | 3 | 5 | 400 | 12.8 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=4; escaped below 18 then polished back without reaching 19 |
| seed2026_T0.6_m3_c10_it400 | 2026 | 0.6 | 3 | 10 | 400 | 15.2 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=7; escaped below 18 then polished back without reaching 19 |
| seed2026_T0.6_m5_c5_it400 | 2026 | 0.6 | 5 | 5 | 400 | 14.9 | 16.0000 | 1.494852 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed2026_T0.6_m5_c10_it400 | 2026 | 0.6 | 5 | 10 | 400 | 17.4 | 16.0000 | 1.494852 | 21.690497 | worse_min | no | skipped_cycles=5; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m1_c5_it400 | 2026 | 1 | 1 | 5 | 400 | 12.9 | 16.0000 | 1.495149 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m1_c10_it400 | 2026 | 1 | 1 | 10 | 400 | 14.2 | 16.0000 | 1.495000 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m3_c5_it400 | 2026 | 1 | 3 | 5 | 400 | 14.1 | 16.0000 | 1.493663 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed2026_T1_m5_c5_it400 | 2026 | 1 | 5 | 5 | 400 | 14.8 | 16.0000 | 1.491878 | 21.690497 | worse_min | no | skipped_cycles=3; escaped below 18 then polished back without reaching 19 |
| seed42_T2_m5_c10_it200 | 42 | 2 | 5 | 10 | 200 | 19.9 | 16.0000 | 1.493811 | 21.690497 | worse_min | no | skipped_cycles=1; escaped below 18 then polished back without reaching 19 |
| seed42_T1.5_m5_c10_it200 | 42 | 1.5 | 5 | 10 | 200 | 18.6 | 16.0000 | 1.493811 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed7_T2_m5_c10_it200 | 7 | 2 | 5 | 10 | 200 | 19.4 | 16.0000 | 1.490687 | 21.690497 | worse_min | no | escaped below 18 then polished back without reaching 19 |
| seed7_T1.5_m5_c10_it200 | 7 | 1.5 | 5 | 10 | 200 | 19.0 | 16.0000 | 1.490687 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T2_m5_c10_it200 | 99 | 2 | 5 | 10 | 200 | 17.3 | 16.0000 | 1.491283 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |
| seed99_T1.5_m5_c10_it200 | 99 | 1.5 | 5 | 10 | 200 | 17.0 | 16.0000 | 1.491432 | 21.690497 | worse_min | no | skipped_cycles=2; escaped below 18 then polished back without reaching 19 |

## Best configuration

Best trial **seed99_T1.5_m8_c15_it400** (tied with `seed123_T2_m8_c15_it400` and `seed123_T1.5_m8_c15_it400` on the exact same score) returned

`[16.0, -1.4799243660442156, 21.690497335701597]`

(min=16.0, std=1.4799243660442156, avg=21.690497335701597) in 32.9s.

Hyperparameter dict:

```python
{'escape_cycles': 15, 'escape_moves': 8, 'escape_temperature': 1.5, 'baseline_max_iters': 400, 'random_seed': 99}
```

Why this is best:

- No trial raised the floor, so the lexicographic winner is the lowest std at min 16.
- Std 1.479924 beats the file-specific 400-iter warm-start std 1.495149 by about **1.02%** (secondary win *on this workbook*, not vs the missing local min-18 baseline).
- The same score was reached by three deep-escape configs (T∈{1.5,2.0}, moves=8, cycles=15, seeds 99 and 123). That cluster is the robust recommendation: **high T, 8 escape moves, 15 cycles, 400 polish iters**.
- Mean std by knob: T=2.0 (1.488) < T=1.5 (1.489) < T=1.0 (1.491) < T=0.6 (1.494); moves=8 (1.485) << moves=1 (1.495); cycles=15 better than 5. `baseline_max_iters=200` never finished the warm-start (std 1.560 at warm-start) and was uniformly worse.

The `vs baseline` column is `worse_min` for every row because it compares against the previously published min-18 score. Versus the *file* warm-start, 137/146 trials strictly improved `-std` at the same min 16.

## Did any trial reach min 19?

**No.** No trial reached min 18 or even min 17.

## What failed

- All 146 trials finished at min 16. Across all trials, **322** escape cycles were skipped because the first required floor-drop was not Metropolis-accepted (most common at T=0.6, where P(accept Δmin=−1)=exp(−1/0.6)≈0.189 and only 3 eligible neighbours exist).
- Observed failure mode on this regenerated workbook: every accepted first escape went to **min 15** (1213/1213 polished cycles), then `greedy_polish` climbed back to a **min 16** basin. Sometimes that basin had a slightly better std; never a higher floor.
- This is the same “escape then snap back” pattern reported for the missing local min-18 file (there: 18 → 17 → 18). Here the attractor is 16, and the 16-opt has **no** neighbour with min ≥ 17.
- Known seed-42 default (`T=0.6, moves=3, cycles=10`) skipped 8/10 cycles and returned the warm-start unchanged (std 1.495149). Too cold, too shallow.
- `baseline_max_iters=200` stops polish ~147 steps early (full warm-start needs 347 improve-only steps) and cannot match the 400-iter local opt.

The published secondary target (same min 18, better std than 1.413971) could not be tested: the input workbook that produced that baseline is not on the remote.

## Recommended next experiment

Stay with this basin-hopping algorithm (do not invent a new one). 19 is not a neighbour of the current 16-opt, and 8-move / 15-cycle hops still polish back to 16, so more of the same grid will only shave std.

Next run, in order:

1. Recover the original `heavy_maintenance_forecast.xlsx` that produced the published min-18 baseline and repeat the high-T / 8-move / 15-cycle slice *on that file*. The 18→19 question is still unanswered if that workbook differs.
2. On whichever file is used: keep escaping from the **protected best-so-far** instead of walking `current` to every newly polished local opt, so later cycles do not drift away from the best 16/18 basin.
3. After the forced floor-drop, take a *longer* plateau walk (20–40 worse-or-equal Metropolis moves) before polish. Eight moves was the best knob this hour but still snapped back.
4. During the post-escape polish, reject any candidate that restores the exact pre-escape start vector (tabu the basin door). That is still VNS + Metropolis, just with a short tabu on the hop that was used to leave.

## Reproduce the best run

```bash
python savn_priority_sa.py --escape-cycles 15 --escape-moves 8 --escape-temperature 1.5 --baseline-max-iters 400 --random-seed 99
```

Equivalent one-off study row:

```bash
python others/run_sa_hyperparameter_study.py --single --escape-cycles 15 --escape-moves 8 --escape-temperature 1.5 --baseline-max-iters 400 --random-seed 99
```
