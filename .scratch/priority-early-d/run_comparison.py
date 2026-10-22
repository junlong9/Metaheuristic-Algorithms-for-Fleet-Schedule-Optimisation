"""Compare the unchanged baseline and the new copy on a common horizon."""
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import vn_priority_based_selection as baseline
import vn_priority_based_selection_early_d as variant
from export import (export_optimised_to_excel, schedule_to_events_table,
                    make_availability_table)

OUT = Path(__file__).resolve().parent
HALF_STEPS = [(-28, -14, 14, 28), (-14, -7, 7, 14),
              (-7, -3, 3, 7), (-3, -1, 1, 3)]


def independent_audit(schedule, reference, horizon, d_early):
    # Literal rules and per-aircraft daily occupancy: no planner validator.
    durations = [14, 28, 84, 126]
    intervals = [365, 730, 1460, 2920]
    early = [42, 70, 70, d_early]
    occupancy = {}
    for ac, es in schedule.items():
        first = reference[ac][0]['latest_start']
        due = [first, first + 365, first + 1095, first + 2555]
        end_previous = first
        occupied = np.zeros(horizon + 1, dtype=int)
        for e in es:
            rank = 'ABCD'.index(e['check'])
            start, end = e['start'], e['start'] + e['duration']
            assert e['duration'] == durations[rank], (ac, e)
            assert max(0, end_previous, due[rank]-early[rank]) <= start <= min(due), (ac, e, due)
            assert all(end <= d for d in due[rank+1:]), (ac, e, due)
            assert e['latest_start'] == due[rank], (ac, e, due)
            assert e['earliest_start'] == max(0, due[rank]-early[rank]), (ac, e, due)
            assert start <= horizon
            occupied[start:min(end, horizon+1)] += 1
            for i in range(rank+1):
                due[i] = end + intervals[i]
            end_previous = end
        assert min(due) > horizon, (ac, 'uncovered terminal deadline', due)
        assert occupied.max() <= 1
        occupancy[ac] = occupied
    return len(schedule) - sum(occupancy.values()), occupancy


def metrics(schedule, horizon, base_date, initial, d_early, full_audit):
    a = variant.compute_availability(schedule, horizon)
    if full_audit:
        independent, occ = independent_audit(schedule, initial, horizon, d_early)
        np.testing.assert_array_equal(a, independent)
    else:
        assert baseline.is_rule_compliant_schedule(schedule, horizon)
        occ = {}
        for ac, es in schedule.items():
            occupied = np.zeros(horizon+1, dtype=int)
            for e in es:
                occupied[e['start']:e['start']+e['duration']] += 1
            assert occupied.max() <= 1
            occ[ac] = occupied
        np.testing.assert_array_equal(a, len(schedule)-sum(occ.values()))
    d_checks = [e for es in schedule.values() for e in es if e['check']=='D']
    first_dates = [next(e['start'] for e in es if e['check']=='D') for es in schedule.values()]
    policy = json.loads((ROOT/'operational_constraints.json').read_text())['scenarios'][0]
    groups = []
    for group in policy['dependency_groups']:
        ga = len(group['aircraft']) - sum(occ[ac] for ac in group['aircraft'])
        groups.append({'aircraft': group['aircraft'], 'minimum': int(ga.min()),
                       'required': group['minimum_available'],
                       'breach_days': int((ga < group['minimum_available']).sum())})
    busy = []
    for period in policy['busy_periods']:
        lo = (pd.Timestamp(period['start'])-base_date).days
        hi = (pd.Timestamp(period['end'])-base_date).days
        busy.append({'start': period['start'], 'end': period['end'],
                     'minimum': int(a[lo:hi+1].min())})
    return {'minimum': int(a.min()), 'std': float(a.std()), 'mean': float(a.mean()),
            'checks': sum(map(len, schedule.values())), 'D_checks': len(d_checks),
            'check_counts': {c: sum(e['check']==c for es in schedule.values() for e in es) for c in 'ABCD'},
            'total_full_check_days': sum(e['duration'] for es in schedule.values() for e in es),
            'within_horizon_unavailable_aircraft_days': int((len(schedule)-a).sum()),
            'first_D_range': [str((base_date+pd.Timedelta(days=x)).date()) for x in (min(first_dates),max(first_dates))],
            'aircraft_first_D_before_2030': sum(base_date+pd.Timedelta(days=x)<pd.Timestamp('2030-01-01') for x in first_dates),
            'D_checks_over_70_days_early': sum(e['latest_start']-e['start']>70 for e in d_checks),
            'max_D_days_early': max(e['latest_start']-e['start'] for e in d_checks),
            'dependency_groups': groups, 'busy_periods': busy,
            'independent_clock_coverage_audit': full_audit}


def main():
    initial, base_date = baseline.load_heavy_schedule(str(ROOT/baseline.FILE_PATH), baseline.SHEET_NAME)
    horizon = baseline.get_forecast_horizon(initial)
    cap = (pd.Timestamp('2030-01-01')-base_date).days - 1
    trials = [('baseline_default', None),
              ('dynamic_70', {'d_early_days':70}),
              ('expanded_1825', {'d_early_days':1825, 'experimental_early_d':True}),
              ('all_first_D_before_2030', {'d_early_days':1825, 'experimental_early_d':True, 'first_d_cap':cap})]
    results = {'horizon_days': horizon+1, 'base_date': str(base_date.date()),
               'horizon_end': str((base_date+pd.Timedelta(days=horizon)).date()),
               'input_sha256': hashlib.sha256((ROOT/baseline.FILE_PATH).read_bytes()).hexdigest(),
               'iteration_cap':400, 'trials':[]}
    for name, kwargs in trials:
        saved = OUT/(name+'.json')
        if saved.exists():
            prior = json.loads(saved.read_text())
            results['trials'].append(prior['metrics'])
            print('Reusing completed', name, flush=True)
            continue
        started = time.perf_counter()
        print('Running', name, flush=True)
        with (OUT/(name+'.log')).open('w') as log, contextlib.redirect_stdout(log):
            if kwargs is None:
                best, score, history = baseline.vn_optimise(initial, max_iters=400)
            else:
                best, score, history = variant.vn_optimise(initial, max_iters=400, horizon=horizon, **kwargs)
        elapsed = time.perf_counter()-started
        info = metrics(best, horizon, base_date, initial, 70 if kwargs is None else kwargs['d_early_days'], kwargs is not None)
        info.update(name=name, seconds=elapsed, accepted_moves=len(history)-1,
                    converged=len(history)-1<400, settings=kwargs)
        print(json.dumps(info), flush=True)
        results['trials'].append(info)
        (OUT/(name+'.json')).write_text(json.dumps(
            {'metrics':info, 'schedule':best, 'history':history}, indent=2,
            default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))
        (OUT/'comparison-results.json').write_text(json.dumps(results, indent=2))
        a = variant.compute_availability(best, horizon)
        original = variant.compute_availability(initial, horizon)
        export_optimised_to_excel(str(OUT/(name+'.xlsx')),
            schedule_to_events_table(initial, base_date), schedule_to_events_table(best, base_date),
            make_availability_table(original, base_date), make_availability_table(a, base_date),
            variant.score_availability(original), score)
    # The tuned baseline's published result is context, not a new timed trial.
    results['published_tuned_baseline'] = {'minimum':18, 'std':1.391860,
        'source':'.scratch/priority-based-selection/hyperparameter-report.md'}
    (OUT/'comparison-results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
