# Iteration 1 Milestone Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a native, editable PowerPoint milestone deck with repeatable algorithm benchmarks, nine main slides, an evidence appendix, and speaker notes.

**Architecture:** Add a small benchmarkability seam to the existing heavy optimiser, then run every milestone through one isolated benchmark harness that records comparable metrics in JSON. Use the local `user-ppt-mcp` PowerPoint MCP server to build, inspect, repair, and save the deck directly through desktop PowerPoint.

**Tech Stack:** Python 3.13, NumPy, pandas, unittest, JSON, Microsoft PowerPoint, PptMcp MCP server.

## Global Constraints

- Audience: mixed University of Queensland and Northrop Grumman stakeholders.
- Speaking time: 10 minutes.
- Main deck: exactly 9 slides, followed by appendix slides.
- Use a new native `.pptx`; do not modify `Iteration 1.pptx` or `Seminar.pptx`.
- Use 16:9 widescreen and a neutral light technical-blueprint style.
- Report the simple-dataset milestone separately from heavy-dataset comparisons.
- Run comparable algorithms three times and report median wall-clock runtime.
- Use random seed `42` for the 200-sample algorithm.
- Apply a 300-second timeout to each benchmark run.
- Never estimate missing runtime values; display a timeout explicitly.
- Validate all quality metrics against the generated benchmark JSON.
- Add speaker notes to all nine main slides.
- Do not create a git commit unless the user explicitly requests one.

## File structure

- Modify `savn_optimiser_heavy.py` only to expose deterministic sample selection for benchmarking while preserving the current default of 200 sampled neighbours.
- Create `test_savn_optimiser_heavy.py` for the new selection seam.
- Create `benchmark_milestones.py` as the isolated benchmark runner and JSON writer.
- Create `test_benchmark_milestones.py` for aggregation, timeout, and serialization behaviour.
- Create `benchmark_results.json` as the source of truth for presentation metrics.
- Create `Iteration 1 Milestone Presentation.pptx` through PowerPoint MCP.
- Create `presentation_preview/` through PowerPoint MCP image export for visual review.

---

### Task 1: Make full and sampled neighbourhood search benchmarkable

**Files:**
- Modify: `savn_optimiser_heavy.py:233-321`
- Create: `test_savn_optimiser_heavy.py`

**Interfaces:**
- Produces: `select_neighbors(neighbors: list, sample_size: int | None, rng: numpy.random.Generator) -> list`
- Updates: `savn_optimise(initial_schedule, max_iters=400, sample_size=200, random_seed=None) -> tuple`
- Preserves: calling `savn_optimise(schedule)` still uses at most 200 randomly selected neighbours.

- [ ] **Step 1: Write focused failing tests**

```python
import unittest
import numpy as np

import savn_optimiser_heavy as optimiser


class NeighborSelectionTests(unittest.TestCase):
    def test_none_sample_size_keeps_full_neighbourhood(self):
        neighbors = [{"id": index} for index in range(250)]
        selected = optimiser.select_neighbors(
            neighbors,
            sample_size=None,
            rng=np.random.default_rng(42),
        )
        self.assertEqual(neighbors, selected)

    def test_sample_size_limits_neighbours_reproducibly(self):
        neighbors = [{"id": index} for index in range(250)]
        first = optimiser.select_neighbors(
            neighbors,
            sample_size=200,
            rng=np.random.default_rng(42),
        )
        second = optimiser.select_neighbors(
            neighbors,
            sample_size=200,
            rng=np.random.default_rng(42),
        )
        self.assertEqual(200, len(first))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm the missing API fails**

Run:

```powershell
python -m unittest test_savn_optimiser_heavy.py -v
```

Expected: both tests error with `AttributeError: module 'savn_optimiser_heavy' has no attribute 'select_neighbors'`.

- [ ] **Step 3: Add the minimal selection helper**

Add before `savn_optimise`:

```python
def select_neighbors(neighbors, sample_size, rng):
    if sample_size is None or len(neighbors) <= sample_size:
        return neighbors

    selected_indices = rng.choice(
        len(neighbors),
        size=sample_size,
        replace=False,
    )
    return [neighbors[index] for index in selected_indices]
```

Change the optimiser signature and selection:

```python
def savn_optimise(
    initial_schedule,
    max_iters=400,
    sample_size=200,
    random_seed=None,
):
    rng = np.random.default_rng(random_seed)
    # existing initialisation remains unchanged
```

Replace the direct `np.random.choice` block with:

```python
neighbors = select_neighbors(neighbors, sample_size, rng)
```

- [ ] **Step 4: Verify the new seam and existing priority tests**

Run:

```powershell
python -m unittest test_savn_optimiser_heavy.py test_vn_priority_based_selection.py -v
python -m py_compile savn_optimiser_heavy.py test_savn_optimiser_heavy.py
```

Expected: all tests pass and compilation exits with code `0`.

---

### Task 2: Build the repeatable milestone benchmark harness

**Files:**
- Create: `benchmark_milestones.py`
- Create: `test_benchmark_milestones.py`
- Produce: `benchmark_results.json`

**Interfaces:**
- Produces: `metric_snapshot(availability: numpy.ndarray) -> dict[str, float]`
- Produces: `summarise_runs(name: str, dataset: str, runs: list[dict]) -> dict`
- Produces: `run_once(algorithm: str) -> dict`
- Produces CLI: `python benchmark_milestones.py --all --repeats 3 --timeout 300 --output benchmark_results.json`
- Consumes: `savn_optimiser.savn_optimise`
- Consumes: `savn_optimiser_heavy.savn_optimise(sample_size=None|200, random_seed=42)`
- Consumes: `vn_priority_based_selection.vn_optimise`

- [ ] **Step 1: Write aggregation and timeout tests**

```python
import unittest

from benchmark_milestones import summarise_runs


class BenchmarkSummaryTests(unittest.TestCase):
    def test_summary_uses_median_runtime_and_preserves_metrics(self):
        runs = [
            {"status": "ok", "runtime_seconds": 9.0, "final": {"minimum": 18}},
            {"status": "ok", "runtime_seconds": 3.0, "final": {"minimum": 18}},
            {"status": "ok", "runtime_seconds": 6.0, "final": {"minimum": 18}},
        ]
        summary = summarise_runs("priority", "heavy", runs)
        self.assertEqual(6.0, summary["median_runtime_seconds"])
        self.assertEqual(18, summary["final"]["minimum"])

    def test_summary_reports_timeout_without_runtime_estimate(self):
        runs = [
            {"status": "timeout", "timeout_seconds": 300},
            {"status": "timeout", "timeout_seconds": 300},
            {"status": "timeout", "timeout_seconds": 300},
        ]
        summary = summarise_runs("full_neighbourhood", "heavy", runs)
        self.assertEqual("timeout", summary["status"])
        self.assertNotIn("median_runtime_seconds", summary)
        self.assertEqual(300, summary["timeout_seconds"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm the module is missing**

Run:

```powershell
python -m unittest test_benchmark_milestones.py -v
```

Expected: import fails because `benchmark_milestones.py` does not exist.

- [ ] **Step 3: Implement metric collection and result aggregation**

Use this result schema:

```python
{
    "generated_at": "ISO-8601 timestamp",
    "environment": {
        "python": "version",
        "platform": "Windows version",
        "processor": "processor name",
    },
    "algorithms": [
        {
            "name": "priority_based",
            "dataset": "heavy_maintenance_forecast.xlsx",
            "status": "ok",
            "repeats": 3,
            "median_runtime_seconds": 12.345,
            "runs": [],
            "initial": {
                "minimum": 15,
                "standard_deviation": 1.956849,
                "average": 21.760979,
            },
            "final": {
                "minimum": 18,
                "standard_deviation": 1.443721,
                "average": 21.745685,
            },
            "iterations": 7,
            "valid": True,
        }
    ],
}
```

Implement:

```python
def metric_snapshot(availability):
    return {
        "minimum": int(np.min(availability)),
        "standard_deviation": float(np.std(availability)),
        "average": float(np.mean(availability)),
    }
```

Use `time.perf_counter()` around only the optimiser call. Suppress normal algorithm printing with `contextlib.redirect_stdout(io.StringIO())`. For the 200-sample milestone pass `sample_size=200, random_seed=42`; for full neighbourhood pass `sample_size=None`; for priority selection call its existing optimiser. Keep the simple fleet result in a separate dataset group.

- [ ] **Step 4: Add subprocess timeout isolation**

The parent process must invoke one child process per run:

```python
completed = subprocess.run(
    [sys.executable, __file__, "--run-one", algorithm],
    capture_output=True,
    text=True,
    timeout=timeout_seconds,
    check=False,
)
```

On `subprocess.TimeoutExpired`, record only:

```python
{
    "status": "timeout",
    "timeout_seconds": timeout_seconds,
}
```

Require the child to print exactly one JSON object to stdout and send diagnostic text to stderr.

- [ ] **Step 5: Run unit tests and compilation**

Run:

```powershell
python -m unittest test_benchmark_milestones.py -v
python -m py_compile benchmark_milestones.py test_benchmark_milestones.py
```

Expected: all tests pass and compilation exits with code `0`.

- [ ] **Step 6: Run fresh benchmarks**

Run:

```powershell
python benchmark_milestones.py --all --repeats 3 --timeout 300 --output benchmark_results.json
```

Expected:

- `benchmark_results.json` is created.
- Every algorithm has three run entries.
- Full neighbourhood either has a measured median or an explicit 300-second timeout.
- Random-200 results are reproducible across the three seeded runs.
- Priority output passes `is_rule_compliant_schedule`.

---

### Task 3: Validate benchmark evidence before presentation use

**Files:**
- Read: `benchmark_results.json`
- Read: `optimised_heavy_maintenance_output.xlsx`

**Interfaces:**
- Consumes: Task 2 result schema.
- Produces: approved metric values for PowerPoint slide 8 and appendix tables.

- [ ] **Step 1: Run all algorithm tests**

Run:

```powershell
python -m unittest test_savn_optimiser_heavy.py test_vn_priority_based_selection.py test_benchmark_milestones.py -v
```

Expected: all tests pass.

- [ ] **Step 2: Check benchmark invariants**

Verify programmatically:

```python
assert priority["valid"] is True
assert priority["final"]["minimum"] >= priority["initial"]["minimum"]
assert priority["final"]["standard_deviation"] <= priority["initial"]["standard_deviation"]
assert random_200["dataset"] == priority["dataset"]
assert full_neighbourhood["dataset"] == priority["dataset"]
assert simple["dataset"] != priority["dataset"]
```

If an assertion fails, stop and report the evidence problem instead of generating a misleading comparison.

- [ ] **Step 3: Reconcile existing exported metrics**

Read the `Summary` sheet from `optimised_heavy_maintenance_output.xlsx` and compare it with the fresh priority benchmark. Small floating-point differences are acceptable; different minimum availability or materially different standard deviation requires investigation before deck generation.

---

### Task 4: Build the native PowerPoint through MCP

**Files:**
- Create: `Iteration 1 Milestone Presentation.pptx`
- Read: `benchmark_results.json`
- Read: `Flowchart of Neighborhood Search.png`
- Read: `Priority Based Optimiser Flowchart.png`

**Interfaces:**
- Consumes: validated metrics from Task 3.
- Produces: PowerPoint MCP `session_id`.
- Produces: 9 main slides and appendix slides with notes.

- [ ] **Step 1: Confirm PowerPoint does not already lock the output**

Call `user-ppt-mcp.file` with:

```json
{"action":"list"}
```

If the output path already has a session, reuse it. Otherwise ensure the file is closed in desktop PowerPoint.

- [ ] **Step 2: Create and show the presentation**

Call:

```json
{
  "action": "create",
  "path": "C:\\Users\\davsk\\OneDrive\\The University of Queensland\\Northrop Grumman\\Iteration 1\\Iteration 1 Milestone Presentation.pptx",
  "show": true,
  "timeout_seconds": 300
}
```

Store the returned `session_id` and use it for every subsequent MCP call.

- [ ] **Step 3: Create the nine main blank slides**

For each slide, call `user-ppt-mcp.slide`:

```json
{"action":"create","session_id":"<session_id>","layout_name":"Blank","position":0}
```

Set slide names to `01 Opening`, `02 Measures`, `03 Roadmap`, `04 Simple Dataset`, `05 Full Neighbourhood`, `06 Random 200`, `07 Priority Selection`, `08 Comparison`, and `09 Lessons`.

- [ ] **Step 4: Apply the shared blueprint visual system**

Use `user-ppt-mcp.shape` and `user-ppt-mcp.text` with:

- slide size: 960×540 points;
- background: `#F4F7FA`;
- title colour: `#173A5E`;
- accent blue: `#2867A8`;
- pale blue panels: `#D9EDFF`;
- success green: `#19745A`;
- warning amber: `#D9901A`;
- failure/timeout red: `#B84A4A`;
- body text: Aptos, 18–22 pt;
- titles: Aptos Display, 28–34 pt;
- minimum outer margin: 42 pt.

Use `shape(add-textbox)` followed by `text(format)` for titles and labels. Use `shape(add-shape, auto_shape_type=23)` for rounded metric cards and timeline nodes.

- [ ] **Step 5: Populate the nine approved slide messages**

Use the exact story:

1. **From exhaustive search to practical priority selection**
2. **A better schedule protects the worst day first**
3. **Four implementations, each responding to a scaling problem**
4. **The simple dataset proved the optimisation objective**
5. **Full neighbourhood search improved quality but did not scale**
6. **Sampling 200 neighbours reduced work but added uncertainty**
7. **Priority selection searches the worst availability regions first**
8. **Measured speed and schedule-quality comparison**
9. **Iteration 1 converted a working idea into a practical optimiser**

Do not place more than five short bullets on any slide.

- [ ] **Step 6: Insert milestone diagrams and benchmark charts**

- Insert `Flowchart of Neighborhood Search.png` on slide 5 with `user-ppt-mcp.image`.
- Insert `Priority Based Optimiser Flowchart.png` on slide 7.
- On slide 8, create a clustered bar chart (`chart_type=72`) for measured runtimes. If full neighbourhood timed out, use a red timeout annotation instead of a fabricated bar.
- Add two metric cards using the fresh priority result:
  - minimum availability: initial → final;
  - standard deviation: initial → final.
- Add average availability as a smaller context metric because the objective is lexicographic.

- [ ] **Step 7: Add concise speaker notes**

Use `user-ppt-mcp.notes` with `action="set"` for slides 1–9. Each note block must contain:

- the slide takeaway;
- a 45–65 second speaking script;
- a transition sentence to the next slide;
- dataset caveats where relevant.

Keep appendix slides without a timed script.

- [ ] **Step 8: Add appendix slides**

Create blank slides for:

10. Benchmark methodology and environment.
11. Detailed benchmark values.
12. Full neighbourhood-search flowchart.
13. Full priority-selection flowchart.
14. Maintenance rules, feasibility checks, and comparison caveats.

Use a compact table or aligned metric cards. Never compare the simple-dataset runtime directly with heavy-dataset runtimes without the dataset label.

- [ ] **Step 9: Save without closing**

Call:

```json
{"action":"save","session_id":"<session_id>"}
```

Keep the session open for validation and repair.

---

### Task 5: Audit, render, repair, and deliver

**Files:**
- Modify: `Iteration 1 Milestone Presentation.pptx`
- Create: `presentation_preview/`
- Optionally create: `Iteration 1 Milestone Presentation.pdf`

**Interfaces:**
- Consumes: open PowerPoint MCP session from Task 4.
- Produces: validated `.pptx`, slide preview images, and final audit evidence.

- [ ] **Step 1: Verify structure and notes**

Call:

```json
{"action":"summary","session_id":"<session_id>"}
```

Expected: 14 slides.

Call `user-ppt-mcp.notes`:

```json
{"action":"read-all","session_id":"<session_id>"}
```

Expected: non-empty notes for slides 1–9.

- [ ] **Step 2: Run accessibility audit**

Call:

```json
{"action":"audit","session_id":"<session_id>"}
```

Fix empty titles, missing image alt text, and reading-order problems. Set descriptive alt text on both flowchart images and every chart.

- [ ] **Step 3: Export all slides for visual inspection**

Call `user-ppt-mcp.export`:

```json
{
  "action": "all-slides-to-images",
  "session_id": "<session_id>",
  "destination_directory": "C:\\Users\\davsk\\OneDrive\\The University of Queensland\\Northrop Grumman\\Iteration 1\\presentation_preview",
  "width": 1920,
  "height": 1080
}
```

Inspect every exported image for clipped text, overlap, illegible charts, inconsistent spacing, and weak contrast. Repair defects through MCP and re-export affected slides.

- [ ] **Step 4: Verify chart data against JSON**

Use `user-ppt-mcp.chart` with `action="read-data"` on every chart. Compare returned values exactly with `benchmark_results.json`. Correct any mismatch before saving.

- [ ] **Step 5: Save and close the final session**

Call:

```json
{"action":"close","session_id":"<session_id>","save":true}
```

Expected: PowerPoint releases the file lock and the `.pptx` remains at the target path.

- [ ] **Step 6: Final file-level verification**

Confirm:

- `Iteration 1 Milestone Presentation.pptx` exists and is non-empty;
- desktop PowerPoint can reopen it through `file(open)`;
- slide summary still reports 14 slides;
- notes still exist on slides 1–9;
- reopening and closing with `save=false` succeeds.
