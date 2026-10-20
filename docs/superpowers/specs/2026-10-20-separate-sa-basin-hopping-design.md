# Separate simulated annealing from basin hopping

## Goal

Keep `savn_priority_sa.py` focused on the classic priority-based simulated
annealing algorithm while preserving the existing basin-hopping experiments in
a dedicated module.

## Module design

`savn_priority_sa.py` retains:

- `accept_candidate`
- `generate_feasible_neighbors`
- `savn_optimise`
- `main`

The new `savn_basin_hopping.py` owns:

- `select_escape_candidate`
- `DEFAULT_SHIFT_SETS`
- `generate_vns_neighbors`
- `start_vector`
- `is_tabu_neighbor`
- `greedy_polish`
- `basin_hopping_optimise`

The basin-hopping module imports `accept_candidate` and
`generate_feasible_neighbors` from the simulated-annealing module. The
simulated-annealing module does not import the basin-hopping module, avoiding a
circular dependency.

## Compatibility

Function parameters and behavior remain unchanged. Repository scripts that use
basin hopping or greedy polishing will import `savn_basin_hopping` explicitly.
No compatibility re-exports will remain in `savn_priority_sa.py`, so its
interface reflects only simulated annealing.

Operational-constraint support remains on `generate_feasible_neighbors` because
both simulated annealing and the basin-hopping module use that proposal
function.

## Tests

Simulated-annealing acceptance, proposal, optimiser, and entry-point tests
remain in `tests/test_savn_priority_sa.py`. Tabu, greedy-polish, and
basin-hopping tests move to `tests/test_savn_basin_hopping.py`.

Iteration 2 tests and research scripts will import the new basin-hopping module
where required. Focused tests must demonstrate that the refactor changes module
ownership without changing scheduling behavior.
