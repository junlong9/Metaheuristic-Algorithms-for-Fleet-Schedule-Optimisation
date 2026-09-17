# Why a Minimum Availability of 19 Is Not Feasible Under Current Constraints

Heavy maintenance forecast (`heavy_maintenance_forecast.xlsx`), 17 September 2026.

University of Queensland / Northrop Grumman internship report.

This markdown sibling records the same facts as `2026-09-17-min19-infeasibility.docx` so the argument can be reviewed in git without opening Word. The Word file is the user-facing deliverable.

## 1. Executive summary

A minimum daily fleet availability of 19 is not feasible on the current heavy-maintenance instance under the current constraints. The instance admits a hard floor ceiling of 18. The recorded hill-climb already attains that ceiling.

The conclusion does not come from search failure. It follows from a forced-core argument on first D-checks. Each first D must start in a 70-day legal window and lasts 126 days, so every first D occupies a 56-day core `[due, due + 56)` regardless of start. On the user’s local forecast workbook, six first-D cores coincide on day indices 2676–2681 (20–25 May 2033). The six aircraft are Aircraft 11, 14, 15, 19, 24 and Blue-8. On those days at least six aircraft are in the hangar, so availability is at most 18. No feasible start vector can produce a minimum of 19.

Total hangar load does not explain the bound. The workbook contains 10,248 hangar-days over 4,480 days on a 24-aircraft fleet, which is an average of 2.287 aircraft down and an average availability of 21.713. That average is well inside a five-down budget. The obstruction is a local pile-up of first D-checks, not average capacity.

The unoptimised start has minimum 15 (standard deviation 1.950; 20 days at the floor). A frozen hill-climb reaches minimum 18 (standard deviation 1.413971). A local basin-hop also reaches minimum 18, with standard deviation 1.405740. Matching the forced ceiling means the search has already hit the bound.

This report uses measurements from the user’s unpublished local workbook. It does not claim a fresh optimiser run in the cloud, and it does not claim that any run produced a minimum of 19.

## 2. Problem and objective

The optimiser scores a schedule lexicographically as `(min, −std, avg)`: first maximise the minimum daily availability, then minimise the standard deviation of the availability series, then maximise the average availability. Higher tuples are better.

The planning goal under discussion is a minimum of 19. On a 24-aircraft fleet that is equivalent to having at most five aircraft down on every day of the horizon. The remainder of this report shows that this goal is inconsistent with the instance as defined.

## 3. Constraints that define the instance

The following constraints define the instance. They are stated as used by the model.

- CHECK_RULES: A 14/365/42, B 28/730/70, C 84/1460/70, D 126/2920/70
- Sequence A, B, A, C, A, B, A, D
- No overlap on one aircraft; later events rebuilt after a move
- Legal start in [due − early, due]
- First due of each aircraft is frozen from the first event's Latest_Start; first D due = first_due + 365×7; first C due = first_due + 365×3
- No hangar-capacity, crew, or parts limits in the model

The three numbers on each check type are duration, interval and early window, in days. A legal start is any integer day in `[due − early, due]`. After a candidate move, later events on the same aircraft are rebuilt so that the sequence, non-overlap and legal-window rules remain satisfied. The first due of each aircraft is not a search variable: it is taken from the first event’s `Latest_Start` in the forecast. First C and first D dues are offset from that frozen first due as above.

The model does not enforce hangar-bay, crew or parts capacities. Any infeasibility of a minimum of 19 is therefore due to check rules, frozen first dues and the resulting occupancy geometry, not to a shop-capacity constraint.

## 4. Why this is not an average-capacity problem

The figures in this section were measured on the user’s unpublished local workbook `heavy_maintenance_forecast.xlsx`. They are not taken from a regenerated cloud forecast.

**Table 1. Local workbook size and average load**

| Quantity | Value |
| --- | --- |
| Fleet size | 24 aircraft |
| Events | 278 (A 144, B 72, C 38, D 24) |
| Horizon | 4,480 days |
| Base date | 21 January 2026 |
| Hangar-days | 10,248 |
| Average aircraft down | 2.287 |
| Average availability | 21.713 |

**Table 2. Recorded scores on the local instance**

| Source | Minimum availability | Standard deviation | Other recorded detail |
| --- | --- | --- | --- |
| Unoptimised start | 15 | 1.950 | 20 days at the floor |
| Frozen hill-climb | 18 | 1.413971 | Attains the forced-core ceiling |
| Local basin-hop | 18 | 1.405740 | Other 18-optimum; lower standard deviation |

Average load is about 2.3 aircraft down. A minimum of 19 would allow five aircraft down every day. Total hangar-days therefore do not block 19. If the bound were an average-capacity shortage, the 10,248 hangar-days would already exceed 5 × 4,480 hangar-days. They do not. The obstruction must be a concentration of occupancy, not the integral of occupancy.

## 5. The forced-core argument

The binding constraint is the intersection of legal first-D placements.

A first D must start in `[due − 70, due]` and lasts 126 days. Occupancy uses half-open intervals `[start, start + duration)`.

- The earliest legal placement starts at `due − 70` and occupies `[due − 70, due + 56)`.
- The latest legal placement starts at `due` and occupies `[due, due + 126)`.

Any legal start `s` occupies `[s, s + 126)`. The intersection of all such intervals is

`[max s, min (s + 126)) = [due, (due − 70) + 126) = [due, due + 56)`.

That 56-day interval is a forced core: the aircraft is in the hangar on every day of `[due, due + 56)` no matter where the first D starts. Equivalently, core length is duration minus early window: `126 − 70 = 56`.

If `k` first-D cores cover the same calendar day, then at least `k` aircraft are down that day, so availability that day is at most `24 − k`.

This was measured on the user’s workbook using both reconstructed dues (`first Latest_Start + 365×7`) and the actual first-D `Earliest_Start` / `Latest_Start` in the sheet. The two reconstructions produced zero mismatches. All first-D windows are the full 70 days, so every first-D core has length 56.

The forced first-D peak is 6, on 6 days: day indices 2676–2681 (20–25 May 2033). Therefore availability is at most 18 on those days. A minimum of 19 is impossible.

**Table 3. Aircraft on the forced first-D peak**

| Day indices | Calendar dates | Forced first-D peak | Availability ceiling | Aircraft on those cores |
| --- | --- | --- | --- | --- |
| 2676–2681 | 20–25 May 2033 | 6 | 18 | Aircraft 11, 14, 15, 19, 24, Blue-8 |

Forced first-C cores are the analogous 14-day intersections (`84 − 70 = 14`). Their peak is 4. Combining forced C and D cores does not raise the forced peak above 6. The binding constraint is the D pile-up.

## 6. Why the optimiser cannot fix it

The neighbourhood moves one aircraft at a time. Variable-neighbourhood search tries shifts of ±28, ±14, ±7 and ±3 days. A first D can slide only inside its 70-day window. After a move, later events on that aircraft are rebuilt and clamped into their new legal windows.

Those operators cannot remove a first-D forced core. They can only slide the D inside `[due − 70, due]`, which leaves `[due, due + 56)` occupied. They also cannot unfreeze a first due: first dues are instance data.

A basin-hop that forces the schedule from a minimum of 18 down to 17 and then polishes finds only other 18-optima. That is consistent with a hard ceiling of 18, not with a search that is stuck short of 19. Matching a minimum of 18 means the search has already attained the bound.

This report does not claim a new optimiser run in the cloud, and it does not claim that any run produced a minimum of 19.

## 7. Instance contrast

Cloud studies have used a regenerated seed-42 forecast. That file is a different instance. On that file the forced first-D peak is 8, so the availability ceiling is 16.

The present report is only about the user’s local `heavy_maintenance_forecast.xlsx`, on which the forced first-D peak is 6 and the ceiling is 18. Results from the seed-42 file should not be read as statements about the local workbook, and conversely.

## 8. What would make 19 possible

The following are options, not recommendations to implement now.

1. Spread first-start / first-due stagger so that no six first-D cores share a day.
2. Widen the D early window or shorten D duration (a rule change). Either shrinks or moves the forced core; a sufficiently wide early window or short duration can make the core empty.
3. Leave the rules and the instance unchanged and accept 18 as the optimal floor. Search may still reduce standard deviation below 1.405740, but it cannot raise the minimum above 18.

## 9. Conclusion

A minimum availability of 19 is ruled out by a six-aircraft first-D forced core on 20–25 May 2033. The feasible floor on this instance is 18, and the recorded hill-climb already attains it. Further annealing knobs cannot create a 19 while the check rules and frozen first dues remain as stated.
