# VN hyperparameter analysis design

## Goal

Create a small, reproducible hyperparameter analysis of
`vn_priority_based_selection.py` for the university project team and assessors.
The study will compare four shift-set strategies and three iteration budgets on
the original, moderate-stagger, and wide-stagger datasets. It will produce raw
results, a concise summary, three readable charts, and a natural-sounding Word
report of approximately ten pages.

The production optimiser and all input workbooks remain unchanged. The search
is deterministic, so each of the 36 configurations is run once. Runtime is one
wall-clock observation, not a statistical sample.

## Verified repository facts

- The datasets are:
  - `heavy_maintenance_forecast.xlsx`
  - `outputs/initial-stagger/heavy_maintenance_forecast_stagger_moderate.xlsx`
  - `outputs/initial-stagger/heavy_maintenance_forecast_stagger_wide.xlsx`
- The common reporting window is 21 January 2026 through 18 January 2038,
  inclusive, as recorded in
  `.scratch/initial-maintenance-stagger/schedule-data.json`.
- The stagger datasets require the saved opening sequence positions and due
  clocks from that JSON file. Loading only the workbooks would reconstruct the
  wrong maintenance state.
- `score_availability` uses the lexicographic score
  `(minimum availability, -population standard deviation, mean availability)`.
- The earlier tuned study baseline in `savn_iteration2.py` ends with
  `(-3, -1, 1, 3)`. The shorter `(-3, 3)` representation is not equivalent.
- The current live ladder in `vn_priority_based_selection.py` has seven
  symmetric levels from ±56 days down to ±1 day and defaults to
  `max_iters=400`.

## Experiment matrix

Selection remains fixed to the production policy: inspect priority levels in
order, stop at the first level containing improving candidates, and accept its
best lexicographic candidate. Only the ordered shift sets and `max_iters`
change.

| Strategy key | Display name | Ordered shift sets, in days |
| --- | --- | --- |
| `historical_half_step` | Earlier tuned baseline | `(-28,-14,14,28)`, `(-14,-7,7,14)`, `(-7,-3,3,7)`, `(-3,-1,1,3)` |
| `live_wide_to_fine` | Current live ladder | `(-56,56)`, `(-42,42)`, `(-28,28)`, `(-14,14)`, `(-7,7)`, `(-3,3)`, `(-1,1)` |
| `dense_pairs` | Dense paired ladder | `(-28,28)`, `(-21,21)`, `(-14,14)`, `(-7,7)`, `(-3,3)`, `(-1,1)` |
| `half_step_plus_42` | Earlier tuned baseline plus ±42 | `(-42,42)`, `(-28,-14,14,28)`, `(-14,-7,7,14)`, `(-7,-3,3,7)`, `(-3,-1,1,3)` |

The budgets are exactly `200`, `400`, and `800`. They represent a shorter run,
the live default, and a convergence check used in existing studies. Crossing
four strategies, three budgets, and three datasets produces exactly 36 trials.
No selection-policy variants, random seeds, or repeated quality runs are in
scope.

## Architecture and data flow

Implementation will add one analysis program:

`analysis/vn_hyperparameter_analysis.py`

It will contain small functions for configuration, dataset loading, one search
run, metric collection, validation, output writing, charting, and Word report
generation. It will import the production module and reuse its workbook loader,
maintenance rebuild, availability update, scoring, and rule validator. A short
study loop will mirror the production control flow while accepting injected
shift sets and an iteration budget; production source will not be edited.

The program will:

1. Load all three schedules and align their day indexes to one common date
   origin.
2. Attach the saved opening clocks and sequence positions to the moderate and
   wide schedules.
3. Use the common reporting window for priority levels, accepted scores, and
   reported metrics while retaining crossing checks in the full model horizon.
4. Iterate datasets, strategies, and budgets in the table order above. Each
   trial starts from a fresh deep copy of its dataset.
5. Validate the final schedule, independently rebuild daily availability from
   aircraft occupancy masks, and collect one trial record.
6. Rank results, write JSON and CSV, render charts with a headless backend, and
   build the Word report from the same in-memory result records.

This is a descriptive benchmark. It does not write optimised workbooks or feed
the winning settings back into `vn_priority_based_selection.py`.

## Metrics and ranking

Every trial records:

- dataset, strategy key and display name, ordered shifts, and `max_iters`;
- minimum, population standard deviation, and mean availability over the common
  reporting window;
- the exact lexicographic score `[minimum, -std, mean]`;
- accepted moves, outer-loop passes entered, the accepted-score trace,
  natural-exhaustion status, and stop reason (`local_exhaustion` or
  `iteration_cap`);
- elapsed search seconds measured with `time.perf_counter`;
- maintenance-rule compliance; and
- an endpoint SHA-256 over canonical JSON containing each aircraft's ordered
  check, start, duration, earliest start, and latest start.

One move can be accepted per outer-loop pass. A pass that finds no improving
move is counted and stops with `local_exhaustion`; otherwise reaching
`max_iters` stops with `iteration_cap`. Runtime covers only the search call and
excludes dataset loading, validation, charting, and report generation.

Rule compliance means full maintenance replay through
`is_rule_compliant_schedule`: legal start windows, no same-aircraft overlap,
the check sequence, and due-date resets. The saved loose, medium, and tight
operational scenarios are not enforced by this optimiser and are therefore a
stated limitation, not silently labelled as passing.

Results are ranked separately within each dataset by the production
lexicographic score, highest first. Exact score ties receive the same
competition rank. The shared practical recommendation minimises the sum of its
three dataset ranks; ties are resolved by lower worst dataset rank, then lower
budget, lower total observed runtime, and finally strategy order in the matrix.
Runtime never outranks schedule quality.

## Outputs

All generated artifacts go in
`docs/reports/2026-10-20-vn-hyperparameter-analysis/`:

- `results.json` — metadata, source and input SHA-256 hashes, the complete
  matrix, all 36 trial records, and recommendation records;
- `summary.csv` — one flat row per trial with report-facing metrics and rank;
- `ranked-quality.png` — one horizontal standard-deviation dot plot per
  dataset, ordered by rank and labelled with each configuration's minimum
  availability, so unlike units do not share an axis;
- `budget-convergence.png` — accepted moves and exhaustion status by budget,
  with one line per strategy and one panel per dataset;
- `runtime.png` — one panel per dataset showing the single observed runtime for
  each strategy and budget; and
- `vn-hyperparameter-analysis.docx` — the final report.

Files are written to temporary siblings and renamed only after all trials and
validations succeed. Existing reports elsewhere in `docs/reports/` are never
overwritten.

## Word report

The report targets 9–11 pages in the repository's usual Calibri 11 style. It
uses short paragraphs, small tables, and the three charts rather than dumping
all raw rows. Its sections are:

1. purpose and executive recommendation;
2. method and datasets;
3. parameter choices, including the earlier baseline versus the live ladder;
4. original-dataset results;
5. moderate-stagger results;
6. wide-stagger results;
7. cross-dataset comparison;
8. runtime and convergence;
9. limitations; and
10. practical recommendation and reproduction command.

The writing will say “one observed run” where relevant. It will not use
averages, confidence language, significance claims, or invented repetitions.
Dataset differences will not be presented as optimiser gains.

## Dependencies and headless execution

The program uses the repository's existing Python stack plus `python-docx`:
NumPy, pandas, openpyxl, Matplotlib, and python-docx. If an import is missing,
it exits with a concise message containing:

`python -m pip install numpy pandas openpyxl matplotlib python-docx`

It selects Matplotlib's `Agg` backend before importing `pyplot`, calls no GUI
APIs, accepts no interactive input, and runs from the repository root with:

`python analysis/vn_hyperparameter_analysis.py`

## Error handling

The program exits nonzero with a dataset and configuration identifier when an
input is missing, a required worksheet or opening-state record is absent, a
schedule is initially invalid, a trial ends rule-invalid, independent
availability differs, or the matrix is incomplete. It does not catch and
continue after a failed trial. Final artifacts are published only after all 36
records validate, so partial output cannot look complete.

## Verification

The analysis program includes focused assertions for:

- exactly four unique strategies, three budgets, three datasets, and 36 unique
  trial keys;
- exact matrix values and fixed first-priority-level selection;
- common scoring dates and preserved stagger opening state;
- strictly improving accepted score traces;
- full endpoint rule replay;
- equality between incremental, full delta-array, and independent occupancy-mask
  availability;
- unchanged check counts, check types, durations, and commenced checks;
- JSON/CSV agreement and 36 CSV rows; and
- existence and nonzero size of all three charts and the Word report.

After a full run, open the DOCX and inspect every page for clipped tables,
unreadable labels, blank pages, chart legibility, natural wording, and a
roughly ten-page length. If LibreOffice is available, render it headlessly to
PDF and confirm 9–11 pages; otherwise record that page-count verification was
manual. Git verification must show no change to the production optimiser,
input workbooks, or any file outside the analysis program and generated output
directory.

## Acceptance criteria

- The production optimiser is unchanged.
- The implementation consists of one readable analysis Python file and the
  specified generated artifacts.
- The matrix is exactly 36 deterministic, single-run trials with no selection
  policy variation.
- The earlier tuned baseline and current live ladder are accurately and clearly
  distinguished.
- All trial endpoints pass maintenance-rule replay and independent availability
  verification.
- JSON and CSV contain every required metric, lexicographic score, and
  per-dataset rank.
- Charts are headless, labelled, and uncluttered.
- The approximately ten-page DOCX follows the required structure and avoids
  unsupported statistical claims.
- Failures are explicit and cannot leave a complete-looking partial report.
