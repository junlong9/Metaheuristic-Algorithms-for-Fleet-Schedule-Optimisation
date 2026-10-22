"""Compare rerun endpoints of the original four strategies with the 2026-10-20 study."""

from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "docs/reports/2026-10-20-vn-hyperparameter-analysis/summary.csv"
NEW = ROOT / "docs/reports/2026-10-22-vn-step-size-study/results.json"
OUT = Path(__file__).with_name("sha-check.json")


def main() -> int:
    with OLD.open(newline="", encoding="utf-8") as handle:
        old = {row["trial_key"]: row for row in csv.DictReader(handle)}
    new = {
        item["trial_key"]: item
        for item in json.loads(NEW.read_text(encoding="utf-8"))["trials"]
    }
    rows = []
    for key, before in old.items():
        after = new.get(key)
        rows.append({
            "trial_key": key,
            "old_sha256": before["endpoint_sha256"],
            "new_sha256": after["endpoint_sha256"] if after else None,
            "match": bool(after)
            and after["endpoint_sha256"] == before["endpoint_sha256"],
            "old_score": json.loads(before["lexicographic_score"]),
            "new_score": after["lexicographic_score"] if after else None,
        })
    mismatches = [row["trial_key"] for row in rows if not row["match"]]
    OUT.write_text(
        json.dumps(
            {"compared": len(rows), "mismatches": mismatches, "trials": rows},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"compared {len(rows)}; mismatches {len(mismatches)}: {mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
