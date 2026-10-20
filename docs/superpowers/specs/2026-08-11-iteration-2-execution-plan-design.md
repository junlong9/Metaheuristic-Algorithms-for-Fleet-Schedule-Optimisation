# Iteration 2 Execution Plan Design

## Goal

Create a native, editable PowerPoint presentation that sets the Iteration 2 / Semester 2 execution plan for fleet-maintenance optimisation research. The deck must recap Iteration 1 outcomes briefly, deliver a researched Simulated Annealing (SA) + priority/VNS integration verdict, and justify four workstreams: SA hybrid design, operational constraints, hyperparameter analysis, and initial stagger experiments.

## Audience and format

- Audience: mixed University of Queensland and Northrop Grumman stakeholders.
- Speaking time: approximately 10 minutes.
- Main deck: exactly 10 slides.
- Supporting material: speaker notes (~1 minute per slide).
- Output: a new `.pptx` file at workspace root, `Iteration 2 Execution Plan.pptx`, generated through the local PowerPoint MCP server.
- Branding: neutral technical engineering style without organisation-specific logos or templates; match Iteration 1 Milestones visual language.

## Story structure

The presentation uses a hybrid structure: short Iteration 1 recap → SA integration deep-dive → one slide each for remaining future-work topics → timeline + success criteria.

1. **Title** — Iteration 2 Execution Plan: Priority search → validated research workstreams.
2. **Where Iteration 1 left us** — Priority VNS results (min availability 15→18, ~15.4 s); acceptance is strict hill-climbing.
3. **Iteration 2 overview** — four workstream cards: SA+VNS hybrid · Constraints · Hyperparameters · Initial stagger.
4. **SA integration analysis** — proposal vs acceptance layers; code-level conflicts; verdict that they compose as layers.
5. **Hybrid design + work plan** — Priority-SA+VNS design; energy/staged acceptance; experiment vs frozen baseline.
6. **Operational & logistics constraints** — current model under-constrained; availability-max windows + surrounding event moves + local std control.
7. **Hyperparameter analysis** — fixed `shift_sets`, `max_iters`, priority early-exit (+ SA knobs if added); sensitivity on heavy data.
8. **Initial stagger** — local search depends on start; controlled stagger variants to separate start effect from algorithm gain.
9. **Execution timeline** — freeze baseline → SA layer → energy rule → constraint prototypes → sensitivity → decision gate.
10. **Success criteria & risks** — measurable quality/runtime/constraint validity; abandon SA if no gain; staged acceptance if lex energy thrashing.

## Researched SA + priority integration verdict

Source: `vn_priority_based_selection.py`.

**Verdict:** Priority selection, rule rebuild, incremental availability, and VNS shift sets are compatible **proposal/evaluation** machinery for SA. The current optimiser is **hill-climbing at acceptance and filtering**, so SA is not a drop-in; it replaces the acceptance layer.

### Compatible keep (proposal / evaluation layer)

- `prioritise_events` / worst-availability buckets
- `rebuild_aircraft_schedule`
- `availability_with_rebuilt_aircraft`
- VNS `shift_sets`
- separate `best` / `best_score`

### Must change for SA (acceptance layer)

- Improvement-only filter (`candidate_score <= current_score: continue`)
- Early-exit that returns only improving neighbours at the first fruitful priority level
- Strict accept (`best_neighbor_score > current_score`) and stop-on-no-improve
- Lexicographic tuple score needs a defined scalar energy or staged Metropolis rule

### Recommended hybrid for the deck

**Priority-biased proposals + VNS neighbourhoods + SA acceptance + best-so-far**, with current deterministic priority VNS retained as baseline.

```text
Keep as proposal layer: Priority buckets → Rule rebuild → Incremental availability → VNS shift sets
Replace acceptance layer: Drop improve-only filter → Metropolis / staged accept → Track best-so-far
```

## Workstream design

### 1. SA + VNS hybrid

- Treat priority/VNS as proposal machinery; replace hill-climbing acceptance with SA.
- Define scalar energy or staged Metropolis for lexicographic `(min_avail, -std, avg)` scores.
- Freeze current priority VNS as baseline; run SA variants as experiments.

### 2. Operational & logistics constraints

- Current model maximises availability under maintenance rules but is under-constrained for operational realism.
- Prototype: availability-max windows, surrounding-event move limits, and local standard-deviation control.
- Validate constraint satisfaction separately from raw availability gains.

### 3. Hyperparameter analysis

- Document fixed knobs: `shift_sets`, `max_iters`, priority early-exit; add SA temperature/cooling if SA proceeds.
- Run sensitivity on heavy maintenance data.
- Report which knobs move quality vs runtime materially.

### 4. Initial stagger

- Local search quality depends on the starting schedule.
- Controlled stagger variants separate start-point effects from algorithm gains.
- Use same seed/protocol when comparing algorithms.

## Visual design

- Use a light technical-blueprint style with navy and blue accents.
- Use 16:9 widescreen slides.
- Keep one principal message per slide.
- Use overview cards on the Iteration 2 overview slide (four workstreams).
- Use a clear proposal-vs-acceptance layer diagram on the SA integration slide.
- Use a left-to-right timeline on the execution timeline slide.
- Clearly distinguish measured Iteration 1 outcomes from Iteration 2 design intentions and pending work.
- Use minimal, restrained transitions only when they improve sequencing.
- Reuse patterns from `others/build_milestone_presentation.py` and `Iteration 1 Milestones.pptx` (accent bar, section labels, cards, metric callouts).

## Speaker notes

Each of the ten main slides will contain concise speaking notes targeting approximately one minute. Notes will explain the intended takeaway, define technical terminology for a mixed audience, and state any comparison or research limitations.

## Evidence integrity

- Present Iteration 1 metrics as measured outcomes (min availability 15→18, ~15.4 s) and do not invent new benchmark numbers for Iteration 2 workstreams.
- Frame SA, constraints, hyperparameters, and stagger as planned research, not completed results.
- Keep the SA verdict grounded in the current code structure of `vn_priority_based_selection.py`.
- Distinguish “compatible as proposal layer” from “drop-in SA replacement.”

## Out of scope

- Implementing SA or new constraints in Python (presentation only).
- Modifying `Iteration 1 Milestones.pptx` content.
- Git commit unless explicitly requested.

## Validation

Before delivery:

- confirm the `.pptx` opens in desktop PowerPoint;
- confirm all text fits within slide bounds;
- verify speaker notes exist on all ten main slides;
- verify slide count is exactly 10;
- run the PowerPoint MCP accessibility audit where available;
- inspect slide snapshots or rendered images for visual defects;
- close the PowerPoint MCP session with save and without leaving files locked.
