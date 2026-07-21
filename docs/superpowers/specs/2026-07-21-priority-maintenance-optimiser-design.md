# Priority-Based, Rule-Aware Maintenance Optimiser

## Goal

Reduce optimisation time while producing a final fleet schedule that follows the A/B/C/D maintenance rules, remains inside the fixed forecast horizon, and contains no overlapping events for any aircraft.

## Search strategy

The optimiser will replace random neighbour sampling with deterministic priority selection:

1. Compute fleet availability once over a fixed forecast horizon.
2. Find the timeline regions with the lowest availability.
3. Prioritise maintenance events that overlap those regions.
4. Try the existing coarse-to-fine shifts in both directions.
5. If no move improves the score, progressively include events from the next-lowest availability levels.
6. Use a deterministic full-event sweep as the final fallback.

This keeps the search aligned with the lexicographic objective: maximise minimum availability first, then minimise standard deviation, then maximise average availability.

## Rule-aware downstream rebuilding

A candidate move will not leave later maintenance windows fixed. The optimiser will replay the affected aircraft's maintenance cycle from the changed event onward:

- A is due after the configured A interval following the last A/B/C/D completion.
- B is due after the configured B interval following the last B/C/D completion.
- C is due after the configured C interval following the last C/D completion.
- D is due after the configured D interval following the last D completion.
- Larger checks reset the applicable smaller checks.
- When multiple checks are legally available, the highest-level check is selected, matching `generate_extended_dataset.py`.
- Existing downstream starts are retained as preferences where possible and clamped into their newly calculated legal windows.
- If the regenerated check sequence differs, the deterministic legal start closest to the previous downstream timing is used.

Only the affected aircraft is rebuilt for a candidate. Other aircraft remain unchanged.

## Non-overlap guarantee

Non-overlap is a hard invariant:

- Every rebuilt event must start no earlier than the affected aircraft's previous event end.
- Candidates that cannot satisfy both the due window and aircraft availability are rejected.
- Candidate schedules receive a per-aircraft chronological overlap check.
- The final schedule receives a complete feasibility check before it is returned or exported.
- Maintenance intervals use half-open semantics: `[start, start + duration)`. An event may start exactly when the previous event ends.

## Performance design

The optimiser will avoid deep-copying and validating the complete fleet for every proposed move:

- Compute the current availability array once.
- Remove the affected aircraft's old intervals and add its rebuilt intervals to a temporary availability array.
- Score that array directly over the fixed horizon.
- Copy or replace schedule data only after accepting the winning move.
- Validate only the affected aircraft during candidate generation.
- Perform one complete validation on the accepted final result.

This removes random sampling and avoids repeated full-schedule feasibility checks.

## Forecast horizon and scoring

All current and candidate schedules are scored over the same horizon. The horizon will be derived once from the loaded schedule's latest allowed start plus its duration. Events extending beyond that horizon are rejected. This prevents shifts of the final event from changing the length of the availability array and makes scores directly comparable.

## Failure handling

- An empty schedule or invalid event data raises a clear `ValueError`.
- An initial overlapping or out-of-window schedule is rejected before optimisation.
- A candidate that cannot produce a valid downstream schedule is skipped.
- If no improving candidate exists, the optimiser returns the best valid schedule found.
- Final validation failure raises an error and prevents export.

## Testing

Automated tests will cover:

- Fixed-horizon availability and comparable scoring.
- Selection of events overlapping minimum-availability regions.
- Expansion to broader availability levels.
- A/B/C/D due-date propagation after an accepted move.
- Larger checks replacing smaller checks.
- Legal-window enforcement.
- Rejection of overlapping events.
- Acceptance of adjacent, non-overlapping events.
- Deterministic candidate selection.
- Final full-schedule feasibility.

The implementation will preserve the existing script entry point, history output, plotting, and Excel export behaviour.
