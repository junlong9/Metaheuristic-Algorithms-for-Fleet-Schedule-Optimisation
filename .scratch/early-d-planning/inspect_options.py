"""Calendar illustrations for brainstorming, not a feasibility certificate."""
import sys
import json
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".scratch/busy-period-tradeoff"))
from check_windows import baseline

schedule, base = baseline.load_heavy_schedule(ROOT / baseline.FILE_PATH, baseline.SHEET_NAME)
start_of_busy = baseline.pd.Timestamp("2033-04-27")
latest_clear_start = start_of_busy - timedelta(days=126)
rows = []
for name in ("Aircraft 15", "Blue-8"):
    checks = schedule[name]
    index = next(i for i, e in enumerate(checks) if e["check"] == "D")
    e = checks[index]
    due = base + timedelta(days=e["latest_start"])
    previous = checks[index-1]
    previous_end = base + timedelta(days=previous["start"]+previous["duration"])
    rows.append({"aircraft": name, "D_due": str(due.date()),
                 "D_start_to_finish_before_busy": str(latest_clear_start.date()),
                 "D_finish_boundary": str(start_of_busy.date()),
                 "days_early_required": (due-latest_clear_start).days,
                 "extra_early_allowance_vs_current": (due-latest_clear_start).days-70,
                 "previous_loaded_check": previous["check"],
                 "previous_loaded_check_finish": str(previous_end.date()),
                 "previous_loaded_check_finishes_before_proposed_D": bool(previous_end <= latest_clear_start)})
document = {"illustrations": rows,
            "note": "These starts remove these two first-D checks from the entire spring busy period. They do not establish full-fleet feasibility or validate the proposed replacement policy. All other checks and future due resets still need planning."}
Path(__file__).with_name("calendar-options.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
print(json.dumps(document, indent=2))
