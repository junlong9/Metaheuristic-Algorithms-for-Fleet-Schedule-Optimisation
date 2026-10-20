# Iteration 1 Milestone Presentation Design

## Goal

Create a native, editable PowerPoint presentation that explains the evolution of the fleet-maintenance optimisation work across four implementation milestones. The deck must show both algorithmic progress and measured outcomes, with particular emphasis on runtime, minimum fleet availability, and availability standard deviation.

## Audience and format

- Audience: mixed University of Queensland and Northrop Grumman stakeholders.
- Speaking time: 10 minutes.
- Main deck: 9 slides.
- Supporting material: speaker notes and benchmark appendix.
- Output: a new `.pptx` file, generated through the local PowerPoint MCP server.
- Branding: neutral technical engineering style without organisation-specific logos or templates.

## Story structure

The presentation uses an evidence-led chronological milestone journey with a results-first preview:

1. **Title and outcome** — introduce the progression from exhaustive neighbourhood evaluation to practical priority selection.
2. **Problem and success measures** — explain fleet availability, runtime, minimum availability, standard deviation, and average availability.
3. **Algorithm evolution roadmap** — show the four milestones on one timeline.
4. **Milestone 1: simple fleet dataset** — explain the initial optimiser, feasibility checks, and lexicographic objective.
5. **Milestone 2: full neighbourhood search** — show complete candidate generation and the resulting scalability limitation.
6. **Milestone 3: 200 random samples** — show the reduction in candidate evaluations and the trade-off of non-deterministic selection.
7. **Milestone 4: priority-based selection** — explain worst-availability ranking, rule-aware downstream rebuilding, incremental availability updates, and deterministic selection.
8. **Measured comparison** — compare runtime and schedule quality, including minimum availability and standard deviation before and after optimisation.
9. **Lessons and next steps** — summarise technical learning, current limitations, and planned validation or sensitivity testing.

## Benchmark design

- Report the initial simple-dataset implementation separately because it used a smaller and less complex input.
- Benchmark the comparable heavy-dataset algorithms on the same input and machine.
- Run each comparable algorithm three times and report median wall-clock runtime.
- Use a fixed random seed for the 200-sample algorithm.
- Capture:
  - input dataset and event count;
  - runtime;
  - number of accepted iterations where available;
  - initial and final minimum availability;
  - initial and final availability standard deviation;
  - initial and final average availability;
  - validation result or failure reason.
- Apply a documented time limit to algorithms that do not finish in practical time. Report the timeout directly rather than estimating runtime.
- Keep raw benchmark results and conditions in the appendix.

## Visual design

- Use a light technical-blueprint style with navy and blue accents.
- Use 16:9 widescreen slides.
- Keep one principal message per slide.
- Use a left-to-right milestone timeline for algorithm evolution.
- Use simplified process diagrams on algorithm slides.
- Use runtime bars and compact before/after metric callouts on the comparison slide.
- Reuse the existing neighbourhood-search and priority-selection flowcharts where they remain legible.
- Clearly distinguish measured outcomes from design intentions and pending work.
- Use minimal, restrained transitions only when they improve sequencing.

## Speaker notes

Each main slide will contain concise speaking notes targeting approximately one minute. Notes will explain the intended takeaway, define technical terminology for a mixed audience, and state any comparison limitations.

## Appendix

The appendix will include:

- benchmark conditions and methodology;
- detailed benchmark values;
- full neighbourhood-search flowchart;
- full priority-based optimiser flowchart;
- maintenance-rule and feasibility checks;
- metric definitions and comparison caveats.

## Failure handling and evidence integrity

- Do not present missing runtime measurements as estimates.
- Mark timed-out algorithms explicitly.
- Do not directly compare simple-dataset runtime with heavy-dataset runtime without a dataset caveat.
- Exclude invalid schedules from quality comparisons and state the validation failure.
- Preserve source metrics at useful precision in the appendix while rounding slide callouts for readability.

## Validation

Before delivery:

- confirm the `.pptx` opens in desktop PowerPoint;
- confirm all text fits within slide bounds;
- verify charts and metric labels against benchmark data;
- verify speaker notes exist on all nine main slides;
- verify the appendix contains benchmark methodology and detailed values;
- run the PowerPoint MCP accessibility audit;
- inspect slide snapshots or rendered images for visual defects;
- save the final deck without leaving PowerPoint sessions or files locked.
