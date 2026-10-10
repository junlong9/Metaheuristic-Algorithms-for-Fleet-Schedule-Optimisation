# Iteration 2 handover

Semester 2 asked whether basin-hopping should replace the frozen priority hill-climb, and whether dummy operational limits can sit on top of it. This note records what was measured on the canonical heavy forecast. It does not fill in numbers for runs that did not finish.

## Recommendation

Drop the candidate method. Its median smoothness was 1.390417, a gain of 0.001444 on the tuned baseline's 1.391860. The keep rule needs a gain of at least 0.005, worst-day availability 18 on every seed, and a typical run within 5 minutes. The smoothness spread across seeds was 0.001445, the typical runtime was 306.3s, and every seed held worst-day availability 18: yes. Recommend the tuned baseline instead: the frozen hill-climb, called with the half-step neighbourhoods (28 with 14, then 14 with 7, then 7 with 3, then 3 with 1, either direction) and a 400-iteration cap. Leave the published defaults in the baseline module unchanged, and pass those neighbourhoods in from the caller.

Worst-day availability 19 is infeasible on this forecast. The 17 September note shows six opening D checks force the floor to 18 or below, so later work should not spend itself hunting 19.

Classic simulated annealing, from the earlier local chase, stayed at smoothness 1.413971 with worst-day availability 18. That is the published baseline smoothness. It is an ablation, not the method under test, and it was not re-run here.

## How a worse move is accepted

The execution-plan deck says a move that lowers worst-day availability is always rejected. The candidate method does not do that. Early on, a high temperature may accept that move, and it becomes rare as the search cools. The reported schedule is the best-so-far, so a dip is not what is handed back. Tightened acceptance is the fallback: it rejects a lower worst day before the temperature draw. The deck was left as presented.

## Decision runs

Same half-step neighbourhoods for the tuned baseline and the candidate method. The baseline is one run because it is deterministic. The candidate and the tightened fallback are the median of seeds 1, 2, and 3. A run that passes 5 minutes is stopped.

| Run | Result |
| --- | --- |
| Tuned baseline | worst day 18, smoothness 1.391860, 115.6s |
| candidate-seed-1 | worst day 18, smoothness 1.389453, 285.5s |
| candidate-seed-2 | worst day 18, smoothness 1.390417, 318.4s timed out |
| candidate-seed-3 | worst day 18, smoothness 1.390898, 306.3s timed out |
| tightened-seed-1 | worst day 18, smoothness 1.391860, 56.4s |
| tightened-seed-2 | worst day 18, smoothness 1.391860, 63.5s |
| tightened-seed-3 | worst day 18, smoothness 1.391860, 106.3s |

## Start schedules

The opening check on each aircraft is pinned to its due date by the maintenance replay, so a start schedule cannot move it. Bunched and spread move the next check, the first one the replay will place somewhere else in its start window, then rebuild. Due dates stay the same. These runs are unconstrained, so the start effect is not mixed with the operational limits. The candidate run from each start uses seed 1.

| Start | Before search | Tuned baseline | Candidate, seed 1 |
| --- | --- | --- | --- |
| as-loaded | worst day 15, smoothness 1.949767, 0.0s | worst day 18, smoothness 1.391860, 63.3s | worst day 18, smoothness 1.389453, 306.8s timed out |
| bunched | worst day 15, smoothness 1.955482, 0.0s | worst day 18, smoothness 1.404629, 47.8s | worst day 18, smoothness 1.401288, 169.5s |
| spread | worst day 15, smoothness 1.978174, 0.0s | worst day 18, smoothness 1.417282, 93.2s | worst day 18, smoothness 1.416022, 224.5s |

## Operational limits

Limits live in operational_constraints.json. The workbook was not edited. Busy periods cover 27 April to 26 May 2033 and 14 September to 13 October 2033, the busy stretches in the loaded forecast. Displacement limits are 70, 42, and 21 days from the as-loaded start. No group of four aircraft stays at three available on every day of the loaded plan, so loose and medium ask for two of four, which the loaded plan meets, and tight asks for three of four plus a busy-period floor of 16, which the loaded plan does not. Tight is reported infeasible. There is no repair.

| Scenario | Result |
| --- | --- |
| loose | worst day 18, smoothness 1.506731, 16.5s; breaches after search: 0 |
| medium | worst day 18, smoothness 1.717945, 3.3s; breaches after search: 0 |
| tight | infeasible at the loaded schedule; busy period days 2653-2682 worst-day availability 15 is below 16; busy period days 2793-2822 worst-day availability 15 is below 16; dependency group Blue-6, Blue-7, Blue-8, Blue-9 falls to 2 available; dependency group Aircraft 11, Aircraft 12, Aircraft 13, Aircraft 16 falls to 2 available |

## Settings sweep

One setting at a time, on the tuned neighbourhoods, with no operational limits, seed 99. The hour cap stopped the list if it was still going. A second seed was used only for the best finished variant, and only if time remained. The decision-run defaults (temperature 1.5, 15 escape cycles, 30 plateau moves, 400 polish iterations) were not repeated inside the hour. The extra seed of escape temperature 1.0 was stopped at 5 minutes during its opening polish, so that row is not a finished repeat of the setting.

| Variant | Result |
| --- | --- |
| escape_temperature_1.0-seed-99 | worst day 18, smoothness 1.389293, 142.8s |
| escape_temperature_2.0-seed-99 | worst day 18, smoothness 1.391219, 164.3s |
| escape_cycles_8-seed-99 | worst day 18, smoothness 1.391219, 308.3s timed out |
| escape_cycles_25-seed-99 | worst day 18, smoothness 1.391860, 311.6s timed out |
| plateau_moves_15-seed-99 | worst day 18, smoothness 1.389614, 191.3s |
| plateau_moves_45-seed-99 | worst day 18, smoothness 1.391860, 379.3s timed out |
| polish_iterations_200-seed-99 | worst day 18, smoothness 1.396183, 416.5s timed out |
| polish_iterations_800-seed-99 | worst day 18, smoothness 1.391860, 721.3s timed out |
| escape_temperature_1.0-seed-1 | worst day 18, smoothness 1.403993, 301.7s timed out |

## Footnote on the cloud settings study

An earlier 146-trial cloud study rebuilt the heavy forecast because the canonical workbook was not on the remote branch. That rebuilt file warm-started at worst-day availability 16, not 18. Those trials are not comparable with the numbers above.
