# Priority + Simulated Annealing Hybrid

## Problem Statement

The current priority-based optimiser finds good maintenance schedules quickly by focusing on the worst availability days, rebuilding aircraft plans under A/B/C/D rules, and updating availability cheaply. But it only accepts improving moves and stops when nothing improves. That can leave the search stuck on a locally good plan when a temporary worse move would unlock a better worst-day availability. Iteration 2 needs a way to sometimes accept temporary worse moves without throwing away the smart search machinery that already works.

## Solution

Add a simulated-annealing acceptance layer on top of the existing priority-based proposal machinery. Keep focusing on worst-availability events, rule-aware rebuild, incremental availability updates, VNS shift sizes, and best-so-far tracking. Change neighbour generation so non-improving candidates can be proposed, and accept candidates with a temperature-dependent rule that cools over time. Keep today’s deterministic hill-climbing optimiser as the frozen baseline for comparison, with a clear keep-or-drop decision if annealing does not help.

## User Stories

1. As a fleet planner, I want the optimiser to sometimes accept a temporary worse schedule, so that it can escape local traps and find a better worst-day availability.
2. As a fleet planner, I want better moves to always be accepted, so that clear improvements are never rejected.
3. As a fleet planner, I want worse moves to become less likely over time, so that the search settles rather than wandering forever.
4. As a fleet planner, I want the search to always remember the best schedule seen, so that wandering during annealing does not lose the best result.
5. As a fleet planner, I want the returned schedule to obey maintenance rules and non-overlap, so that results remain operationally valid.
6. As a fleet planner, I want the optimiser to still focus on events that hit the worst availability days, so that search effort stays targeted.
7. As a fleet planner, I want aircraft plans to be rebuilt after a moved check, so that later A/B/C/D windows stay consistent.
8. As a fleet planner, I want availability to be updated without a full fleet recalculation for every trial, so that runtime stays practical.
9. As a fleet planner, I want larger timing shifts to be tried before smaller ones, so that the neighbourhood structure from Iteration 1 is preserved.
10. As a researcher, I want a deterministic hill-climbing baseline that still works unchanged, so that I can compare annealing fairly.
11. As a researcher, I want to run annealing with a fixed random seed, so that experiments are reproducible.
12. As a researcher, I want annealing parameters (starting temperature, cooling, iteration budget) to be configurable, so that I can study sensitivity later without rewriting the core.
13. As a researcher, I want the scoring order to still prefer worst-day availability first, then smoothness, then average, so that the operational objective does not change.
14. As a researcher, I want a fair scoring rule for temporary worse moves, so that annealing does not thrash secondary metrics while hurting the floor.
15. As a researcher, I want invalid or rule-breaking candidates to be rejected, so that annealing never accepts illegal schedules.
16. As a developer, I want neighbour generation to be able to return non-improving feasible candidates, so that annealing has something to accept or reject.
17. As a developer, I want the improve-only early-exit behaviour to be optional or disabled in annealing mode, so that the search is not trapped by hill-climb filtering.
18. As a developer, I want acceptance logic testable in isolation, so that temperature behaviour can be checked without a full heavy-dataset run.
19. As a developer, I want the optimiser entry point to remain the main integration surface, so that callers do not need a new pipeline.
20. As a developer, I want existing priority, rebuild, and feasibility tests to keep passing, so that Iteration 1 behaviour is not regressed.
21. As a developer, I want annealing mode to fail clearly on an invalid initial schedule, so that bad inputs are caught early.
22. As a developer, I want the final returned schedule to be validated before return, so that broken outputs cannot slip through.
23. As a stakeholder, I want a measurable comparison against the Iteration 1 baseline on the heavy forecast, so that we can decide whether annealing is worth keeping.
24. As a stakeholder, I want annealing abandoned if it does not match or beat baseline quality without large runtime regression, so that we do not keep complexity without benefit.
25. As a presenter, I want the design to match the Iteration 2 execution story (keep search, change acceptance), so that the implementation matches what was presented.

## Locked for this implementation

- New module only: `savn_priority_sa.py`. Do not change `vn_priority_based_selection.py`.
- Classic SA (option B): pick one feasible neighbour at random from the priority/VNS proposal set, then Metropolis-accept it.
- Staged acceptance: always accept a better minimum availability; always reject a worse minimum; if the minimum is unchanged, always accept a better secondary score and sometimes accept a bumpier plan with `P = exp(-Δstd / T)`.
- Return best-so-far. Seed, `initial_temperature`, and `cooling_rate` are constructor/entry arguments.

## Implementation Decisions

- Keep the existing priority-based proposal machinery: worst-availability event ordering, rule-aware aircraft rebuild, incremental availability updates, and VNS shift sets.
- Keep separate best-so-far tracking while the current solution may worsen under annealing.
- Preserve deterministic hill-climbing as the default/baseline path so Iteration 1 behaviour remains available.
- Add an annealing mode (or parallel entry) that:
  - proposes feasible candidates including non-improving ones from priority-focused events and shift sets;
  - always accepts improving candidates;
  - accepts non-improving candidates with a temperature-dependent probability that decreases as the search cools;
  - returns the best schedule seen, not merely the final current schedule.
- Remove or bypass the improve-only neighbour filter and “first improving priority level only” early-exit when in annealing mode.
- Define a fair scoring rule for temporary worse moves that protects the lexicographic objective (minimum availability first). Prefer a staged/hierarchical acceptance approach over a naive scalar that can thrash standard deviation while hurting the floor.
- Expose seedable randomness for annealing acceptance and any random candidate selection.
- Expose configurable temperature / cooling / iteration controls without hard-coding a single experimental setup into irreversible logic.
- Do not change the A/B/C/D maintenance rules, overlap rules, or fixed-horizon scoring definitions as part of this feature.
- Primary module surface remains the priority-based optimiser; avoid introducing a second parallel scheduling stack.

## Testing Decisions

- Good tests assert external behaviour: given an input schedule and mode settings, the optimiser returns a rule-valid schedule and a score that matches the lexicographic objective. Prefer not to assert private search bookkeeping.
- Primary seam under test: the optimiser entry point (baseline vs annealing mode).
- Optional thin seam: acceptance decision helper (current score, candidate score, temperature, RNG → accept/reject), used only to pin Metropolis/staged acceptance behaviour deterministically.
- Prior art: `test_vn_priority_based_selection.py` already covers fixed-horizon scoring, feasibility/overlap, rule-aware rebuild, priority ordering, and optimiser improvement behaviour — extend that style rather than inventing a new harness.
- Include regression checks that baseline hill-climb behaviour remains available and that annealing never returns a rule-invalid schedule.
- Prefer small constructed schedules for unit tests; heavy-dataset comparison can be a separate manual/benchmark step, not a required unit test.

## Out of Scope

- PowerPoint / presentation updates
- New operational or logistics constraints (busy-period windows, hangar capacity, crew/parts)
- Full hyperparameter sensitivity study and reporting
- Controlled initial-stagger experiment suite
- Exact/IP solvers or replacement of priority search with a different metaheuristic family
- UI, Excel export redesign, or visualisation changes beyond what is needed to run the optimiser

## Further Notes

- Seams confirmed with the user: optimiser entry point as primary; optional acceptance helper only if needed for deterministic acceptance tests.
- Iteration 2 research workstreams (constraints, settings study, stagger) remain future work after this hybrid exists and can be compared to the frozen baseline.
- Success gate from the execution plan: keep annealing only if it matches or beats baseline worst-day availability without a large runtime regression; otherwise retain deterministic priority VNS.
