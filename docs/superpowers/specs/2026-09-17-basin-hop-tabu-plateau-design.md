# Basin-hop tabu plateau design

## Goal

Raise worst-day fleet availability from 18 to 19 on the existing local `heavy_maintenance_forecast.xlsx`. If 19 is not found, keep simulated annealing only if it returns min 18 with a strictly better standard deviation than the current local best **1.405740**.

This change does not invent a new search. It changes how `basin_hopping_optimise` leaves an 18-opt and how `greedy_polish` is allowed to walk back.

## Success gate

Lexicographic score is unchanged: `(min, -std, avg)`.

| Outcome | Decision |
|---|---|
| Printed `score[0] >= 19` on the real workbook | Success. Keep the change. |
| Min 18 and std `< 1.405740` | Fallback keep. SA earned a smoother 18. |
| Min 18 and std `>= 1.405740` | This change did not earn its keep. |

Claim 19 only from a fresh printed score on `heavy_maintenance_forecast.xlsx`. Do not use cloud or regenerated-forecast numbers.

Reference scores on that workbook:

- Frozen hill-climb (`vn_priority_based_selection.py`): min 18, std 1.413971
- Local basin-hop 15 cycles × 8 moves, T=1.5, seed 99: min 18, std 1.405740 in 95.9s

## Problem

Every local hop still does 18 → 17 (sometimes 16) → polish back to 18. Three causes:

1. The next cycle starts from the last polished schedule, not the protected best-so-far.
2. Eight Metropolis moves are not a long enough walk after the forced floor drop.
3. Improve-only polish can reverse the exact first-escape move and reopen the same 18-opt.

## Locked decisions

- New behaviour lives only in `savn_priority_sa.py`.
- Do not edit `vn_priority_based_selection.py`.
- Keep priority proposals, rule-aware rebuild, incremental availability, VNS shift sets `(-28,28), (-14,14), (-7,7), (-3,3)`, and staged Metropolis `accept_candidate`.
- Keep returning best-so-far. The returned score must not be worse than the warm-start.
- Polish and availability always use the original forecast horizon from `get_forecast_horizon`.
- Work locally on the existing workbook. Do not regenerate it. Do not run another cloud grid.
- Do not edit live `.pptx` files.

## Architecture

Each basin-hop cycle:

1. Copy the protected **best-so-far** (not the last polished local opt).
2. Snapshot `forbidden = start_vector(best)`.
3. Force one Metropolis move with `require_lower_minimum=True` (18→17). If none is accepted, skip the cycle.
4. Take `plateau_moves` further Metropolis steps with `require_lower_minimum=False` on the VNS-union neighbourhood.
5. `greedy_polish` the escaped schedule with `tabu_vectors=(forbidden,)`.
6. If the polished score is lexicographically better than best, replace best.

Default experiment knobs (not a new grid):

- `escape_cycles=15`
- `plateau_moves=30`
- `escape_temperature=1.5`
- `baseline_max_iters=400`
- `random_seed=99`

Replace `escape_moves` with `plateau_moves`. The first hop is exactly one required floor-drop. The walk after that is `plateau_moves` Metropolis steps. Update the `main` mock in `test_savn_priority_sa.py` that currently expects `escape_moves=3`.

## Components

All in `savn_priority_sa.py`.

### `start_vector(schedule)`

Returns a hashable, ordered tuple of `(aircraft, check, start)` for every event in the schedule. Aircraft order is sorted by name. Events on an aircraft stay in list order. This is the tabu key for a whole schedule.

### `is_tabu_neighbor(schedule, neighbor, forbidden_vector)`

Build the candidate schedule by replacing `neighbor["aircraft"]` with `neighbor["events"]`. Return true if `start_vector(candidate) == forbidden_vector`.

The forbidden object is the **pre-escape start vector**, not a single event’s old start. One polish move that restores the exact door we left is rejected. Other improving polish moves remain legal.

### `greedy_polish(initial_schedule, horizon, max_iters=400, tabu_vectors=())`

Same improve-only VNS polish as today. When ranking neighbours, skip any neighbour for which `is_tabu_neighbor` is true against any vector in `tabu_vectors`. Empty `tabu_vectors` must match today’s behaviour.

Still raise `ValueError` on an invalid initial schedule and `RuntimeError` on an invalid result. Still pass through the caller’s `horizon`.

### `basin_hopping_optimise`

Add `plateau_moves=30`. Cycle start state is `copy.deepcopy(best)`, not `local_schedule` from the previous polish.

Escape selection:

- Move 1: `select_escape_candidate(..., require_lower_minimum=True)`. `None` → skip cycle.
- Moves 2 .. `1 + plateau_moves`: `select_escape_candidate(..., require_lower_minimum=False)`. A rejected/empty move ends the plateau early; still polish whatever was accepted.

Warm-start polish (cycle 0) uses `tabu_vectors=()`. Escape polishes use the pre-escape vector.

`main()` should call this with the default experiment knobs above so `python savn_priority_sa.py` is the verification run.

## Data flow and errors

No new score, no new maintenance rules, no expanded horizon. Incremental availability updates stay as they are.

Invalid initial schedule: `ValueError`. Invalid best after search: `RuntimeError`. Same messages as today.

## Testing

TDD in `test_savn_priority_sa.py`. Existing acceptance, feasibility, horizon, warm-start-protection, and `main` tests stay green.

Required new tests:

1. After a polish that is worse than best, the next cycle’s starting schedule is the previous best, not the worse local opt.
2. First escape still only considers a lower minimum; plateau moves may accept same-min or worse via Metropolis (`select_escape_candidate` already covers the first-move filter; add a plateau-length / `require_lower_minimum=False` case if the optimiser path is not otherwise exercised).
3. `greedy_polish` with a tabu vector refuses the neighbour that restores that vector and still accepts a different improving neighbour.
4. `greedy_polish` with `tabu_vectors=()` matches current no-tabu behaviour.
5. Returned best is never worse than the warm-start (extend the existing protection test if the new cycle start changes the mock sequence).

Heavy-dataset 19 is **not** a unit test. After unit tests pass, run one timed local basin-hop on `heavy_maintenance_forecast.xlsx` with the knobs above.

Also run:

```text
python -m unittest test_savn_priority_sa test_vn_priority_based_selection -q
```

## Out of scope

- Editing `vn_priority_based_selection.py`
- Cloud agents, regenerated `generate_extended_dataset.py` forecasts, or committing the real workbook unless the user asks
- PowerPoint / live `.pptx` edits
- Changing A/B/C/D rules, overlap rules, or the lexicographic objective
- A new metaheuristic family; tabu means only “do not restore this start vector”
- Another hyperparameter grid
- Neighbourhood counting at the 18-opt (follow-up only if this change snaps back with no std gain)

## Parent context

Supersedes the hop/polish loop described in `.scratch/priority-sa-hybrid/spec.md` for basin-hopping only. Classic continuous `savn_optimise` annealing is unchanged.
