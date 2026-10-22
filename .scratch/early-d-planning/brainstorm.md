# Early D maintenance planning proposal

Status: ready-for-human

## User direction

Explore an algorithm that moves D checks substantially earlier, potentially by years, and replaces smaller checks covered by the D. This is a research scenario rather than the original fixed 70-day early-start model. The previous infeasibility proof remains correct for that original model and does not establish infeasibility under this new policy.

## Important implementation distinction

The current baseline fixes the check sequence to A, B, A, C, A, B, A, D. It resets A, B, C and D due clocks after D, but cannot replace an earlier A, B or C slot with an early D. Enlarging the start window alone does not enable arbitrary sequence changes. The new planner needs to choose both check type and time from the aircraft's maintenance-clock state. A smaller check with a deadline before the proposed D start must still be performed; replacement cannot retrospectively cure an overdue check.

The operational displacement limit also needs an explicit new policy for D checks. The old 70-day as-loaded limit is incompatible with a D move years early. Retain latest-start deadlines, non-overlap, check durations and dependency groups. Vary the permitted early-D allowance separately from any displacement rule.

## A concrete smaller change to investigate first

Aircraft 15 and Blue-8 are two of the six D checks forced down during 20 to 25 May 2033. A 126-day D starting on 22 December 2032 finishes at the beginning of 27 April 2033 and therefore avoids the entire April to May busy window. This is 99 days before Aircraft 15's D due date, and 101 days before Blue-8's due date, versus the current allowance of 70 days. Their preceding loaded A checks finish before the proposed date.

These are calendar illustrations, not a full-fleet feasibility result. They suggest testing modest extensions before paying the cost of moving D checks by years. Other D checks, A/B/C maintenance, displacement rules, dependency availability and later clock resets still need verification. See calendar-options.json and inspect_options.py.

## Proposed algorithm

Use priority-based repair inside a larger search that changes maintenance plans.

1. Identify dates with an availability deficit and the aircraft whose D checks create the overlap. During a six-aircraft D overlap, target 20 requires at least two of those D checks to be absent, before considering other maintenance.
2. Select a small subset of conflicting aircraft. Prefer changes that remove more busy-period deficit for less unused D interval and less surrounding downtime.
3. Generate early D start candidates, including dates that finish immediately before the busy window and dates in lower-demand years. Screen expanded allowances such as 100, 180, 365 and 730 days. The two illustrative aircraft require a common allowance of at least 101 days to finish before 27 April.
4. Rebuild each selected aircraft's plan from the change point using maintenance clocks rather than the fixed check sequence. Keep all checks required before D starts. Replace only smaller checks actually covered by D; reset their clocks after completion. Generate every subsequently required check, including a later D if it enters the planning horizon.
5. Repair availability around the changed plans using priority-based small shifts. Also propose simultaneous changes to two or more aircraft: one-at-a-time improvement can miss a coordinated solution.
6. Keep final schedules meeting every protected-period requirement and all retained maintenance and operational rules. Among feasible results, compare early maintenance cost, surrounding worst-day availability, total downtime, displacement and smoothness.
7. If greedy selection stalls, let annealing accept temporarily worse outer changes and repair them. Always return the best feasible plan. Temperature cannot make a move outside the new permitted policy legal.

A practical alternative repair component is a CP-SAT model for the selected aircraft. Optional intervals can represent alternative checks, and no-overlap and cumulative constraints support the resulting scheduling problem. The aircraft-specific coverage and clock rules require explicit modelling; they are not provided automatically by a generic solver. Use the solver as a feasibility reference, not as evidence that an invented heuristic is novel.

## Evaluation

Compare the original fixed policy, expanded early allowance with fixed checks, expanded allowance plus check replacement with priority search, and the same plan-changing neighbourhood with annealing acceptance. Hold the new policy, objectives, initial aircraft maintenance state and computational budget fixed between the last two methods. Use multiple seeds and record any unknown feasibility outcome caused by time limits.

Measure whether both busy windows reach 20, how many D checks move, maximum and total early advance, smaller checks replaced, actual total downtime, maintenance cost assumptions, surrounding minima, runtime and any breaches. Do not assume mean availability stays constant: replacement can change check counts and downtime. Prevent horizon effects by checking the final aircraft clock state and later maintenance obligations, or extending the evaluation horizon consistently.

## Open modelling details

The user approved researching early D replacement and requested a separate algorithm file. Parameters for real operational use still to choose include maximum early advance, whether and how early maintenance loses useful interval, planning horizon and capacity assumptions. Existing optimiser files have not been modified.

## Implementation update

`savn_early_d_planning.py` now implements the proposed dynamic check selection, larger D moves, smaller-check rebuilding, paired D moves, priority search and optional annealing. Its configurable default D allowance is 730 days. It reuses the original rule definitions, initial clocks, input loader and acceptance rule without importing plotting dependencies.

Four initial 60-second trials all found plans with availability at least 20 in both existing busy windows. Independent replay of serialized schedules checked the initial state against the workbook, all maintenance clocks and durations, dependency groups, day-by-day availability and obligations through the end of the horizon. Availability outside the protected periods fell to 15 or 16. One annealing witness uses no D more than 130 days early. The 70-day start allowance and original as-loaded displacement limits are not claimed to hold in this new policy. See README.md and results-early730-comparison.json for settings, limitations and recorded results.

## Sources

- vn_priority_based_selection.py: fixed sequence, early allowance and due resets.
- calendar-options.json: independently calculated dates for the two illustrative D advances.
- https://github.com/google/or-tools/blob/stable/ortools/sat/docs/scheduling.md: official optional-interval, no-overlap and cumulative scheduling constructs.
