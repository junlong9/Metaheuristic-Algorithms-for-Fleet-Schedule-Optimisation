# Priority Maintenance Optimiser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace random full-schedule neighbour evaluation with deterministic, priority-based candidate selection while preserving all maintenance rules and preventing overlap.

**Architecture:** Keep `vn_priority_based_selection.py` as a single script with its current loading, availability, evaluation, feasibility, neighbour-generation, optimiser, and main sections. Add focused helpers inside those sections for fixed-horizon scoring, rule replay, affected-aircraft availability replacement, and timeline-priority selection.

**Tech Stack:** Python 3, NumPy, pandas, unittest.

## Global Constraints

- Preserve the existing script structure and `main()` export/plot flow.
- Use a fixed scoring horizon for every candidate.
- Reapply A/B/C/D reset, interval, duration, and early-start rules downstream.
- Reject every candidate and final schedule containing overlapping events.
- Candidate selection must be deterministic; do not randomly sample neighbours.

---

### Task 1: Fixed-horizon scoring and overlap validation

**Files:**
- Modify: `vn_priority_based_selection.py:72-179`
- Create: `test_vn_priority_based_selection.py`

**Interfaces:**
- Produces: `get_forecast_horizon(schedule) -> int`
- Produces: `compute_availability(schedule, horizon=None) -> numpy.ndarray`
- Produces: `score_availability(availability) -> tuple`
- Produces: `is_aircraft_feasible(events, horizon=None) -> bool`

- [ ] **Step 1: Write failing tests**

```python
def test_fixed_horizon_keeps_candidate_scores_comparable(self):
    horizon = optimiser.get_forecast_horizon(self.schedule)
    self.assertEqual(
        len(optimiser.compute_availability(self.schedule, horizon)),
        len(optimiser.compute_availability(self.shifted_schedule, horizon)),
    )

def test_adjacent_events_are_valid_but_overlapping_events_are_not(self):
    self.assertTrue(optimiser.is_aircraft_feasible(self.adjacent))
    self.assertFalse(optimiser.is_aircraft_feasible(self.overlapping))
```

- [ ] **Step 2: Run tests and verify missing fixed-horizon APIs fail**

Run: `python -m unittest test_vn_priority_based_selection.py -v`
Expected: FAIL because the new helper APIs or parameters do not exist.

- [ ] **Step 3: Implement fixed-horizon availability and local feasibility**

```python
def get_forecast_horizon(schedule):
    return max(event["latest_start"] + event["duration"]
               for events in schedule.values() for event in events)

def score_availability(availability):
    return (np.min(availability), -np.std(availability), np.mean(availability))
```

Update `compute_availability` to allocate exactly `horizon + 1` days and reject events outside it. Add a sorted, half-open interval feasibility check that permits `current_end == next_start`.

- [ ] **Step 4: Run tests and verify Task 1 passes**

Run: `python -m unittest test_vn_priority_based_selection.py -v`
Expected: Task 1 tests PASS.

### Task 2: Rule-aware aircraft rebuilding

**Files:**
- Modify: `vn_priority_based_selection.py:140-226`
- Modify: `test_vn_priority_based_selection.py`

**Interfaces:**
- Produces: `CHECK_RULES: dict`
- Produces: `rebuild_aircraft_schedule(events, event_index, new_start, horizon) -> list | None`
- Consumes: `is_aircraft_feasible(events, horizon)`

- [ ] **Step 1: Write failing propagation tests**

```python
def test_rebuild_propagates_due_dates_and_prevents_overlap(self):
    rebuilt = optimiser.rebuild_aircraft_schedule(events, 0, 10, 3000)
    self.assertTrue(optimiser.is_aircraft_feasible(rebuilt, 3000))
    self.assertGreaterEqual(rebuilt[1]["earliest_start"], rebuilt[0]["start"])

def test_rebuild_uses_larger_check_when_it_legally_replaces_smaller_check(self):
    rebuilt = optimiser.rebuild_aircraft_schedule(events, 0, 10, 5000)
    self.assertIn("D", [event["check"] for event in rebuilt])
```

- [ ] **Step 2: Run tests and verify rule replay is missing**

Run: `python -m unittest test_vn_priority_based_selection.py -v`
Expected: FAIL because `rebuild_aircraft_schedule` does not exist.

- [ ] **Step 3: Implement deterministic rule replay**

```python
CHECK_RULES = {
    "A": {"duration": 14, "interval": 365, "early": 42, "priority": 1},
    "B": {"duration": 28, "interval": 730, "early": 70, "priority": 2},
    "C": {"duration": 84, "interval": 1460, "early": 70, "priority": 3},
    "D": {"duration": 126, "interval": 2920, "early": 70, "priority": 4},
}
```

Replay due-date state from the aircraft's first cycle anchor. Apply the requested start at `event_index`; afterward, use old starts as deterministic preferences, clamped to the legal range. Select the highest-priority legally available check and update all due dates reset by that check. Return `None` if the requested move or rebuilt result is illegal.

- [ ] **Step 4: Run tests and verify Task 2 passes**

Run: `python -m unittest test_vn_priority_based_selection.py -v`
Expected: Task 1 and Task 2 tests PASS.

### Task 3: Priority candidate search and optimiser integration

**Files:**
- Modify: `vn_priority_based_selection.py:182-321`
- Modify: `test_vn_priority_based_selection.py`

**Interfaces:**
- Produces: `prioritise_events(schedule, availability) -> list[tuple[str, int]]`
- Produces: `availability_with_rebuilt_aircraft(availability, old_events, new_events) -> numpy.ndarray`
- Updates: `generate_neighbors(schedule, availability, horizon, shifts) -> list[dict]`
- Updates: `savn_optimise(initial_schedule, max_iters=400) -> tuple`

- [ ] **Step 1: Write failing priority tests**

```python
def test_priority_order_starts_with_events_covering_global_minimum(self):
    availability = optimiser.compute_availability(schedule, horizon)
    ordered = optimiser.prioritise_events(schedule, availability)
    first_aircraft, first_index = ordered[0]
    event = schedule[first_aircraft][first_index]
    minimum_days = set(np.flatnonzero(availability == availability.min()))
    self.assertTrue(minimum_days.intersection(
        range(event["start"], event["start"] + event["duration"])
    ))

def test_neighbor_generation_is_deterministic_and_overlap_free(self):
    first = optimiser.generate_neighbors(schedule, availability, horizon, (-28, 28))
    second = optimiser.generate_neighbors(schedule, availability, horizon, (-28, 28))
    self.assertEqual(self.move_keys(first), self.move_keys(second))
    self.assertTrue(all(optimiser.is_feasible(n["schedule"], horizon) for n in first))
```

- [ ] **Step 2: Run tests and verify priority APIs fail**

Run: `python -m unittest test_vn_priority_based_selection.py -v`
Expected: FAIL because priority ordering and the updated neighbour API do not exist.

- [ ] **Step 3: Implement deterministic priority search**

Order events by the minimum availability across their active interval, then by start, aircraft, and index. Generate rule-aware candidates in that order, score by replacing only the affected aircraft's availability contribution, and retain candidate metadata without copying the complete schedule. Expand through all priority levels deterministically.

- [ ] **Step 4: Integrate optimiser acceptance and final validation**

Compute the horizon and availability once. For each shift set, choose the maximum precomputed candidate score, replace only the winning aircraft events, and update availability. Before returning, require `is_feasible(best, horizon)` or raise `RuntimeError`.

- [ ] **Step 5: Run full verification**

Run: `python -m unittest test_vn_priority_based_selection.py -v`
Expected: all tests PASS.

Run: `python -m py_compile vn_priority_based_selection.py test_vn_priority_based_selection.py`
Expected: exit code 0.
