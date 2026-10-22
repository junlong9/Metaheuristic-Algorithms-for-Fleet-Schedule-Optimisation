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
    report_labels = dict(payload["labels"])
    report_labels.update(
        {
            "half_step_plus_42": "Half-step sets plus ±42",
            "live_wide_to_fine": "Wide to fine (±56 to ±1)",
        }
    )
    for strategy_key in payload["order"]:
        assert report_labels[strategy_key] in comparison_text
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
