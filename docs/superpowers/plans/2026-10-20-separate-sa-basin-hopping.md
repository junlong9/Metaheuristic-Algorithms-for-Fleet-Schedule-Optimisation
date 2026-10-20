# Separate SA and Basin Hopping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move basin-hopping, tabu, and greedy-polish behavior into `savn_basin_hopping.py` while keeping classic simulated annealing in `savn_priority_sa.py`.

**Architecture:** `savn_priority_sa.py` remains the owner of Metropolis acceptance, feasible priority proposals, continuous annealing, and its command-line entry point. `savn_basin_hopping.py` imports the shared acceptance and proposal functions and owns escape/polish orchestration; repository callers import the module matching the algorithm they use.

**Tech Stack:** Python 3, NumPy, `unittest`, `unittest.mock`

## Global Constraints

- Preserve all optimizer signatures and scheduling behavior.
- Do not re-export basin-hopping functions from `savn_priority_sa.py`.
- Preserve operational-constraint filtering in `generate_feasible_neighbors`.
- Do not alter maintenance rules, score ordering, or default hyperparameters.

---

### Task 1: Establish the basin-hopping module

**Files:**
- Create: `savn_basin_hopping.py`
- Modify: `savn_priority_sa.py:3-544`
- Create: `tests/test_savn_basin_hopping.py`
- Modify: `tests/test_savn_priority_sa.py`

**Interfaces:**
- Consumes: `savn_priority_sa.accept_candidate(...)` and `savn_priority_sa.generate_feasible_neighbors(...)`
- Produces: `select_escape_candidate`, `generate_vns_neighbors`, `start_vector`, `is_tabu_neighbor`, `greedy_polish`, and `basin_hopping_optimise` with their existing signatures

- [ ] **Step 1: Add a failing ownership test**

```python
import savn_basin_hopping as basin
import savn_priority_sa as annealing

def test_algorithm_functions_live_in_their_focused_modules():
    assert hasattr(basin, "basin_hopping_optimise")
    assert hasattr(basin, "greedy_polish")
    assert not hasattr(annealing, "basin_hopping_optimise")
    assert not hasattr(annealing, "greedy_polish")
```

- [ ] **Step 2: Run the ownership test**

Run: `python -m unittest tests.test_savn_basin_hopping -v`

Expected: FAIL because `savn_basin_hopping` does not exist.

- [ ] **Step 3: Move the implementation**

Move the basin-only functions and `DEFAULT_SHIFT_SETS` unchanged into
`savn_basin_hopping.py`. Import the two shared functions as module attributes so
tests and experimental monkey-patching remain explicit:

```python
import savn_priority_sa as annealing

# Calls use:
annealing.accept_candidate(...)
annealing.generate_feasible_neighbors(...)
```

Remove `time` and all basin-only definitions from `savn_priority_sa.py`.

- [ ] **Step 4: Split the existing tests**

Move escape-selection tests, `StartVectorTests`, `BasinHoppingTests`, and
`GreedyPolishTests` into `tests/test_savn_basin_hopping.py`. Keep acceptance,
feasible-neighbor, continuous-annealing, and `MainTests` in
`tests/test_savn_priority_sa.py`. Update patches to target the module that owns
each function.

- [ ] **Step 5: Run both focused suites**

Run:
`python -m unittest tests.test_savn_priority_sa tests.test_savn_basin_hopping -v`

Expected: PASS.

### Task 2: Update repository consumers

**Files:**
- Modify: `tests/test_savn_iteration2.py`
- Modify: `.scratch/iteration-2/run_study.py`
- Modify: `.scratch/busy-period-tradeoff/run_comparison.py`
- Modify: `.scratch/priority-sa-hybrid/chase_std_local.py`

**Interfaces:**
- Consumes: public functions from `savn_priority_sa` and `savn_basin_hopping`
- Produces: existing studies and tests with explicit algorithm ownership

- [ ] **Step 1: Update imports**

Use separate aliases where both modules are needed:

```python
import savn_priority_sa as annealing
import savn_basin_hopping as basin
```

Route `generate_feasible_neighbors` and `savn_optimise` through `annealing`.
Route `generate_vns_neighbors`, `greedy_polish`, and
`basin_hopping_optimise` through `basin`.

- [ ] **Step 2: Preserve experiment monkey-patching**

Where an experiment replaces proposal generation, patch the module used by
basin hopping:

```python
basin.annealing.generate_feasible_neighbors = proposals
```

- [ ] **Step 3: Run integration-focused tests**

Run:
`python -m unittest tests.test_savn_iteration2 tests.test_savn_priority_sa tests.test_savn_basin_hopping -v`

Expected: PASS.

- [ ] **Step 4: Run syntax and ownership checks**

Run:
`python -m py_compile savn_priority_sa.py savn_basin_hopping.py .scratch/iteration-2/run_study.py .scratch/busy-period-tradeoff/run_comparison.py .scratch/priority-sa-hybrid/chase_std_local.py`

Expected: exit code 0.

Run:
`rg "annealing\.(greedy_polish|basin_hopping_optimise|generate_vns_neighbors)" .scratch tests`

Expected: no stale basin-hopping calls through the simulated-annealing alias.
