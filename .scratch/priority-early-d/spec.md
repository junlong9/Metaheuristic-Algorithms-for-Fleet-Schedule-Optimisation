# Priority-based selection with earlier D checks

Status: ready-for-human

The user requested a duplicate of the current priority-based selection approach
to explore D checks before 2030, determine which existing rules this changes,
and measure whether schedule quality improves.

The new file is `vn_priority_based_selection_early_d.py`. The original
`vn_priority_based_selection.py` and existing early-D planner remain unchanged.
The copy retains worst-day availability, smoothness, then mean availability as
its lexicographic objective, deterministic priority buckets, improving-only
acceptance and the default coarse-to-fine neighbourhoods.

Dynamic maintenance-clock rebuilding reuses `savn_early_d_planning.py` and allows
first D placement to replace smaller checks only when their deadlines are
covered. Later D checks and every required check through the common forecast
horizon must be generated. Full durations are retained when crossing its end.

Default D allowance is 70 days. An enlarged allowance requires an explicit
experimental flag; the comparison uses 1,825 days (5 × 365). This relaxes the D
start window, and the original as-loaded displacement limit does not apply to
the changed check sequence. ABC allowances, durations, initial due clocks,
latest-start deadlines, reset intervals and non-overlap remain mandatory.

Like the original standalone priority file, this copy does not enforce the
separate operational-constraint scenarios. The comparison independently audits
the loose dependency groups and reports both busy-period minima. Such metrics
must not be described as a fully operationally compliant solution unless the
relevant requirements actually pass.

Compare baseline, dynamic 70-day policy, optional expanded early D, and all first
D checks before 1 January 2030 using the same input, horizon and iteration cap.
Report differences in start schedule and check counts, runtime, convergence,
total downtime, first D dates, additional D checks and operational audits.
The copy searches first D placements only; later D checks are rebuilt at due
dates. A failed or locally optimal search is not proof of global infeasibility.

## Verification note

The six new-copy tests and nine unchanged baseline tests pass. The existing
`test_savn_early_d_planning.py::test_too_long_C_falls_back_to_covering_B` fails
independently of this copy: it builds using the default 70-day D allowance and
validates metadata using 730 days. The existing planner and its test are left
unchanged.
