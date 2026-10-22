# Early D maintenance planning

The new standalone algorithm is `savn_early_d_planning.py` in the project root. It explores early D checks that reset the smaller maintenance clocks and can replace the smaller checks they cover. Existing optimiser files, workbooks and presentation files are preserved.

## Run it

From the project directory, using a Python environment with NumPy, pandas, openpyxl and XlsxWriter:

```powershell
python savn_early_d_planning.py --method priority --seconds 60
python savn_early_d_planning.py --method annealing --seed 1 --seconds 60
python savn_early_d_planning.py --compare --seconds 60
```

`--compare` runs priority once and annealing with seeds 1, 2 and 3, sequentially. Each trial gets its own runtime budget. The normal output is a new JSON file in this folder, with a full schedule, metrics, accepted-move history and terminal maintenance clocks for every trial. Use `--output` to choose another JSON path. Existing input files cannot be selected as output.

## Excel before/after output

Every CLI run also writes `optimised_early_d_maintenance_output.xlsx` in the
project directory, using the existing priority-based Excel exporter. It contains
`Original_MxEvents`, `Optimised_MxEvents`, `Original_Availability`,
`Optimised_Availability`, and `Summary`, including the before/after availability
chart. Original means the as-loaded input; optimised means the returned
best-so-far schedule. Summary values are actual full-horizon minimum, standard
deviation and mean availability, rather than the new search's internal score.

Use `--excel-output my_comparison.xlsx` to choose another path. `--compare`
creates separate workbooks with method/seed suffixes for its four trials.
Expanded D experiments have an experimental allowance suffix in their default
Excel filename. The supplied `optimised_heavy_maintenance_output.xlsx` is
protected from being selected as the new Excel output.

## Per-iteration print statements

Iteration output is enabled by default and follows the priority-based algorithm:
iteration number, current score, best neighbour score, aircraft/check move,
and `Improved.` The score displays named measures: busy-period shortfall,
total D days early, outside minimum, and standard deviation rounded to three
decimal places. A shortfall of zero means both busy-period requirements are met.
Each accepted step also shows the two busy-period minima. Annealing adds temperature
and identifies equal or worse accepted moves while showing the retained best score.

The full text trace is saved beside the JSON as `OUTPUT-stem-iterations.log`.
`--log PATH` chooses another log path. `--quiet` suppresses iteration output in
the console while retaining the log. Library calls to `optimise` are quiet by
default; use `verbose=True`, with optional `base_date` and `log_stream`.

The JSON history includes before/after checks for each changed aircraft, current
and best metrics, move descriptions and acceptance decisions. Rejected feasible
neighbours are counted; their complete schedules are not dumped. Invalid rebuilds
and dependency breaches are rejected before they become feasible neighbours.
A runtime-limited final neighbourhood is marked in the JSON history.
Printing and logging are included in the runtime budget.

```powershell
python savn_early_d_planning.py --method priority --seconds 60 --iterations 40 --output .scratch/early-d-planning/trace-priority.json
python savn_early_d_planning.py --method annealing --seed 3 --seconds 60 --iterations 40 --output .scratch/early-d-planning/trace-annealing-seed3.json
```

`trace-priority-iterations.log` and `trace-annealing-seed3-iterations.log`
contain the earlier, detailed print statements. New runs use the simplified
format. These runs do not replace the older
four-trial screening comparison.

The default windows come from the loose entry in `operational_constraints.json`; their minima are replaced with the `--minimum` setting, default 20. Both loose dependency groups remain mandatory. D defaults to the required 70-day early-start allowance. A larger allowance requires `--experimental-early-d` and does not satisfy the stated D start window. Saved 730-day results below are earlier policy experiments. `--iterations` changes the iteration cap and `--warm-iterations` changes the annealing warm-up, default eight iterations.

## What changes in the model

The opening A check and initial aircraft maintenance clocks remain fixed. ABC durations, intervals and early allowances remain unchanged. D retains its 126-day duration and latest-start deadline, while its early allowance becomes configurable. A D can occur before the old sequence reaches its D slot. It replaces only smaller checks it covers; a deadline before its start still requires an earlier covering check.

The old 70-day as-loaded displacement constraint is not applied to regenerated plans, where both the check sequence and count may change. This is an explicitly different research policy, not a solution under the old start windows. D checks may also move later than their loaded dates but never after their due dates.

The planner chooses an appropriate covering check from the clock state, using the loaded/current starts as preferences. It checks all pending deadlines, including smaller deadlines before a proposed D and higher deadlines during a smaller check. Consequently the rebuilt initial schedule can differ from the loaded fixed-sequence forecast. Each method begins from the same deterministic rebuild; its metrics are recorded separately under `initial_rebuilt`.

After a D finishes, all maintenance clocks reset. The planner generates every required check through the forecast, including a later D if an early first D brings it into the horizon. Checks crossing the final date are retained at full duration, with occupancy clipped only for within-horizon statistics. The terminal due clocks and full planned durations are exported for audit.

Every D check can take its own start inside its early window. Later D checks are not left on the due date produced by the clock reset. Rebuilding still follows maintenance clocks rather than the fixed A, B, A, C, A, B, A, D sequence. No hangar, crew, parts, flight-hour utilisation or monetary cost model is included.

## Search and reuse

The algorithm reuses the canonical check rules, initial due dates and workbook loader from `vn_priority_based_selection.py`, and the acceptance rule from `savn_priority_sa.py`. It loads those pure definitions directly from local source so optional legacy plotting packages are unnecessary. The original modules are not modified or monkey-patched.

Availability uses the existing delta-array and incremental aircraft remove/add approach, extended to support a changed number of checks and checks crossing the horizon. Worst affected busy-period dates receive priority. The search proposes larger D placements, busy-period boundaries, the tuned half-step repair moves, and coordinated D changes on two aircraft.

The search score is the priority simulated-annealing availability score: maximise the minimum number of available aircraft, then minimise the standard deviation, then maximise the mean. Busy-period shortfall and total D days early are still reported. They are not the acceptance score, so a D check can leave its due date when that raises availability.

The priority method accepts only improving scores. Annealing takes the same moves
and begins requesting exploratory moves with probability 0.25 after the first
eight iterations. If no improving neighbour exists, it can attempt an escape
even within those first eight iterations. Temperature begins at 5 and multiplies
by 0.99 per step. The existing acceptance function decides whether an equal or
worse score is accepted; the returned plan is always best-so-far.

Both reported periods must meet their required minimum for `target_met` to be true. An unsuccessful or timed-out search reports feasibility as unknown, not mathematically infeasible. Successful plans remain meaningful even when the runtime limit prevents convergence.

## Verification

```powershell
python -m unittest test_savn_early_d_planning -v
python .scratch/early-d-planning/run_tests.py
python .scratch/early-d-planning/validate_results.py
```

The full runner includes the new tests and the three existing computational suites. Its isolated legacy loader omits unavailable plotting imports, and the legacy export/plot entry-point test continues to mock its normal output functions.

The independent results audit does not use the algorithm's validator. It replays clocks from literal rules, constructs daily per-aircraft occupancy, checks both busy requirements and dependency groups, verifies terminal obligations and checks best-so-far against the complete accepted-move history. `serialized-validation.json` records hashes of the audited result and algorithm files.

## Saved evidence

The initial 60-second trials all achieved 20 in both windows. Independent replay
confirmed the dates, latest-start deadlines, dependency availability and complete
coverage through the forecast horizon.

| Method | April to May minimum | September to October minimum | Outside minimum | Largest D advance before its due date |
| --- | --- | --- | --- | --- |
| Priority | 20 | 20 | 15 | 222 days |
| Annealing seed 1 | 20 | 20 | 15 | 222 days |
| Annealing seed 2 | 20 | 20 | 16 | 222 days |
| Annealing seed 3 | 20 | 20 | 16 | 130 days |

The three annealing runs accepted 3, 3 and 6 worse moves respectively and still
returned their best plans. The seed-3 witness shows that this particular solution
does not need a D years early, despite the allowed two-year search range. This
does not establish that 130 days is the smallest allowance that can work.

These are screening results, not a reliable method ranking. Priority's timed
trial overlapped a computational test run during part of its first budget;
runtime-sensitive comparisons should be repeated under controlled conditions
before claiming an annealing advantage.

- `results-early730-comparison.json`: full current four-trial comparison.
- `serialized-validation.json`: independent audit of serialized output.
- `test-run.log`: stdout from the computational test runner; unittest summary is printed on stderr.
- `pilot-greedy-only.json`: earlier calibration, excluded from the current annealing comparison because its annealing trials had not reached any exploratory moves.
- `calendar-options.json`: the original illustrative early-D dates; not a full-fleet result.

Treat short runs as feasibility and implementation checks. They are not a definitive ranking of priority and annealing or proof of minimum required D allowance. In the new model, replacement and rebuilt future checks can change total downtime and mean availability, which are therefore recalculated for every result.
