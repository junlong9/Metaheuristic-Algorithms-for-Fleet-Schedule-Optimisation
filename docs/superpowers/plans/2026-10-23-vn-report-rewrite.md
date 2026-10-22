# VN Report Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current three-page VN report with a natural, self-contained two-page decision memo.

**Architecture:** Keep the study data and factual assertions in `.scratch/vn-step-size-study/build_report.py`, but replace the document content with a shorter five-section narrative. A focused test will verify the document structure, word count, and absence of historical framing before the builder regenerates the DOCX.

**Tech Stack:** Python 3, python-docx, pytest, Microsoft Word COM.

## Global Constraints

- Rewrite `vn-hyperparameter-analysis2.docx` in place.
- Target two A4 pages.
- Do not mention earlier studies, follow-up work, report dates, user recollection, cloud agents, or later adoption.
- Keep one compact best-results table and no charts.
- Keep the recommendation, baseline comparison, main step-size and order findings, 400-iteration rationale, and material limitations.
- Leave `summary2.xlsx` unchanged as the detailed record of all trials.

---

### Task 1: Add report-content regression coverage

**Files:**
- Create: `tests/test_vn_report.py`

**Interfaces:**
- Consumes: `build_report.load() -> dict` and `build_report.build(payload) -> docx.Document`
- Produces: regression checks for the concise document

- [ ] **Step 1: Add the focused test**

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".scratch" / "vn-step-size-study"
sys.path.insert(0, str(REPORT_DIR))
spec = spec_from_file_location("build_report", REPORT_DIR / "build_report.py")
assert spec and spec.loader
build_report = module_from_spec(spec)
spec.loader.exec_module(build_report)


def test_report_is_concise_and_self_contained():
    document = build_report.build(build_report.load())
    paragraph_text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    text = f"{paragraph_text}\n{table_text}"
    lowered = text.lower()

    assert 600 <= len(text.split()) <= 950
    assert len(document.tables) == 1
    assert len(document.inline_shapes) == 0
    assert [
        p.text for p in document.paragraphs if p.style.name == "Heading 1"
    ] == [
        "What we tested",
        "Best results",
        "What the results show",
        "Limits and next step",
    ]
    for phrase in (
        "first study",
        "previous study",
        "follow-up",
        "20 october",
        "user's recollection",
        "cloud",
        "adopted after",
    ):
        assert phrase not in lowered
```

- [ ] **Step 2: Run the test and confirm the current report fails**

Run:

```powershell
python -m pytest tests/test_vn_report.py -q
```

Expected: FAIL because the current document is longer than 950 words, has three tables and two images, and contains historical wording.

- [ ] **Step 3: Commit the failing test**

```powershell
git add tests/test_vn_report.py
git commit -m "test: define concise VN report structure"
```

### Task 2: Rewrite and regenerate the report

**Files:**
- Modify: `.scratch/vn-step-size-study/build_report.py`
- Modify: `docs/reports/2026-10-22-vn-step-size-study/vn-hyperparameter-analysis2.docx`

**Interfaces:**
- Consumes: the existing `load`, `trial`, `shared_table`, labels, datasets, and strategy definitions from `study_data.py`
- Produces: `build(payload: dict) -> Document` and the regenerated DOCX

- [ ] **Step 1: Simplify the builder**

Keep the existing styling, table helper, data access, and claim checks. Remove both chart functions and replace the report body with:

```python
def build(payload: dict) -> Document:
    labels = payload["labels"]
    shared = payload["recommendations"]["shared"]
    winners = payload["recommendations"]["dataset_winners"]
    rec_key, rec_budget = shared["strategy_key"], shared["max_iters"]
    check(
        (rec_key, rec_budget) == ("live_wide_to_fine", 400),
        "shared recommendation is wide-to-fine at 400",
    )

    rec = {d: trial(payload, d, rec_key, 400) for d in DATASETS}
    base = {d: trial(payload, d, "pairs_28", 400) for d in DATASETS}
    check(
        all(base[d]["min_availability"] == rec[d]["min_availability"] for d in DATASETS),
        "baseline and recommendation have equal minimum availability",
    )
    check(
        all(base[d]["availability_std"] > rec[d]["availability_std"] for d in DATASETS),
        "recommendation has lower variability than baseline",
    )
    sd_gap = {
        d: base[d]["availability_std"] - rec[d]["availability_std"]
        for d in DATASETS
    }

    document = Document()
    style_document(document)
    document.core_properties.title = "Variable-neighbourhood parameter analysis"
    document.core_properties.author = "UQ / Northrop Grumman fleet schedule project"
    document.add_heading("Variable-neighbourhood parameter analysis", level=0)

    document.add_paragraph(
        "Use the wide-to-fine shift ladder (±56, ±42, ±28, ±14, ±7, ±3 "
        "and ±1 days) with a 400-iteration limit. It gave the strongest "
        "overall result across the three forecasts and was best on the "
        "moderate and wide stagger forecasts. The baseline ladder (±28, ±14, "
        "±7, ±3 and ±1 days) reached the same minimum availability—18, 19 "
        "and 20 aircraft—but its day-to-day availability varied slightly "
        f"more. The difference in standard deviation was "
        f"{f4(min(sd_gap.values()))} to {f4(max(sd_gap.values()))} aircraft."
    )

    document.add_heading("What we tested", level=1)
    document.add_paragraph(
        "The analysis compared 13 ordered shift strategies on the original, "
        "moderate stagger and wide stagger forecasts. Each was tested at 200, "
        "400 and 800 iterations; the two slowest-converging strategies were "
        "also tested at 1600, giving 123 trials. A shift moves a candidate "
        "maintenance event earlier or later, and the optimiser accepts the "
        "best move that improves availability. Results were ranked by minimum "
        "available aircraft, then lower standard deviation, then higher "
        "average availability. Availability was measured from 21 January "
        "2026 to 18 January 2038. All schedules passed the implemented "
        "maintenance checks."
    )

    document.add_heading("Best results", level=1)
    rows = []
    for dataset in DATASETS:
        item = payload["by_key"][winners[dataset]]
        rows.append([
            DATASET_LABELS[dataset],
            labels[item["strategy_key"]],
            str(item["max_iters"]),
            str(item["min_availability"]),
            f4(item["availability_std"]),
            f4(item["mean_availability"]),
        ])
    add_table(
        document,
        ["Forecast", "Best strategy", "Iterations", "Minimum", "SD", "Average"],
        rows,
        [3.0, 6.0, 1.8, 1.7, 1.7, 2.0],
    )
    document.add_paragraph(
        "The forecasts begin from different maintenance states, so their "
        "availability levels should not be compared directly. The original "
        "forecast favoured the overlapping half-step ladder with ±42, while "
        "the wide-to-fine ladder was best on the two staggered forecasts. "
        "Using one shared setting avoids changing the optimiser between "
        "forecasts for a very small loss on the original forecast."
    )

    document.add_heading("What the results show", level=1)
    lead_paragraph(
        document,
        "Large shifts help.",
        "Removing the largest shifts progressively increased variability. "
        "Ladders beginning at ±28, ±14 and ±7 retained the same minimum "
        "availability at 400 iterations, but ±3 and ±1 lost aircraft on at "
        "least two forecasts. In the recommended ladder, 36% of accepted "
        "moves were ±42 or ±56, showing that the larger shifts were actively "
        "used rather than simply adding search cost."
    )
    lead_paragraph(
        document,
        "Search coarse to fine.",
        "Reversing the baseline ladder so that ±1 was searched first produced "
        "the same schedules as using ±1 alone through 800 iterations. Small "
        "improvements kept the search in the first neighbourhood, so it never "
        "reached the larger shifts. At 400 iterations this reduced the minimum "
        "availability from 18/19/20 aircraft to 17/18/18. Larger shifts should "
        "therefore be searched first."
    )
    lead_paragraph(
        document,
        "Use 400 iterations.",
        "Every 200-iteration run reached its limit, so 200 is too short. The "
        "recommended ladder found no further improving move after 291 to 367 "
        "accepted moves on the three forecasts, and its 800-iteration results "
        "were identical. A 400-iteration limit captures its full result "
        "without unnecessary work."
    )

    document.add_heading("Limits and next step", level=1)
    document.add_paragraph(
        "The analysis covers three related forecasts and deterministic runs, "
        "so it does not show variation across repeated trials or establish a "
        "global optimum. Differences between the leading strategies are only "
        "hundredths of an aircraft in standard deviation and may change on a "
        "different fleet or starting schedule. The optimiser also does not "
        "enforce the separate loose, medium and tight operational scenarios; "
        "those constraints still need review before deployment."
    )
    document.add_paragraph(
        "Keep the wide-to-fine ladder at 400 iterations as the shared setting. "
        "If simplicity is more important than the small reduction in "
        "variability, the ±28 baseline is a reasonable alternative because "
        "it preserves the same minimum availability. Repeat the comparison "
        "when the fleet, maintenance rules or starting schedule changes. "
        "The workbook contains the complete trial results."
    )
    return document
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
python -m pytest tests/test_vn_report.py -q
```

Expected: `1 passed`.

- [ ] **Step 3: Regenerate the report**

Run:

```powershell
python .scratch/vn-step-size-study/build_report.py
```

Expected: prints the path to `vn-hyperparameter-analysis2.docx`.

- [ ] **Step 4: Verify page count and wording**

Run the report through Word COM and verify `ComputeStatistics(2)` returns `2`. Extract text with python-docx and confirm none of the prohibited phrases appear. Inspect both rendered pages for clipped text, split rows, orphan headings, or excessive whitespace.

- [ ] **Step 5: Run the affected tests**

Run:

```powershell
python -m pytest tests/test_vn_report.py tests/test_vn_hyperparameter_analysis.py -q
```

Expected: `32 passed`.

- [ ] **Step 6: Commit the rewrite**

```powershell
git add .scratch/vn-step-size-study/build_report.py `
  docs/reports/2026-10-22-vn-step-size-study/vn-hyperparameter-analysis2.docx `
  tests/test_vn_report.py `
  docs/superpowers/plans/2026-10-23-vn-report-rewrite.md
git commit -m "docs: streamline VN parameter report"
```
