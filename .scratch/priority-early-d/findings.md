# Earlier D checks in priority-based selection

> Follow-up audit (13 October 2026): the expanded-policy availability figures
> were independently reproduced from the saved Excel rows. The original
> baseline has smaller-check deadline breaches that its validator misses.
> Treat the original baseline row as its reported search output, not a fully
> deadline-compliant schedule. The dynamic 70-day versus dynamic 1,825-day
> comparison is the cleaner policy comparison. See `audit-findings.md` and
> `claim-audit.json` for the corrected interpretation and horizon sensitivity.

The unchanged baseline is `vn_priority_based_selection.py`. Its duplicate is
`vn_priority_based_selection_early_d.py`. This experiment keeps the priority
buckets, greedy improving-only acceptance and lexicographic objective:
worst-day availability, then smoothness, then mean availability.

## What rules would change?

The workbook currently places D checks from December 2032 to October 2034. The
initial D deadline is seven 365-day years after the opening A due date; after a
D completes, the next D deadline is eight 365-day years after completion.
The baseline additionally fixes the sequence to A–B–A–C–A–B–A–D and permits
only 70 days of early D start. Moving a D before 2030 breaks that start window;
it also exceeds the separate loose scenario's 70-day as-loaded displacement
limit. Changing the sequence alone cannot make a years-early D legal.

The copy defaults to 70 days and requires an explicit experimental flag to
enlarge that allowance. These trials allow 1,825 days (5 × 365). ABC early
allowances remain 42/70/70 days, check durations stay 14/28/84/126 days, and all
latest-start deadlines, intervals and non-overlap rules remain mandatory.
Performing D covers smaller checks and resets all four clocks on completion.
A smaller deadline before D starts must still be covered by an earlier check.
Earlier D can bring a second D into the horizon; it is generated and counted.

This is an experiment with different maintenance policy, not a schedule
compliant with the original D allowance and displacement rules. The separate
operational-constraint scenarios are audited below; neither the original
standalone baseline nor the new copy enforces them during search.

## Measured results

All trials use the same 24-aircraft, 278-check input workbook, fixed evaluation
horizon and 400-iteration cap. Runs are deterministic and executed sequentially.
The baseline uses its unchanged default shift ladder; each copy uses the same
ladder, plus first-D jump proposals. The forced scenario applies the before-2030
cap to all 24 aircraft; the optional scenario can choose a subset.

Horizon: 2026-01-21 through 2038-04-28 (4,481 days).

| Approach | Worst day | Std (lower is better) | Mean | D checks | Aircraft with first D before 2030 | Runtime | Converged |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline, default settings | 18 | 1.413971 | 21.713010 | 24 | 0 | 49.7s | True |
| New copy, 70-day D allowance | 18 | 1.472819 | 21.635349 | 24 | 0 | 66.6s | True |
| New copy, optional D up to 1,825 days early | 19 | 0.844500 | 21.599643 | 28 | 4 | 38.1s | True |
| New copy, every first D before 2030 | 18 | 1.405715 | 21.415979 | 45 | 24 | 25.0s | True |

The previously published tuned baseline achieved worst-day availability 18 and standard deviation 1.391860. This is a historical reference from the hyperparameter report, not a new runtime-matched trial.

The optional expanded-D trial is **better than the default baseline** under the priority objective. The all-before-2030 trial is **better than the default baseline**. These are search outcomes under the stated budgets, not proofs of global optimality.

Selective early D is the stronger result here: it raises worst-day
availability to 19, beating both the default and historical tuned baseline's
18, with four first D checks before 2030 and 20 in both busy periods. Both loose
dependency groups pass. Mean availability declines from 21.713010 to 21.599643,
and D checks increase from 24 to 28. This is an availability trade-off under
an explicitly relaxed D policy, not a free reduction in maintenance.

Forcing every first D before 2030 returns worst-day availability 18. Although
its smoothness is slightly better than the default baseline, it is worse than
the historical tuned baseline and breaches the second dependency group on 14
days, leaving only one of its aircraft available instead of the required two.
It therefore is not an acceptable solution under the loose operational rules.
It also produces 45 D checks in the horizon. The tested evidence supports
allowing selective early D, rather than forcing the entire fleet before 2030.

## Maintenance burden and operational audit

| Approach | A / B / C / D counts | Full check days | Downtime days within horizon | First D date range | D checks >70 days early | Busy-period minima | Dependency-group breaches |
| --- | --- | ---: | ---: | --- | ---: | --- | --- |
| Baseline, default settings | 144 / 72 / 38 / 24 | 10,248 | 10,248 | 2032-11-12 to 2034-10-11 | 0 | 18 / 18 | 0 / 0 |
| New copy, 70-day D allowance | 145 / 72 / 43 / 24 | 10,682 | 10,596 | 2032-11-10 to 2034-10-14 | 0 | 18 / 18 | 0 / 0 |
| New copy, optional D up to 1,825 days early | 146 / 73 / 39 / 28 | 10,892 | 10,756 | 2028-04-01 to 2034-10-11 | 17 | 20 / 20 | 0 / 0 |
| New copy, every first D before 2030 | 143 / 72 / 25 / 45 | 11,788 | 11,579 | 2028-01-21 to 2029-12-31 | 24 | 21 / 20 | 0 / 14 |

Busy-period columns refer to 27 April–26 May and 14 September–13 October 2033.
The loose scenario requires 15 in both. A proposed requirement of 20 must be
checked against these values separately. Dependency columns report days below
two available aircraft in each of the two four-aircraft groups.

The 70-day dynamic trial isolates another modelling difference: the copy
generates checks until all terminal due clocks extend beyond the horizon,
including checks that finish beyond it. The original baseline replays only
the supplied check count. Consequently the copy can include extra late-horizon
maintenance even without expanding the D allowance. Its initial rebuilt
metrics are saved in `comparison-results.json`; do not attribute all baseline
differences solely to earlier D. Full planned durations and within-horizon
downtime are reported separately. An extended-horizon study would be needed
to establish long-term maintenance cost or utilisation effects.

All new-copy serialized schedules passed an independent replay using literal
intervals, durations and allowances, plus per-aircraft daily occupancy and
terminal coverage. Baseline validity uses its unchanged validator and an
independent daily-occupancy calculation. The enlarged-policy audit does not
claim original 70-day-window compliance.

## Run the duplicate

```powershell
python vn_priority_based_selection_early_d.py
python vn_priority_based_selection_early_d.py --d-early-days 1825 --experimental-early-d
python vn_priority_based_selection_early_d.py --d-early-days 1825 --experimental-early-d --first-d-before 2030-01-01
```

The default output is `optimised_priority_early_d_output.xlsx`; choose another
with `--output`. It contains the original and optimised checks and availability,
comparison chart, search history, and an explicit experimental-policy sheet.
The audited comparison workbooks are in this folder under each trial's name.
The copy optimises first D placements; later D checks are rebuilt at due dates.
It imports the existing early-D planner for maintenance-clock logic, which in
turn reads the canonical rule definitions from the original baseline.

## Tests and reproducibility

```powershell
python -m unittest test_vn_priority_based_selection_early_d test_vn_priority_based_selection -q
python .scratch/priority-early-d/run_comparison.py
python .scratch/priority-early-d/write_report.py
```

Six new-copy tests and nine baseline tests pass. The existing early-D suite has
one unrelated failing test: `test_too_long_C_falls_back_to_covering_B` builds a
70-day plan and validates its stored window metadata as a 730-day plan. Neither
the existing planner nor that test was modified. The runner reuses completed
JSON trials; use a new folder/remove only those generated results for a fresh
comparison. Input, source and result hashes are stored with the results.
