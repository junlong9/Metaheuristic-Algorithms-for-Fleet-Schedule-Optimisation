"""Verify the delivered Excel claim without importing either optimiser."""
import copy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CHECKS = 'ABCD'
DURATION = {'A':14, 'B':28, 'C':84, 'D':126}
INTERVAL = {'A':365, 'B':730, 'C':1460, 'D':2920}
EARLY = {'A':42, 'B':70, 'C':70, 'D':70}


def read_rows(book, name):
    values = iter(book[name].values)
    headers = next(values)
    return [dict(zip(headers, row)) for row in values if row[0] is not None]


def check_clocks(rows, loaded, horizon, d_early, require_coverage=True):
    schedule = {}
    for row in rows:
        schedule.setdefault(row['Aircraft'], []).append(row)
    assert set(schedule) == set(loaded), 'An aircraft was lost or added'
    all_terminal, violations, ranks = {}, [], {c:i for i,c in enumerate(CHECKS)}
    for ac, checks in schedule.items():
        first = loaded[ac][0]['Latest_Start']
        clocks = {'A':first, 'B':first+timedelta(days=365),
                  'C':first+timedelta(days=1095), 'D':first+timedelta(days=2555)}
        previous_end = first
        checks = sorted(checks, key=lambda row:row['Start'])
        assert checks[0]['Check']=='A' and checks[0]['Start']==first, (ac,'opening state changed')
        for row in checks:
            c, start, end = row['Check'], row['Start'], row['End']
            assert row['Duration'] == DURATION[c] and end-start == timedelta(days=DURATION[c]), (ac,'wrong duration')
            assert start >= previous_end, (ac,'overlap')
            early = d_early if c=='D' else EARLY[c]
            assert clocks[c]-timedelta(days=early) <= start <= min(clocks.values()), (ac,c,'deadline or early window',start,clocks)
            assert all(end <= clocks[h] for h in CHECKS[ranks[c]+1:]), (ac,c,'blocked higher deadline')
            assert row['Latest_Start']==clocks[c], (ac,c,'incorrect latest window')
            # Day-zero clamping is the only allowed difference in the earliest field.
            assert row['Earliest_Start']==max(BASE, clocks[c]-timedelta(days=early)), (ac,c,'incorrect earliest window')
            if start < clocks[c]-timedelta(days=EARLY[c]):
                violations.append({'aircraft':ac, 'check':c, 'start':str(start.date()),
                    'days_early':(clocks[c]-start).days})
            for covered in CHECKS[:ranks[c]+1]:
                clocks[covered] = end+timedelta(days=INTERVAL[covered])
            previous_end = end
        overdue = {c:str(date.date()) for c,date in clocks.items() if date<=horizon}
        if require_coverage:
            assert not overdue, (ac,'missing future checks',overdue)
        all_terminal[ac] = {'due':{c:str(d.date()) for c,d in clocks.items()}, 'uncovered':overdue}
    return all_terminal, violations


def occupancy(rows, aircraft, end):
    total_days = (end-BASE).days+1
    busy = {ac:np.zeros(total_days, dtype=bool) for ac in aircraft}
    for row in rows:
        start = (row['Start']-BASE).days
        stop = (row['End']-BASE).days
        assert row['Aircraft'] in busy and 0<=start<total_days
        assert not busy[row['Aircraft']][start:stop].any(), 'Overlapping checks'
        busy[row['Aircraft']][start:stop] = True
    return len(aircraft)-sum(busy.values()), busy


source = ROOT/'heavy_maintenance_forecast.xlsx'
delivered = ROOT/'optimised_priority_early_d_experimental_output.xlsx'
book = openpyxl.load_workbook(source, read_only=True, data_only=True)
loaded_rows = read_rows(book, 'MxEvents')
book.close()
loaded = {}
for row in loaded_rows:
    loaded.setdefault(row['Aircraft'], []).append(row)
for rows in loaded.values():
    rows.sort(key=lambda r:r['Start'])
BASE = min(row['Start'] for row in loaded_rows)
END = max(row['Latest_Start']+timedelta(days=row['Duration']) for row in loaded_rows)
audited_file = delivered
try:
    book = openpyxl.load_workbook(audited_file, read_only=True, data_only=True)
except PermissionError:
    # Excel exclusively locks the delivered copy while it is open. The original
    # saved export is the source copied to that delivery file in the prior turn.
    audited_file = OUT/'expanded_1825.xlsx'
    book = openpyxl.load_workbook(audited_file, read_only=True, data_only=True)
best_rows = read_rows(book, 'Optimised_MxEvents')
daily = read_rows(book, 'Optimised_Availability')
summary = read_rows(book, 'Summary')
original_rows = read_rows(book, 'Original_MxEvents')
book.close()
assert len(original_rows)==len(loaded_rows)
cols = ['Aircraft','Check','Start','End','Duration','Earliest_Start','Latest_Start']
canonical = lambda rs: sorted(tuple(r[c] for c in cols) for r in rs)
assert canonical(original_rows)==canonical(loaded_rows), 'Workbook original differs from input'
terminal, violations = check_clocks(best_rows, loaded, END, 1825)
a, busy = occupancy(best_rows, loaded, END)
assert len(daily)==len(a)
assert [r['Date'] for r in daily] == [BASE+timedelta(days=i) for i in range(len(a))]
np.testing.assert_array_equal(a, [r['Available'] for r in daily])
reported = next(r for r in summary if r['Schedule']=='Optimised')
assert int(a.min()) == reported['Min_Availability'] == 19
assert abs(a.std()-reported['Availability_Std'])<1e-12
assert abs(a.mean()-reported['Average_Availability'])<1e-12

# Negative controls: the validator must actually reject the suspected errors.
broken = copy.deepcopy(best_rows)
victim = next(row for row in broken if row['Check']=='D')
broken.remove(victim)
try:
    check_clocks(broken, loaded, END, 1825)
except AssertionError:
    missing_D_detected = True
else:
    raise AssertionError('Audit failed to detect missing D')
try:
    np.testing.assert_array_equal(a+1, [r['Available'] for r in daily])
except AssertionError:
    inflated_availability_detected = True
else:
    raise AssertionError('Audit failed to detect inflated availability')
try:
    check_clocks(best_rows, loaded, END, 70)
except AssertionError:
    original_policy_rejected = True
else:
    raise AssertionError('Result unexpectedly passes original 70-day policy')

policy = json.loads((ROOT/'operational_constraints.json').read_text())
audits = []
for scenario in policy['scenarios']:
    groups = []
    periods = []
    for group in scenario['dependency_groups']:
        ga = len(group['aircraft'])-sum(busy[ac] for ac in group['aircraft'])
        groups.append({'minimum':int(ga.min()), 'required':group['minimum_available'],
                       'breach_days':int((ga<group['minimum_available']).sum())})
    for period in scenario['busy_periods']:
        lo = (datetime.fromisoformat(period['start'])-BASE).days
        hi = (datetime.fromisoformat(period['end'])-BASE).days+1
        periods.append({'minimum':int(a[lo:hi].min()), 'required':period['minimum_availability']})
    audits.append({'name':scenario['name'], 'groups':groups, 'periods':periods})

advances = []
for ac in loaded:
    old = next(r for r in loaded[ac] if r['Check']=='D')
    new = min((r for r in best_rows if r['Aircraft']==ac and r['Check']=='D'), key=lambda r:r['Start'])
    advances.append({'aircraft':ac, 'loaded_start':str(old['Start'].date()),
                     'new_start':str(new['Start'].date()),
                     'advance_from_loaded_days':(old['Start']-new['Start']).days,
                     'days_early_before_due':(new['Latest_Start']-new['Start']).days})
pre2030 = [r for r in advances if r['new_start']<'2030-01-01']
baseline_json = json.loads((OUT/'baseline_default.json').read_text())
baseline_rows = []
for ac, checks in baseline_json['schedule'].items():
    for e in checks:
        baseline_rows.append({'Aircraft':ac, 'Check':e['check'],
            'Start':BASE+timedelta(days=e['start']),
            'End':BASE+timedelta(days=e['start']+e['duration']), 'Duration':e['duration'],
            'Earliest_Start':max(BASE, BASE+timedelta(days=e['earliest_start'])),
            'Latest_Start':BASE+timedelta(days=e['latest_start'])})
# Find terminal omissions; do not change or optimise either saved schedule.
baseline_error = None
try:
    baseline_terminal, _ = check_clocks(baseline_rows, loaded, END, 70, require_coverage=False)
except AssertionError as exc:
    baseline_terminal = None
    baseline_error = str(exc)


def deadline_diagnostics(rows):
    misses, uncovered = [], {}
    for ac in loaded:
        first = loaded[ac][0]['Latest_Start']
        clocks = {'A':first,'B':first+timedelta(days=365),
                  'C':first+timedelta(days=1095),'D':first+timedelta(days=2555)}
        es = sorted((r for r in rows if r['Aircraft']==ac), key=lambda r:r['Start'])
        for row in es:
            c,start,end = row['Check'],row['Start'],row['End']
            for pending, due in clocks.items():
                if start>due:
                    misses.append({'aircraft':ac,'performed_check':c,'start':str(start.date()),
                        'overdue_check':pending,'deadline':str(due.date()),'late_days':(start-due).days})
            for h in CHECKS[CHECKS.index(c)+1:]:
                if end>clocks[h]:
                    misses.append({'aircraft':ac,'performed_check':c,'start':str(start.date()),
                        'blocked_higher_check':h,'deadline':str(clocks[h].date()),
                        'late_days':(end-clocks[h]).days})
            for covered in CHECKS[:CHECKS.index(c)+1]:
                clocks[covered]=end+timedelta(days=INTERVAL[covered])
        terminal_missing = {c:str(d.date()) for c,d in clocks.items() if d<=END}
        if terminal_missing:
            uncovered[ac]=terminal_missing
    return {'deadline_breaches':misses,'uncovered_terminal_deadlines':uncovered}


def continue_at_due_dates(rows, end, d_early):
    """Unoptimised tail sensitivity; keep the entire saved schedule fixed."""
    extended = copy.deepcopy(rows)
    for ac in loaded:
        es = sorted((r for r in rows if r['Aircraft']==ac), key=lambda r:r['Start'])
        first = loaded[ac][0]['Latest_Start']
        clocks = {'A':first,'B':first+timedelta(days=365),
                  'C':first+timedelta(days=1095),'D':first+timedelta(days=2555)}
        previous_end = first
        for row in es:
            for covered in CHECKS[:CHECKS.index(row['Check'])+1]:
                clocks[covered] = row['End']+timedelta(days=INTERVAL[covered])
            previous_end=row['End']
        while min(clocks.values())<=end:
            next_due = min(clocks.values())
            required = max(CHECKS.index(c) for c in CHECKS if clocks[c]==next_due)
            options=[]
            for c in CHECKS[required:]:
                low = max(previous_end,clocks[c]-timedelta(days=EARLY[c]))
                high = min(next_due,clocks[c])
                for h in CHECKS[CHECKS.index(c)+1:]:
                    high = min(high,clocks[h]-timedelta(days=DURATION[c]))
                if low<=high:
                    options.append((c,high))
            assert options, (ac,'tail cannot be continued')
            c,start=options[-1]
            row={'Aircraft':ac,'Check':c,'Start':start,
                 'End':start+timedelta(days=DURATION[c]),'Duration':DURATION[c],
                 'Earliest_Start':max(BASE,clocks[c]-timedelta(days=d_early if c=='D' else EARLY[c])),
                 'Latest_Start':clocks[c]}
            extended.append(row)
            for covered in CHECKS[:CHECKS.index(c)+1]:
                clocks[covered]=row['End']+timedelta(days=INTERVAL[covered])
            previous_end=row['End']
    return extended


baseline_diagnostics = deadline_diagnostics(baseline_rows)
input_diagnostics = deadline_diagnostics(loaded_rows)
assert baseline_diagnostics['deadline_breaches'], 'Expected smaller-deadline reproducer disappeared'
# A fully compliant same-clock comparator from the previous experiment.
control = json.loads((OUT/'dynamic_70.json').read_text())
control_rows=[]
for ac,checks in control['schedule'].items():
    for e in checks:
        control_rows.append({'Aircraft':ac,'Check':e['check'], 'Duration':e['duration'],
            'Start':BASE+timedelta(days=e['start']), 'End':BASE+timedelta(days=e['start']+e['duration']),
            'Earliest_Start':BASE+timedelta(days=e['earliest_start']),
            'Latest_Start':BASE+timedelta(days=e['latest_start'])})
check_clocks(control_rows, loaded, END, 70)
tail_sensitivity=[]
for date in ('2040-04-28','2046-04-28'):
    end = datetime.fromisoformat(date)
    trial={}
    for name,rows,early in (('dynamic_70',control_rows,70),('expanded_1825',best_rows,1825)):
        extended=continue_at_due_dates(rows,end,early)
        # Appended D choices use only 70 days, a subset of the expanded policy;
        # exported metadata reflects the policy used to audit the whole plan.
        check_clocks(extended,loaded,end,early)
        aa,_=occupancy(extended,loaded,end)
        tail=aa[(END-BASE).days+1:]
        trial[name]={'full_horizon_minimum':int(aa.min()),'tail_only_minimum':int(tail.min()),
                     'full_horizon_std':float(aa.std()),'full_horizon_mean':float(aa.mean()),
                     'D_checks':sum(r['Check']=='D' for r in extended)}
    tail_sensitivity.append({'end':date,'continuation':'saved prefix fixed; due-date tail; no tail optimisation',**trial})

last_D = [r for r in best_rows if r['Check']=='D']
out = {'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
       'excel_sha256':hashlib.sha256(audited_file.read_bytes()).hexdigest(),
       'audited_excel_path':str(audited_file),
       'delivery_copy_locked':audited_file!=delivered,
       'direct_excel_audit_passed':True, 'worst_day':int(a.min()),
       'std':float(a.std()), 'mean':float(a.mean()),
       'downtime_aircraft_days':int((24-a).sum()),
       'checks':len(best_rows), 'D_checks':len(last_D),
       'negative_controls':{'missing_D_detected':missing_D_detected,
                            'inflated_availability_detected':inflated_availability_detected,
                            'original_policy_rejected':original_policy_rejected},
       'original_early_window_violations':violations,
       'first_D_advances':advances, 'before_2030':pre2030,
       'operational_audits':audits,
       'crossing_horizon_checks':[{'aircraft':r['Aircraft'],'check':r['Check'],
          'start':str(r['Start'].date()),'end':str(r['End'].date())} for r in best_rows if r['End']>END+timedelta(days=1)],
       'future_D_due_after_horizon':{ac:t['due']['D'] for ac,t in terminal.items()},
       'baseline_clock_replay_error':baseline_error,
       'baseline_uncovered_terminal_deadlines':None if baseline_terminal is None else {
           ac:t['uncovered'] for ac,t in baseline_terminal.items() if t['uncovered']},
       'baseline_diagnostics':baseline_diagnostics, 'as_loaded_diagnostics':input_diagnostics,
       'future_sensitivity':tail_sensitivity,
       'max_concurrent_checks':int((24-a).max()),
       'max_concurrent_D_checks':int((24-occupancy(last_D, loaded, END)[0]).max())}
(OUT/'claim-audit.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=2))
