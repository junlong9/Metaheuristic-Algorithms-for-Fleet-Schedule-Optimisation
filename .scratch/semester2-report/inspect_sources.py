from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import json, sys, ast, types
from collections import Counter
from datetime import timedelta
ROOT = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(ROOT))
# Load unchanged computational functions without optional plot imports.
tree = ast.parse((ROOT/'vn_priority_based_selection.py').read_text())
tree.body = [n for n in tree.body if not (isinstance(n,ast.Import) and any(a.name=='matplotlib.pyplot' for a in n.names)) and not (isinstance(n,ast.ImportFrom) and n.module=='visualisations')]
b = types.ModuleType('vn_priority_based_selection')
sys.modules[b.__name__] = b
exec(compile(tree, str(ROOT/'vn_priority_based_selection.py'),'exec'),b.__dict__)
import savn_iteration2 as s

for filename in ['Iteration 2 Execution Plan.pptx', 'Iteration 1.pptx', 'Iteration 1 Milestones.pptx']:
    print('\nDECK', filename)
    try:
        z = ZipFile(ROOT / filename)
    except PermissionError:
        print('LOCKED')
        continue
    with z:
        slides = sorted([n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')], key=lambda n:int(n.rsplit('slide',1)[1].split('.')[0]))
        for i,n in enumerate(slides,1):
            ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
            root=ET.fromstring(z.read(n))
            print('SLIDE', i, ' | '.join(t.text or '' for t in root.findall('.//a:t',ns)))
            if filename == 'Iteration 2 Execution Plan.pptx':
                note=f'ppt/notesSlides/notesSlide{i}.xml'
                if note in z.namelist():
                    print('NOTES', ' | '.join(t.text or '' for t in ET.fromstring(z.read(note)).findall('.//a:t',ns)))

schedule, base = b.load_heavy_schedule(ROOT/b.FILE_PATH, b.SHEET_NAME)
h=b.get_forecast_horizon(schedule)
a=b.compute_availability(schedule,h)
print('\nWORKBOOK', {'base':str(base),'horizon':h,'days':len(a),'aircraft':len(schedule),'counts':dict(Counter(e['check'] for v in schedule.values() for e in v)),'hangar_days':sum(e['duration'] for v in schedule.values() for e in v),'score':list(map(float,b.score_availability(a))),'valid':b.is_rule_compliant_schedule(schedule,h)})
cores=[]
for aircraft,events in schedule.items():
    e=next(e for e in events if e['check']=='D')
    due=events[0]['latest_start']+365*7
    cores.append((aircraft,e['latest_start'],e['earliest_start']+e['duration'],due,e['earliest_start']))
peak=max(sum(start<=d<end for _,start,end,_,_ in cores) for d in range(len(a)))
days=[d for d in range(len(a)) if sum(start<=d<end for _,start,end,_,_ in cores)==peak]
print('D_CORES', {'peak':peak,'days':days,'dates':[str(base+timedelta(days=d)) for d in days],'mismatch':sum(start!=due or early!=due-70 for _,start,_,due,early in cores),'aircraft':[ac for ac,start,end,_,_ in cores if start<=days[0]<end]})
for scenario in s.load_scenarios(ROOT/'operational_constraints.json',base):
    print('SCENARIO',scenario['name'],s.operational_breaches(schedule,scenario,schedule,h))
for kind in ['as-loaded','bunched','spread']:
    v=s.build_start_schedule(schedule,kind,h)
    due_changes=sum(x['latest_start']!=y['latest_start'] for ac in schedule for x,y in zip(schedule[ac],v[ac]))
    print('START',kind,{'score':list(map(float,b.evaluate_schedule(v,h))),'valid':b.is_rule_compliant_schedule(v,h),'due_changes':due_changes,'check_changes':sum(x['check']!=y['check'] for ac in schedule for x,y in zip(schedule[ac],v[ac])),'first_changes':sum(schedule[ac][0]['start']!=v[ac][0]['start'] for ac in schedule)})
for name in ['.scratch/priority-based-selection/hyperparameter-results.json','.scratch/priority-sa-hybrid/hyperparameter-results.json','.scratch/priority-sa-hybrid/std-chase-trials.json']:
    j=json.loads((ROOT/name).read_text(encoding='utf-8'))
    print('JSON',name,'type',type(j).__name__,'keys',list(j)[:20] if isinstance(j,dict) else len(j))
    if isinstance(j,dict):
        for k,v in j.items():
            print(k, str(v)[:1800] if not isinstance(v,list) else f'list length {len(v)} first {str(v[:1])[:1800]}')
