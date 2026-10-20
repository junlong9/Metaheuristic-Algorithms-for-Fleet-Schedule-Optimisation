# Availability 20 during a busy period

Status: ready-for-human

## Request

Test whether at least 20 aircraft can be made available during a busy period by sacrificing availability elsewhere, then reconsider the choice between priority-based selection and the annealing candidate. This extends the old study, which rejected operationally invalid starts without repair and optimised a global availability score.

## Confirmed dates and surrounding availability

The user confirmed testing both existing busy windows and allowing lower availability outside the target while reporting the trade-off. These are the assumptions used when tests began. Keep maintenance rules mandatory. For an achievable window, retain the loose scenario's 70-day displacement limit and two dependency groups requiring two of four aircraft daily. Measure the immediately surrounding 30 days as well as the full forecast. Requiring 20 in both windows simultaneously is infeasible because the April to May window is infeasible by itself.

## Experiment

`check_windows.py` verifies date alignment and computes the invariant first-D occupancy bound. April to May is impossible at 20, so no search is spent on it. September to October has a D-only upper bound of 20, requiring constructive verification.

`run_comparison.py` loads the original baseline computational definitions, omitting unavailable plotting imports only. It changes scoring and priority ordering in memory within the isolated process. No published model, optimiser, workbook, operational config or presentation is edited.

The busy target is a repair objective while searching and a hard requirement for success. Score components are the busy minimum capped at 20, negative aircraft-day deficit below 20, then outside minimum minus full-forecast standard deviation divided by 100. The final component gives outside availability priority over smoothness because the 24-aircraft standard deviation cannot approach 100. Search first targets checks overlapping the lowest busy-period availability; after repair it returns to ordinary worst-day priority.

Both methods use the tuned half-step neighbourhoods, as-loaded start and retained hard constraints. Priority has a 400-iteration cap and a 60-second budget. Candidate uses seeds 1, 2 and 3, a 60-second budget and an 80-iteration warm-start and polish cap to allow actual annealing escapes. Other candidate settings remain at existing defaults. This is a screening comparison; the candidate's cap differs from the previous 400-iteration decision setting.

An initial 60-second candidate pilot spent its budget on deterministic warm-up and did not perform escapes. That run was excluded from the actual annealing comparison and preserved in `pilot-warm-only-results.json`. The priority result was reused. The active candidate runs each performed escape moves and returned best-so-far schedules.

## Result and limits

April to May cannot reach 20: six mandatory first-D checks overlap on 20 to 25 May 2033. September to October is constructively feasible: priority reaches 20 and retains 18 over the full forecast. Each actual annealing screen reaches 20 but retains only 17 outside. Priority reaches the target after seven accepted moves and has better final smoothness than the three candidate screens.

The priority schedule gains 56 aircraft-days in the busy period relative to the earlier saved unconstrained priority export and loses 56 outside it. The preceding 30-day minimum changes from 19 to 18. This reference export is maintenance compliant but violates the new 70-day displacement limit on four checks, so it is not an eligible constrained competitor.

All serialized outputs were reloaded under the unmodified computational rules and checked independently for maintenance compliance, retained operational limits, daily availability and conserved downtime. Search budgets were reached, so no convergence or global smoothness optimum is claimed. Results support the adapted priority method for this particular window, retained constraints and screening budget. Broader method ranking remains open.

## Deliverable

`docs/reports/2026-10-12-busy-period-20-tradeoff.docx` is an addendum to the Semester 2 report. Original reports and the live deck are preserved.
