"""Reproducible extension of the priority selection study without production edits."""
from pathlib import Path
import sys, copy, json, time, hashlib, platform, importlib.util, contextlib, io, ast, types
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
# The bundled document runtime lacks matplotlib. Exclude only GUI imports;
# compile the unchanged scheduling functions directly from the production file.
tree=ast.parse((ROOT/'vn_priority_based_selection.py').read_text())
tree.body=[n for n in tree.body if not (isinstance(n,ast.Import) and any(a.name=='matplotlib.pyplot' for a in n.names)) and not (isinstance(n,ast.ImportFrom) and n.module=='visualisations')]
opt=types.ModuleType('vn_priority_based_selection')
exec(compile(tree,str(ROOT/'vn_priority_based_selection.py'),'exec'),opt.__dict__)
sys.modules['vn_priority_based_selection']=opt
spec = importlib.util.spec_from_file_location('prior_study', ROOT/'.scratch/priority-based-selection/run_hyperparameter_study.py')
study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)
DEFAULT = study.DEFAULT_SHIFTS
HALVES = [(-28,-14,14,28),(-14,-7,7,14),(-7,-3,3,7),(-3,-1,1,3)]
DENSE = [(-28,28),(-21,21),(-14,14),(-7,7),(-3,3),(-1,1)]
WIDE = [(-42,42)] + DEFAULT
CONFIGS = {'Default': DEFAULT, 'Half steps': HALVES, 'Dense pairs': DENSE, 'Wide first': WIDE}

def fingerprint(schedule):
    return hashlib.sha256(json.dumps(schedule,sort_keys=True).encode()).hexdigest()

def stats(a):
    return {'min': int(a.min()), 'std': float(a.std()), 'avg': float(a.mean()),
            'worst_days': int(np.sum(a == a.min())), 'days_below_19': int(np.sum(a < 19)),
            'distribution': {str(int(k)):int(v) for k,v in zip(*np.unique(a,return_counts=True))}}

def run(schedule,horizon,shifts,policy='first_level',cap=800):
    start = time.perf_counter()
    current=copy.deepcopy(schedule); a=opt.compute_availability(current,horizon)
    score=opt.score_availability(a)
    trace=[{'iteration':0,'score':list(map(float,score)),**stats(a)}]
    level_counts=Counter(); exhausted=False
    for iteration in range(cap):
        found=False
        for level, offsets in enumerate(shifts):
            candidates=study.generate_neighbors_study(current,a,horizon,score,offsets,policy)
            if not candidates: continue
            chosen=max(candidates,key=lambda x:x['score'])
            current[chosen['aircraft']]=chosen['events']; a=chosen['availability']; score=chosen['score']
            level_counts[str(level+1)]+=1
            trace.append({'iteration':iteration+1,'score':list(map(float,score)),
                          'level':level+1,'shift':chosen['shift'],'aircraft':chosen['aircraft'],
                          'event_index':chosen['event_index'], **stats(a)})
            found=True; break
        if not found: exhausted=True; break
    elapsed=time.perf_counter()-start
    recomputed=opt.compute_availability(current,horizon)
    # Independent boolean occupancy check catches double counts and incremental drift.
    occupied=np.zeros(horizon+1,dtype=int)
    for events in current.values():
        occupied_aircraft=np.zeros(horizon+1,dtype=bool)
        for e in events: occupied_aircraft[e['start']:e['start']+e['duration']]=True
        occupied+=occupied_aircraft
    assert np.array_equal(a,recomputed)
    assert np.array_equal(a,len(current)-occupied)
    assert opt.is_rule_compliant_schedule(current,horizon)
    assert all(tuple(x['score'])<tuple(y['score']) for x,y in zip(trace,trace[1:]))
    assert sum(e['duration'] for es in current.values() for e in es)==sum(e['duration'] for es in schedule.values() for e in es)
    return current, {'score':list(map(float,score)),**stats(a), 'elapsed_seconds':elapsed,
        'accepted_moves':len(trace)-1,'exhausted':exhausted,'rule_compliant':True,
        'independent_availability_verified':True,'schedule_sha256':fingerprint(current),
        'level_move_counts':dict(level_counts),'trace':trace}

def perturbed_start(schedule,horizon,seed):
    # Keep the same first due clocks and check count; legally perturb one later check per aircraft.
    rng=np.random.default_rng(seed); result=copy.deepcopy(schedule); changes=0
    for aircraft,events in result.items():
        order=list(rng.permutation(np.arange(1,len(events))))
        moved=False
        for index in order:
            for offset in rng.permutation([i for i in range(-14,15) if i]):
                rebuilt=opt.rebuild_aircraft_schedule(events,horizon,int(index),events[index]['start']+int(offset))
                if rebuilt is not None:
                    result[aircraft]=rebuilt; changes+=1; moved=True; break
            if moved: break
    assert opt.is_rule_compliant_schedule(result,horizon)
    return result,changes

def main():
    schedule,base=opt.load_heavy_schedule(ROOT/opt.FILE_PATH,opt.SHEET_NAME)
    horizon=opt.get_forecast_horizon(schedule)
    historical=json.loads((ROOT/'.scratch/priority-based-selection/hyperparameter-results.json').read_text())
    assert opt.is_rule_compliant_schedule(schedule,horizon)
    assert np.allclose(opt.evaluate_schedule(schedule,horizon), historical['original_score'],atol=1e-12,rtol=0)
    payload={'date':'2026-10-13','workbook_sha256':hashlib.sha256((ROOT/opt.FILE_PATH).read_bytes()).hexdigest(),
        'production_sha256':hashlib.sha256((ROOT/'vn_priority_based_selection.py').read_bytes()).hexdigest(),
        'historical_sha256':hashlib.sha256((ROOT/'.scratch/priority-based-selection/hyperparameter-results.json').read_bytes()).hexdigest(),
        'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),
        'base_date':str(base.date()),'last_date':str((base+__import__('pandas').Timedelta(days=horizon)).date()),
        'aircraft':len(schedule),'checks':sum(map(len,schedule.values())),'horizon_index':horizon,
        'observations':horizon+1,'check_counts':dict(Counter(e['check'] for es in schedule.values() for e in es)),
        'original':stats(opt.compute_availability(schedule,horizon)),'trials':[], 'start_variants':{}}
    out=WORK/'fresh-results.json'
    if out.exists():
        old=json.loads(out.read_text())
        assert old['workbook_sha256']==payload['workbook_sha256'] and old['production_sha256']==payload['production_sha256']
        payload=old
    def save():
        pending=WORK/'fresh-results.pending.json'
        pending.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        pending.replace(out)
    payload['complete']=False; save()
    def trial(name,phase,config,shifts,policy='first_level',cap=800,start_schedule=None,start_name='As loaded'):
        if any(t['name']==name for t in payload['trials']): return
        print('RUN',name,flush=True)
        best,record=run(schedule if start_schedule is None else start_schedule,horizon,shifts,policy,cap)
        record.update(name=name,phase=phase,config=config,params={'shift_sets':[list(x) for x in shifts], 'selection':policy,'max_iters':cap},start_name=start_name)
        # Keep the best result and every finalist for exact reproducibility.
        (WORK/(name+'-schedule.json')).write_text(json.dumps(best,indent=2),encoding='utf-8')
        if name=='default_rep1':
            with contextlib.redirect_stdout(io.StringIO()): native,score,history=opt.vn_optimise(schedule,max_iters=800)
            assert fingerprint(native)==record['schedule_sha256'] and tuple(score)==tuple(record['score'])
            assert len(history)==len(record['trace'])
            payload['production_equivalence_verified']=True
        payload['trials'].append(record); save()
        print(f"DONE {name} min={record['min']} std={record['std']:.9f} moves={record['accepted_moves']} sec={record['elapsed_seconds']:.2f} exhausted={record['exhausted']}",flush=True)
    for rep in range(1,4):
        for config in ['Default','Half steps','Wide first']:
            trial(f"{config.lower().replace(' ','_')}_rep{rep}" if config!='Default' else f'default_rep{rep}', 'repeat',config,CONFIGS[config])
    trial('dense_pairs_rep1','validation','Dense pairs',DENSE)
    for config in ['Default','Half steps','Dense pairs']:
        for policy in ['all_levels','first_improving']:
            trial(config.lower().replace(' ','_')+'_'+policy,'interaction',config,CONFIGS[config],policy)
    for index in range(4):
        shifted=copy.deepcopy(HALVES); shifted[index]=DEFAULT[index]
        trial(f'ablate_half_level_{index+1}','ablation',f'Remove half offsets at level {index+1}',shifted)
    trial('reverse_halves','order','Half steps reversed',list(reversed(HALVES)))
    trial('reverse_dense','order','Dense pairs reversed',list(reversed(DENSE)))
    trial('halves_plus_two','local_refine','Half steps plus two days',HALVES+[(-2,2)])
    trial('halves_plus_42','local_refine','Half steps plus 42 days',[(-42,42)]+HALVES)
    trial('halves_plus_21','local_refine','Half steps plus 21 days',[(-28,-21,-14,14,21,28)]+HALVES[1:])
    for seed in [41,42,43]:
        start,changes=perturbed_start(schedule,horizon,seed)
        payload['start_variants'][str(seed)]={'changed_aircraft':changes,'stats':stats(opt.compute_availability(start,horizon)), 'sha256':fingerprint(start)}
        (WORK/f'start_{seed}.json').write_text(json.dumps(start,indent=2))
        for config in ['Default','Half steps','Wide first']:
            trial(f'start_{seed}_'+config.lower().replace(' ','_'),'start_sensitivity',config,CONFIGS[config],start_schedule=start,start_name=f'Perturbed {seed}')
    leader=max([t for t in payload['trials'] if t['start_name']=='As loaded'],key=lambda t:t['score'])
    payload['fresh_leader_name']=leader['name']
    if leader['config'] not in ['Default','Half steps','Wide first'] or leader['params']['selection']!='first_level':
        offsets=[tuple(x) for x in leader['params']['shift_sets']]
        for rep in [2,3]:
            trial(f'new_leader_rep{rep}','repeat',leader['config'],offsets,leader['params']['selection'])
        for seed in [41,42,43]:
            start=json.loads((WORK/f'start_{seed}.json').read_text())
            trial(f'start_{seed}_new_leader','start_sensitivity',leader['config'],offsets,leader['params']['selection'],start_schedule=start,start_name=f'Perturbed {seed}')
    payload['complete']=True; save()
    print('COMPLETE',len(payload['trials']),flush=True)

if __name__=='__main__': main()
