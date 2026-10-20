from pathlib import Path
import ast, sys, types, json, hashlib
from datetime import timedelta
from collections import Counter
import openpyxl
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
tree=ast.parse((ROOT/'vn_priority_based_selection.py').read_text())
tree.body=[n for n in tree.body if not (isinstance(n,ast.Import) and any(a.name=='matplotlib.pyplot' for a in n.names)) and not (isinstance(n,ast.ImportFrom) and n.module=='visualisations')]
b=types.ModuleType('vn_priority_based_selection')
exec(compile(tree,str(ROOT/'vn_priority_based_selection.py'),'exec'),b.__dict__)
schedule,base=b.load_heavy_schedule(ROOT/b.FILE_PATH,b.SHEET_NAME)
h=b.get_forecast_horizon(schedule)
a=b.compute_availability(schedule,h)
cores=[]
for ac,events in schedule.items():
    e=next(e for e in events if e['check']=='D')
    due=events[0]['latest_start']+365*7
    assert e['latest_start']==due and e['earliest_start']==due-70 and e['duration']==126
    cores.append({'aircraft':ac,'earliest':due-70,'due':due,'core_end_exclusive':due+56,'core_last_day':due+55})
forced=[sum(c['due']<=day<c['core_end_exclusive'] for c in cores) for day in range(len(a))]
peak=max(forced)
days=[i for i,k in enumerate(forced) if k==peak]
selected=[c for c in cores if c['due']<=days[0]<c['core_end_exclusive']]
for c in selected:
    for k in ['earliest','due','core_end_exclusive','core_last_day']:
        c[k+'_date']=(base+timedelta(days=c[k])).strftime('%d %b %Y')
    # Exhaust every integer legal D start for each selected aircraft and peak day.
    assert all(start<=day<start+126 for start in range(c['earliest'],c['due']+1) for day in days)
record={'workbook':b.FILE_PATH,'sha256':hashlib.sha256((ROOT/b.FILE_PATH).read_bytes()).hexdigest(),'fleet':len(schedule),'checks':dict(Counter(e['check'] for es in schedule.values() for e in es)),'horizon_index':h,'observations':len(a),'downtime':sum(e['duration'] for es in schedule.values() for e in es),'mean':float(a.mean()),'loaded_min':int(a.min()),'loaded_std':float(a.std()),'loaded_compliant':b.is_rule_compliant_schedule(schedule,h),'forced_peak':peak,'peak_days':days,'peak_dates':[(base+timedelta(days=d)).strftime('%d %b %Y') for d in days],'selected':selected,'core_intersection':[max(c['due'] for c in selected),min(c['core_end_exclusive'] for c in selected)],'legal_placements_checked':6*71,'occupancy_assertions':6*71*len(days)}
wb=openpyxl.load_workbook(ROOT/'optimised_heavy_maintenance_output.xlsx',read_only=True,data_only=True)
record['export_summary']=list(wb['Summary'].values)
try:
    optimised,_=b.load_heavy_schedule(ROOT/'optimised_heavy_maintenance_output.xlsx','Optimised_MxEvents')
    record['optimised_compliant']=b.is_rule_compliant_schedule(optimised,h)
    record['optimised_score']=list(map(float,b.evaluate_schedule(optimised,h)))
except Exception as e:
    record['export_validation_error']=str(e)
(ROOT/'.scratch/semester2-report/min19-evidence.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
