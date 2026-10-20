"""Run finalist repetitions serially after every independent sweep finishes."""
from pathlib import Path
import json,subprocess,sys
WORK=Path(__file__).resolve().parent
SLUGS=['original','moderate','wide']
def load_cases():
    parts={s:json.loads((WORK/f'three-dataset-{s}.json').read_text()) for s in SLUGS}
    assert all(p['complete'] for p in parts.values())
    configs=parts['original']['configs'];cases={}
    for s,p in parts.items():
        assert p['configs']==configs
        for c in configs:
            ts=[t for t in p['trials'] if t['config_id']==c['id'] and t['phase'] in ['sweep','budget_extension']]
            assert ts;cases[s,c['id']]=max(ts,key=lambda t:t['score'])
    best={s:max((cases[s,c['id']] for c in configs),key=lambda t:t['score']) for s in SLUGS}
    eligible=[c for c in configs if all(cases[s,c['id']]['min']==best[s]['min'] and cases[s,c['id']]['exhausted'] for s in SLUGS)]
    def regrets(c):return [cases[s,c['id']]['std']/best[s]['std']-1 for s in SLUGS]
    shared=min(eligible,key=lambda c:(max(regrets(c)),sum(regrets(c)))) if eligible else None
    return shared
for attempt in range(3):
    shared=load_cases();extra=['--extra-finalist',shared['id']] if shared else []
    print('SHARED FINALIST',shared['id'] if shared else 'None',flush=True)
    for slug in SLUGS:
        print('SERIAL FINALISTS',slug,flush=True)
        subprocess.run([sys.executable,str(WORK/'run_three_datasets.py'),'--dataset',slug]+extra,check=True)
    updated=load_cases()
    if (updated['id'] if updated else None)==(shared['id'] if shared else None):break
else:raise RuntimeError('Shared recommendation did not stabilise after finalist extensions')
print('ALL FINALISTS COMPLETE',flush=True)
