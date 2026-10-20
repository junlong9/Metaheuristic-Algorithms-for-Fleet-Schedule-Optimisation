# Priority-based VNS hyperparameter study

## Question

Which settings of the deterministic priority / variable-neighbourhood
search in `vn_priority_based_selection.py` give the best lexicographic
score on the local `heavy_maintenance_forecast.xlsx` workbook?

## Objective

Higher is better, in this order:

1. Minimum availability
2. Negative standard deviation (smoother is better)
3. Mean availability

## Knobs under test

- `max_iters` — iteration cap; search also stops when a full VNS pass
  finds no improving neighbour.
- `shift_sets` — neighbourhood sizes and the order they are tried.
- Selection policy — current first-priority-level early exit versus
  best-across-all-levels and first-improving.

## Method

The production module stays unchanged. A quiet copy of the search loop
in `run_hyperparameter_study.py` imports the same scoring, rebuild, and
neighbour functions. The algorithm is deterministic, so each
configuration is run once. Every finished schedule is checked with
`is_rule_compliant_schedule`.

## Dataset

Local `heavy_maintenance_forecast.xlsx`, sheet `MxEvents`.
This is the workbook that already reaches minimum availability 18
under the published default settings.
