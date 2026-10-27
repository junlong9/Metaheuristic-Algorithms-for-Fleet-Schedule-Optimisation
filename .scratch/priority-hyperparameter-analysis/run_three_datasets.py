"""Matched forecast study with preserved maintenance opening states."""
from pathlib import Path
import sys,json,hashlib,copy,time,importlib.util,contextlib,io,platform
from collections import Counter
import numpy as np
import pandas as pd

WORK=Path(__file__).resolve().parent; ROOT=WORK.parents[1]
sys.path.insert(0,str(WORK)); import frozen_baseline as old
opt=old.opt; ORIGINAL_REBUILD=opt.rebuild_aircraft_schedule
spec=importlib.util.spec_from_file_location('stagger_adapter',WORK/'frozen-source/run_priority_optimise.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
STATE=ROOT/'.scratch/initial-maintenance-stagger/schedule-data.json'
OPEN=json.loads(STATE.read_text())
SELECTED=sys.argv[sys.argv.index('--dataset')+1] if '--dataset' in sys.argv else None
SWEEP_ONLY='--sweep-only' in sys.argv
EXTRA_FINALIST=sys.argv[sys.argv.index('--extra-finalist')+1] if '--extra-finalist' in sys.argv else None
OUT=WORK/(f'three-dataset-{SELECTED}.json' if SELECTED else 'three-dataset-results.json'); SCHEDULES=WORK/'three-dataset-schedules'; SCHEDULES.mkdir(exist_ok=True)
FORECAST_START=pd.Timestamp(OPEN['forecast_start']); FORECAST_END=pd.Timestamp(OPEN['forecast_end'])
PATHS={'original':ROOT/'heavy_maintenance_forecast.xlsx',**{v['slug']:ROOT/'outputs/initial-stagger'/v['filename'] for v in OPEN['variants']}}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(payload):
    pending=OUT.with_suffix('.pending.json');pending.write_text(json.dumps(payload,indent=2));pending.replace(OUT)
def params_key(params):return json.dumps([params['shift_sets'],params['selection']])
def catalogue():
    h=json.loads((WORK.parent/'priority-based-selection/hyperparameter-results.json').read_text())
    f=json.loads((WORK/'fresh-results.json').read_text())
    seen=set();configs=[]
    # First put familiar configurations at the front, then cover every old structural setting.
    for name,shifts in old.CONFIGS.items():
        p={'shift_sets':[list(x) for x in shifts],'selection':'first_level'}
        seen.add(params_key(p));configs.append({'id':f'C{len(configs)+1:02d}','name':name,'params':p,'family':'Reference configurations'})
    for t in h['trials']+f['trials']:
        if t.get('phase')=='start_sensitivity':continue
        p={k:t['params'][k] for k in ['shift_sets','selection']};key=params_key(p)
        if key in seen:continue
        seen.add(key);configs.append({'id':f'C{len(configs)+1:02d}','name':t.get('config',t['name'].replace('_',' ')),'params':p,'family':t['phase']})
    return configs
def load_inputs():
    loaded={}
    for slug,path in PATHS.items():
        s,base=opt.load_heavy_schedule(path,'MxEvents');loaded[slug]=(s,base)
    origin=min([FORECAST_START]+[base for s,base in loaded.values()])
    datasets={}
    for slug,(s,base) in loaded.items():
        delta=(base-origin).days
        for es in s.values():
            for e in es:
                for field in ['start','earliest_start','latest_start']:e[field]+=delta
        if slug!='original':
            v=next(v for v in OPEN['variants'] if v['slug']==slug)
            adapter.attach_opening_state(s,origin,v['fleet'])
        datasets[slug]=s
    model_horizon=max(opt.get_forecast_horizon(s) for s in datasets.values())
    return datasets,origin,model_horizon,(FORECAST_START-origin).days,(FORECAST_END-origin).days
def availability(s,h):return opt.compute_availability(s,h)
def metrics(a):return {'min':int(a.min()),'std':float(a.std()),'avg':float(a.mean()),'worst_days':int(np.sum(a==a.min())),'days_below_19':int(np.sum(a<19)),'distribution':{str(int(k)):int(v) for k,v in zip(*np.unique(a,return_counts=True))}}
def signature(candidates):return [(c['aircraft'],c['event_index'],c['new_start'],tuple(c['score'])) for c in candidates]
def groups(s,a,lo,hi):
    ordered=[]
    for ac in sorted(s):
        for idx,e in enumerate(s[ac]):
            left=max(e['start'],lo);right=min(e['start']+e['duration'],hi+1)
            level=float(np.min(a[left:right])) if right>left else float('inf')
            ordered.append((level,e['start'],ac,idx))
    ordered.sort();result={}
    for level,_,ac,idx in ordered:result.setdefault(level,[]).append((ac,idx))
    return list(result.values())
def neighbours(s,a,h,lo,hi,current,shifts,policy,cached=None,counters=None,screen=False):
    collected=[]
    for bucket in groups(s,a,lo,hi) if cached is None else cached:
        improving=[]
        for ac,idx in bucket:
            es=s[ac];e=es[idx]
            if e['start']<lo:continue # Already commenced checks remain fixed.
            for offset in shifts:
                if counters is not None:counters['proposals']+=1
                rebuilt=opt.rebuild_aircraft_schedule(es,h,event_index=idx,new_start=e['start']+offset)
                if rebuilt is None or rebuilt[idx]['start']<lo:continue
                if counters is not None:counters['feasible_proposals']+=1
                if screen:
                    ca=a.copy()
                    for previous,updated in zip(es,rebuilt):
                        if previous['start']==updated['start'] and previous['duration']==updated['duration']:continue
                        ca[previous['start']:previous['start']+previous['duration']]+=1
                        ca[updated['start']:updated['start']+updated['duration']]-=1
                else:
                    ca=opt.availability_with_rebuilt_aircraft(a,es,rebuilt)
                visible=ca[lo:hi+1]
                if screen:
                    candidate_min=float(np.min(visible))
                    if candidate_min<current[0]:
                        if counters is not None:counters['screened_minimum']+=1
                        continue
                    if candidate_min==current[0]:
                        mean=float(np.sum(visible))/len(visible)
                        variance=float(np.dot(visible,visible))/len(visible)-mean*mean
                        # Integer-valued sums are exact here. The conservative margin
                        # exceeds rounding error by orders of magnitude. Every retained
                        # candidate is still scored by the original NumPy function.
                        if variance>current[1]*current[1]+1e-10:
                            if counters is not None:counters['screened_variance']+=1
                            continue
                score=opt.score_availability(visible)
                if score<=current:continue
                c={'aircraft':ac,'event_index':idx,'new_start':e['start']+offset,'shift':offset,'events':rebuilt,'availability':ca,'score':score}
                if policy=='first_improving':return [c]
                improving.append(c)
        if improving and policy=='first_level':return improving
        collected.extend(improving)
    return collected
def validate(s,initial,a,h,lo,hi):
    assert opt.is_rule_compliant_schedule(s,h)
    exact=availability(s,h);occupancy=np.zeros(h+1,dtype=int)
    for ac,es in s.items():
        occupied=np.zeros(h+1,dtype=bool)
        for i,e in enumerate(es):
            occupied[e['start']:e['start']+e['duration']]=True
            if initial[ac][i]['start']<lo:assert e==initial[ac][i]
            assert e['check']==initial[ac][i]['check'] and e['duration']==initial[ac][i]['duration']
            if '_origin' in e:assert e['_origin']==initial[ac][i]['_origin'] and e['_opening']==initial[ac][i]['_opening']
        occupancy+=occupied
    assert np.array_equal(exact,a) and np.array_equal(a,len(s)-occupancy)
    assert sum(map(len,s.values()))==sum(map(len,initial.values()))
def solve(s,h,lo,hi,config,cap=800):
    current=copy.deepcopy(s);a=availability(current,h);score=opt.score_availability(a[lo:hi+1]);trace=[{'iteration':0,'score':list(map(float,score))}]
    params=config['params'];counts=Counter();levels=Counter();started=time.perf_counter();exhausted=False
    for iteration in range(cap):
        cached=groups(current,a,lo,hi);accepted=False
        for level,shifts in enumerate(params['shift_sets'],1):
            candidates=neighbours(current,a,h,lo,hi,score,shifts,params['selection'],cached,counts,screen=True)
            if not candidates:continue
            best=max(candidates,key=lambda c:c['score']);current[best['aircraft']]=best['events'];a=best['availability'];score=best['score'];levels[str(level)]+=1
            trace.append({'iteration':iteration+1,'score':list(map(float,score)),'level':level,'shift':best['shift']});accepted=True;break
        if not accepted:exhausted=True;break
    elapsed=time.perf_counter()-started
    validate(current,s,a,h,lo,hi)
    assert all(tuple(x['score'])<tuple(y['score']) for x,y in zip(trace,trace[1:]))
    # Verify cached and uncached neighbour generation at the final endpoint for each level.
    for shifts in params['shift_sets']:
        left=neighbours(current,a,h,lo,hi,score,shifts,params['selection'],cached=groups(current,a,lo,hi),screen=True)
        right=neighbours(current,a,h,lo,hi,score,shifts,params['selection'])
        assert signature(left)==signature(right)
    return current,{'score':list(map(float,score)),**metrics(a[lo:hi+1]),'accepted_moves':len(trace)-1,'cap':cap,'exhausted':exhausted,'elapsed_seconds':elapsed,'proposal_counts':dict(counts),'level_counts':dict(levels),'trace':trace,'schedule_sha256':old.fingerprint(current),'rule_compliant':True,'independent_availability_verified':True,'past_checks_frozen':True}
def audit(s,initial,h,lo,hi,origin):
    full=availability(s,h);maxdisp=max(abs(e['start']-initial[ac][i]['start']) for ac,es in s.items() for i,e in enumerate(es));audits={}
    for scenario in OPEN['operational_constraints']['scenarios']:
        busy=[];dependencies=[]
        for b in scenario['busy_periods']:
            left=max(lo,(pd.Timestamp(b['start'])-origin).days);right=min(hi,(pd.Timestamp(b['end'])-origin).days)
            v=full[left:right+1];busy.append({'required':b['minimum_availability'],'actual_min':int(v.min()),'breach_days':int(np.sum(v<b['minimum_availability']))})
        for group in scenario['dependency_groups']:
            ga=np.zeros(h+1,dtype=int)
            for ac in group['aircraft']:
                occupied=np.zeros(h+1,dtype=bool)
                for e in s[ac]:occupied[e['start']:e['start']+e['duration']]=True
                ga+=(~occupied).astype(int)
            v=ga[lo:hi+1];dependencies.append({'required':group['minimum_available'],'actual_min':int(v.min()),'breach_days':int(np.sum(v<group['minimum_available']))})
        limit=scenario['displacement_limit_days'];audits[scenario['name']]={'passes':maxdisp<=limit and not any(b['breach_days'] for b in busy+dependencies),'displacement_limit':limit,'maximum_displacement':maxdisp,'busy_periods':busy,'dependency_groups':dependencies}
    return audits
def main():
    datasets,origin,h,lo,hi=load_inputs();configs=catalogue()
    if SELECTED:datasets={SELECTED:datasets[SELECTED]}
    hashes={k:sha(v) for k,v in PATHS.items()};hashes['opening_state']=sha(STATE);hashes['production']=sha(old.FROZEN_PRODUCTION);hashes['adapter']=sha(Path(adapter.__file__))
    payload={'date':'2026-10-14','hashes':hashes,'forecast_start':str(FORECAST_START.date()),'forecast_end':str(FORECAST_END.date()),'observations':hi-lo+1,'coordinate_origin':str(origin.date()),'model_horizon_index':h,'scoring_start_index':lo,'scoring_end_index':hi,'python':platform.python_version(),'numpy':np.__version__,'configs':configs,'datasets':{},'trials':[]}
    if OUT.exists():
        previous=json.loads(OUT.read_text());assert previous['hashes']==hashes and previous['configs']==configs;payload=previous
    elif SELECTED and (WORK/'three-dataset-results.json').exists():
        previous=json.loads((WORK/'three-dataset-results.json').read_text());assert previous['hashes']==hashes and previous['configs']==configs
        previous['trials']=[t for t in previous['trials'] if t['dataset']==SELECTED]
        previous['datasets']={k:v for k,v in previous['datasets'].items() if k==SELECTED};payload=previous
    for t in payload['trials']:
        if 'implementation' not in t:t['phase']='reference_validation'
    payload['complete']=False;dump(payload)
    for slug,s in datasets.items():
        opt.rebuild_aircraft_schedule=ORIGINAL_REBUILD if slug=='original' else adapter.rebuild_from_opening_state
        assert opt.is_rule_compliant_schedule(s,h)
        a=availability(s,h);metadata={'aircraft':len(s),'checks':sum(map(len,s.values())),'check_counts':dict(Counter(e['check'] for es in s.values() for e in es)),'initial':metrics(a[lo:hi+1]),'full_downtime':sum(e['duration'] for es in s.values() for e in es),'opening_checks_in_progress':sum(e['start']<lo<e['start']+e['duration'] for es in s.values() for e in es),'frozen_checks':sum(e['start']<lo for es in s.values() for e in es),'initial_operational_audit':audit(s,s,h,lo,hi,origin)}
        if slug!='original':
            expected=next(v for v in OPEN['variants'] if v['slug']==slug)['metrics']
            assert metadata['initial']['min']==expected['worst_day_availability']
            assert np.isclose(metadata['initial']['std'],expected['availability_std_population'],atol=1e-12,rtol=0)
            assert np.isclose(metadata['initial']['avg'],expected['mean_availability'],atol=1e-12,rtol=0)
            metadata['initial_saved_metrics_verified']=True
        already_checked=payload['datasets'].get(slug,{}).get('all_initial_neighbour_checks_passed',False)
        payload['datasets'][slug]=metadata
        print('DATASET',slug,metadata['checks'],metadata['initial'],flush=True)
        # Ensure the cached policy produces exactly the same proposals as the slow reference.
        score=opt.score_availability(a[lo:hi+1])
        if not already_checked:
            for config in configs:
                for shifts in config['params']['shift_sets']:
                    uncached=neighbours(s,a,h,lo,hi,score,shifts,config['params']['selection'])
                    cached=neighbours(s,a,h,lo,hi,score,shifts,config['params']['selection'],groups(s,a,lo,hi),screen=True)
                    assert signature(cached)==signature(uncached)
        metadata['all_initial_neighbour_checks_passed']=True;dump(payload)
        def trial(config,rep=1,cap=800,phase='sweep'):
            key=f'{slug}-{config["id"]}-r{rep}-cap{cap}-v2'
            if any(t['key']==key for t in payload['trials']):return
            print('RUN',key,config['name'],flush=True)
            best,result=solve(s,h,lo,hi,config,cap)
            result.update(key=key,dataset=slug,config_id=config['id'],config_name=config['name'],rep=rep,phase=phase,implementation='screened_interval_differences_v2',operational_audit=audit(best,s,h,lo,hi,origin))
            references=[t for t in payload['trials'] if t['dataset']==slug and t['config_id']==config['id'] and t['phase']=='reference_validation']
            if references:
                assert result['score']==references[0]['score'] and result['schedule_sha256']==references[0]['schedule_sha256']
                result['reference_full_trajectory_match']=result['trace']==references[0]['trace']
                assert result['reference_full_trajectory_match']
            (SCHEDULES/(key+'.json')).write_text(json.dumps(best,indent=2))
            payload['trials'].append(result);dump(payload)
            print(f'DONE {key} min={result["min"]} std={result["std"]:.9f} avg={result["avg"]:.9f} moves={result["accepted_moves"]} sec={result["elapsed_seconds"]:.2f} local={result["exhausted"]}',flush=True)
        for config in configs:trial(config)
        sweep=[t for t in payload['trials'] if t['dataset']==slug and t['phase']=='sweep']
        leader=max(sweep,key=lambda t:t['score']);metadata['leader_id']=leader['config_id']
        finalists=list(dict.fromkeys(['C01',leader['config_id']]))
        if EXTRA_FINALIST:finalists=list(dict.fromkeys(finalists+[EXTRA_FINALIST]))
        if SWEEP_ONLY:
            metadata['sweep_done']=True;dump(payload);continue
        for cid in finalists:
            config=next(c for c in configs if c['id']==cid)
            for rep in [2,3,4]:trial(config,rep=rep,phase='timing_repeat')
        # Resolve truncation for finalists rather than calling cap-limited scores converged.
        for cid in finalists:
            t=next(t for t in sweep if t['config_id']==cid)
            if not t['exhausted']:trial(next(c for c in configs if c['id']==cid),cap=1600,phase='budget_extension')
        metadata['done']=True;dump(payload)
    opt.rebuild_aircraft_schedule=ORIGINAL_REBUILD
    payload['complete']=True;payload['stage']='sweep' if SWEEP_ONLY else 'finalists';dump(payload);print('COMPLETE',len(payload['trials']),flush=True)
if __name__=='__main__':main()
