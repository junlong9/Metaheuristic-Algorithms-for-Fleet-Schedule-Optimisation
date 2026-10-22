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
