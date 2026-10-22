import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import savn_early_d_planning as p

schedule, base = p.load_schedule(ROOT / "heavy_maintenance_forecast.xlsx", "MxEvents")
horizon = max(e["latest_start"]+e["duration"] for es in schedule.values() for e in es)

def trace(frame, event, arg):
    if frame.f_code.co_name == "build_aircraft_plan" and event == "return" and arg is None:
        selected = {k: frame.f_locals.get(k) for k in ("due", "available", "check", "start", "end", "low", "high", "d_target", "plan")}
        print(json.dumps(selected, indent=2))
    return trace

sys.settrace(trace)
p.build_aircraft_plan(schedule["Aircraft 24"], horizon)
sys.settrace(None)
print("REFERENCE", json.dumps(schedule["Aircraft 24"], indent=2))
