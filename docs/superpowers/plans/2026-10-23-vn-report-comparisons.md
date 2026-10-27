# VN Report Comparisons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the self-contained VN report to three pages with a complete 13-method comparison table and both comparison graphs.

**Architecture:** Keep the concise report builder as the source of the narrative. Add a dedicated comparison page using `shared_table()` and `sd_chart()`, then place `runtime_chart()` with the findings on the third page. Use explicit page breaks so the Word layout remains stable.

**Tech Stack:** Python 3, python-docx, matplotlib, pytest, Microsoft Word COM.

## Global Constraints

- Rewrite `vn-hyperparameter-analysis2.docx` in place.
- Target exactly three readable A4 pages.
- Do not mention earlier studies, follow-up work, report dates, user recollection, cloud agents, or later adoption.
- Include all 13 shift methods at 400 iterations.
- Show minimum availability and standard deviation for Original, Moderate and Wide.
- Restore the variability-by-strategy and runtime-versus-standard-deviation graphs.
- Leave `summary2.xlsx` unchanged.

---

### Task 1: Update comparison-report regression coverage

**Files:**
- Modify: `tests/test_vn_report.py`

**Interfaces:**
- Consumes: `build_report.load() -> dict` and `build_report.build(payload) -> docx.Document`
- Produces: regression checks for all strategies, two tables, two graphs and self-contained wording

- [ ] **Step 1: Update the document assertions**

```python
def test_report_is_comparison_focused_and_self_contained():
    payload = build_report.load()
    document = build_report.build(payload)
    paragraph_text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    text = f"{paragraph_text}\n{table_text}"
    lowered = text.lower()

    assert 700 <= len(text.split()) <= 1300
    assert len(document.tables) == 2
    assert len(document.inline_shapes) == 2
    assert [
        p.text for p in document.paragraphs if p.style.name == "Heading 1"
    ] == [
        "What we tested",
        "Best results",
        "All strategies at 400 iterations",
        "What the results show",
        "Limits and next step",
    ]
    comparison_text = "\n".join(
        cell.text
        for row in document.tables[1].rows
        for cell in row.cells
    )
    for strategy_key in payload["order"]:
        assert payload["labels"][strategy_key] in comparison_text
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

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
python -m pytest tests/test_vn_report.py -q
```

Expected: FAIL because the current report has one table and no graphs.

- [ ] **Step 3: Commit the failing test**

```powershell
git add tests/test_vn_report.py
git commit -m "test: require VN strategy comparisons"
```

### Task 2: Restore the complete comparisons

**Files:**
- Modify: `.scratch/vn-step-size-study/build_report.py`
- Modify: `.scratch/vn-step-size-study/figures/sd-by-strategy-400.png`
- Modify: `.scratch/vn-step-size-study/figures/runtime-vs-sd-400.png`
- Modify: `docs/reports/vn-step-size-study/vn-hyperparameter-analysis2.docx`

**Interfaces:**
- Consumes: `shared_table(payload, 400)`, `sd_chart(payload, path)` and `runtime_chart(payload, path)`
- Produces: a three-page DOCX with two tables and two embedded figures

- [ ] **Step 1: Add the full comparison page before the findings**

Use `shared_table(payload, BUDGET)` to add one row per strategy. Each forecast cell must show `minimum / SD`, with `*` appended to the SD when that run stopped at the iteration limit. Sort using the existing combined-rank order and make the recommended first row bold.

```python
table_400 = shared_table(payload, BUDGET)
document.add_page_break()
document.add_heading(f"All strategies at {BUDGET} iterations", level=1)
comparison_rows = []
for row in table_400:
    values = [labels[row["key"]]]
    for item in row["cells"]:
        capped = "*" if item["stop_reason"] == "iteration_cap" else ""
        values.append(
            f"{item['min_availability']} / "
            f"{f4(item['availability_std'])}{capped}"
        )
    comparison_rows.append(values)
add_table(
    document,
    ["Strategy", "Original", "Moderate", "Wide"],
    comparison_rows,
    [7.0, 3.2, 3.2, 3.2],
    size=7.5,
    bold_rows={0},
)
document.add_paragraph(
    "Each result is minimum available aircraft / standard deviation. "
    "Lower standard deviation is better when minimum availability is equal. "
    "* indicates that the search reached the 400-iteration limit."
)
sd_path = FIGURES / "sd-by-strategy-400.png"
sd_chart(payload, sd_path)
document.add_picture(str(sd_path), width=Cm(14.5))
document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
caption(
    document,
    "Figure 1. Standard deviation at 400 iterations. Point labels show "
    "minimum available aircraft; filled points reach the best minimum for "
    "that forecast.",
)
```

- [ ] **Step 2: Add the runtime graph to the findings page**

Insert a page break before `What the results show`. After the three comparison findings, generate and add the runtime graph.

```python
rt_path = FIGURES / "runtime-vs-sd-400.png"
runtime_chart(payload, rt_path)
document.add_picture(str(rt_path), width=Cm(14.5))
document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
caption(
    document,
    "Figure 2. Search time against standard deviation at 400 iterations. "
    "Timings are single observations and are useful for relative comparison "
    "only.",
)
```

- [ ] **Step 3: Keep the narrative concise**

Retain the recommendation, method, best-results table, large-shift finding, search-order finding, 400-iteration rationale and limitations. Remove repeated figures already visible in the complete table or graph. Keep all prohibited historical phrases absent.

- [ ] **Step 4: Run the focused test**

Run:

```powershell
python -m pytest tests/test_vn_report.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Regenerate and verify the report**

Run:

```powershell
python .scratch/vn-step-size-study/build_report.py
```

Use Word COM to verify exactly three pages. Confirm page 1 contains the recommendation and best-results table, page 2 contains the complete comparison table and Figure 1, and page 3 contains the findings, Figure 2 and limitations.

- [ ] **Step 6: Run all affected tests**

Run:

```powershell
python -m pytest tests/test_vn_report.py tests/test_vn_hyperparameter_analysis.py -q
```

Expected: `32 passed`.

- [ ] **Step 7: Commit**

```powershell
git add tests/test_vn_report.py `
  .scratch/vn-step-size-study/build_report.py `
  .scratch/vn-step-size-study/figures/sd-by-strategy-400.png `
  .scratch/vn-step-size-study/figures/runtime-vs-sd-400.png `
  docs/reports/vn-step-size-study/vn-hyperparameter-analysis2.docx `
  docs/superpowers/plans/2026-10-23-vn-report-comparisons.md
git commit -m "docs: restore VN strategy comparisons"
```
