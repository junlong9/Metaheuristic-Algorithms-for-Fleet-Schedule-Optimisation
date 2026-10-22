# Verification of the early-D result

13 October 2026

The saved result's worst-day availability of **19**, standard deviation of
**0.8444998319922753**, and mean availability of **21.599642936844454** are
correct for the expanded-policy schedule over 21 January 2026 to 28 April 2038.
This is a research result under different rules, not compliance with the
original policy or proof that the search algorithm alone is better.

## Independent checks

`audit_claim.py` imports neither optimiser. It reads the input and exported
Excel rows directly, checks every aircraft is present, compares the export's
original rows against the input, replays literal maintenance intervals,
checks durations and non-overlap, and reconstructs daily per-aircraft
occupancy. The reconstructed availability matches every saved day and the
summary figures. The input SHA256 still matches the original comparison.

The delivered workbook was exclusively locked by another process, so the
audit read `.scratch/priority-early-d/expanded_1825.xlsx`, the saved export
copied into the delivered workbook in the previous turn. It does not verify
any unsaved changes to the currently open workbook.

No required checks are missing under the expanded policy. Checks crossing the
forecast end retain their full duration; within-horizon occupancy is clipped
only for scoring. The audit deliberately removes a D check and inflates
availability by one aircraft, and detects both errors. It also rejects the
actual saved result when the D allowance is restored to 70 days.

## Why the result improves

The experiment expands the D early-start allowance from **70 to 1,825 days**,
allows D to cover earlier smaller checks, and resets the covered clocks on
completion. Seventeen D checks exceed the original 70-day window, although
only four aircraft have their first D before 2030. The original displacement
limits also remain relaxed. This gives the search much more calendar freedom.

The scheduled work is spread over more years, so a better worst day and lower
standard deviation are plausible. It is not a reduction in maintenance burden:
there are **28 D checks instead of 24**, and **10,756 unavailable aircraft-days
instead of the baseline's 10,248** in the measured horizon. Mean availability
is lower. Full planned check days are 10,892 versus 10,248. Monetary cost,
maintenance capacity, crews, parts and utilisation are not modelled.

The result passes both loose dependency groups and achieves 20 in both busy
periods. It fails the tight dependency groups, with 75 and 117 breach days;
its groups reach two available aircraft whereas that scenario requires three.
Passing the medium group and busy-period requirements does not mean passing
the medium scenario overall: its displacement limit still fails.

## Correction to the baseline comparison

The original baseline validator checks the selected check's own window and
fixed sequence, but does not require that all pending smaller deadlines are
covered by the start of a larger check. Independent replay found **37 pending
deadline violations across 24 checks** in the saved baseline. The as-loaded
forecast has 40 such violations. This problem predates the early-D copy.

For example, Aircraft 12's first four checks have start days 435, 730, 1121
and 1505. After B and A complete, B is due on day 1488 and A on day 1500.
C starts on day 1505: **17 days after B is due and 5 days after A is due**,
even though C is within its own start window. Performing C then cannot
retroactively cover those overdue days. The original validator accepts this
four-check example; the new copy rejects it.

The earlier progress update said 19 days for this B delay; the correct delay
is 17 days. The separate availability figure of 19 aircraft is unaffected.

The saved baseline also has terminal maintenance obligations on or before
28 April 2038 for seven aircraft which its fixed-count replay does not add.
Consequently its "valid" label must be understood as passing its existing
validator, not full clock coverage. The original algorithm and input workbook
were left unchanged.

The cleaner comparison is **dynamic planner with 70-day D allowance: worst
day 18, std 1.472819**, versus **the same planner with 1,825 days: worst day
19, std 0.844500**. Both pass independent complete clock replay for their
respective policies. This supports an improvement from allowing early D;
it does not isolate a superior search algorithm under unchanged rules.

## Forecast-end sensitivity

Both saved dynamic schedules were held fixed, then continued with legal
maintenance at due dates, without optimising the added years. Independent
replay validates both extended plans. The continuation uses only the normal
70-day allowance for newly generated D choices, which is also a subset of
the expanded policy. These are sensitivity checks, not optimal future plans.

| Forecast end | Dynamic 70-day policy: worst day | Expanded D policy: worst day |
| --- | ---: | ---: |
| 28 April 2038 | 18 | 19 |
| 28 April 2040 | 18 | 19 |
| 28 April 2046 | 17 | 18 |

The result is not solely caused by excluding the next D check at the horizon.
It survives a two-year extension, but **19 is not a permanent availability
guarantee**. Longer-horizon optimisation and a cost/capacity model would be
needed for adoption as an operational policy.

## Reproduce

```powershell
python .scratch/priority-early-d/audit_claim.py
python -m unittest test_vn_priority_based_selection_early_d test_vn_priority_based_selection -q
```

Audit details, hashes, individual D advances, deadline breaches, operational
scenario checks and extension metrics are saved in `claim-audit.json`.
The new minimized regression example checks that the copy rejects the baseline
validator's late-small-check pattern. Seven copy tests and nine baseline tests
pass. No original optimiser code was changed.
