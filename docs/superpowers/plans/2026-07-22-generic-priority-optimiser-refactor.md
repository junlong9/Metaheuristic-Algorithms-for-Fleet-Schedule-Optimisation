# Generic Priority Optimiser Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the priority optimiser and remove its fixed 12-year assumption without weakening propagation or overlap guarantees.

**Architecture:** Keep the existing single-script section structure. Replace forecast-boundary generation with exact supplied-slot replay using a repeating check sequence and one horizon derived from the input schedule.

**Tech Stack:** Python 3, NumPy, pandas, unittest.

## Global Constraints

- Process exactly the supplied event count.
- Use `A, B, A, C, A, B, A, D` as the repeating check sequence.
- Recalculate all downstream windows after a move.
- Preserve legal downstream starts and clamp illegal starts.
- Reject overlap and events outside the supplied horizon.
- Preserve deterministic priority search and existing export flow.

---

### Task 1: Specify generic-horizon behavior

**Files:**
- Modify: `test_vn_priority_based_selection.py`

**Interfaces:**
- Consumes: `get_forecast_horizon(schedule) -> int`
- Produces expected behavior for `savn_optimise` without a forecast constant.

- [ ] Add a test with a short schedule asserting the derived horizon equals its latest legal end and optimisation requires no fixed forecast duration.
- [ ] Add a test asserting rebuild returns exactly the supplied event count while following the repeating sequence.
- [ ] Run `python -m unittest test_vn_priority_based_selection.py -v` and verify the old fixed-boundary behavior fails.

### Task 2: Simplify rule replay

**Files:**
- Modify: `vn_priority_based_selection.py:19-442`
- Modify: `test_vn_priority_based_selection.py`

**Interfaces:**
- Add: `CHECK_SEQUENCE = ("A", "B", "A", "C", "A", "B", "A", "D")`
- Update: `rebuild_aircraft_schedule(events, horizon, event_index=None, new_start=None) -> list | None`
- Update: `is_rule_compliant_schedule(schedule, horizon) -> bool`

- [ ] Remove `FORECAST_DAYS`, `_next_check`, boundary normalization, `forecast_end`, and event-creation loops.
- [ ] Replay `range(len(events))`, choose `CHECK_SEQUENCE[position % len(CHECK_SEQUENCE)]`, update due dates, and retain/clamp downstream starts.
- [ ] Keep only legal-window, horizon, overlap, expected-sequence, and final-comparison checks.
- [ ] Run the unit tests and verify all replay and overlap tests pass.

### Task 3: Simplify search integration

**Files:**
- Modify: `vn_priority_based_selection.py:449-782`
- Modify: `test_vn_priority_based_selection.py`

**Interfaces:**
- Update: `generate_neighbors(schedule, availability, horizon, current_score, shifts) -> list[dict]`
- Preserve: `savn_optimise(initial_schedule, max_iters=400) -> tuple`

- [ ] Remove forecast-end parameters and duplicate horizon calculations.
- [ ] Compute the horizon once from the input schedule and use it for every candidate and export comparison.
- [ ] Consolidate repeated priority-level calculations without changing deterministic ordering.
- [ ] Run `python -m unittest test_vn_priority_based_selection.py -v`.
- [ ] Run `python -m py_compile vn_priority_based_selection.py test_vn_priority_based_selection.py`.
- [ ] Smoke-test two iterations against `heavy_maintenance_forecast.xlsx` and confirm final rule compliance.
