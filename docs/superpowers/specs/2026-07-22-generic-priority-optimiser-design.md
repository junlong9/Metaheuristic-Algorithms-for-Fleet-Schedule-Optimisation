# Generic Priority Optimiser Simplification

## Goal

Make `savn_priority_based_selection.py` easier to read and usable with supplied schedules of any length, while preserving deterministic priority search, downstream date propagation, and non-overlap.

## Schedule model

- The optimiser processes exactly the maintenance slots supplied by the input schedule.
- Check types follow the repeating sequence `A, B, A, C, A, B, A, D`.
- A larger check occupies its sequence slot instead of adding separate smaller checks.
- Events before a selected move remain unchanged.
- The selected event moves exactly by the candidate shift.
- Every later event is recalculated from preceding completion dates.
- A later start remains unchanged when legal; otherwise it is clamped to the nearest legal date.

## Generic horizon

There is no fixed forecast duration. One comparison horizon is derived from the supplied schedule as the maximum `latest_start + duration`. Candidate schedules may not exceed that supplied horizon. The optimiser never creates maintenance slots beyond those provided.

## Simplification

Remove the 12-year constant, forecast-end arguments, boundary normalization, dynamic next-check selection, and duplicate defensive checks. Keep essential checks for allowed windows, horizon, overlap, expected sequence, and final rule compliance.

## Search and scoring

Keep deterministic priority selection based on the minimum fleet availability during each event. Evaluate all moves in the first priority level containing an improvement. Update availability by replacing only the affected aircraft contribution. Keep the lexicographic score of maximum minimum availability, minimum standard deviation, then maximum average availability.

## Validation

Reject candidates that violate a recalculated window, exceed the supplied horizon, or overlap. Replay each aircraft against the repeating sequence before returning the final schedule.

## Testing

Tests cover non-12-year horizons, fixed supplied event count, repeating sequence, downstream propagation, overlap rejection, deterministic priority ordering, and final rule compliance.
