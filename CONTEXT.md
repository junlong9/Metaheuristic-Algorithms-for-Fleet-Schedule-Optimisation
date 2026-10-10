# Fleet Maintenance Scheduling

Research into re-timing a fleet's heavy maintenance checks so that as many aircraft as possible are available every day, while staying inside maintenance rules and operational limits.

## Language

### Fleet and maintenance

**Aircraft**:
One airframe in the fleet; it is either available or in maintenance on any given day.
_Avoid_: Tail, plane, unit

**Check**:
One scheduled heavy maintenance event of type A, B, C or D on one aircraft, with a fixed duration and a window in which it may start.
_Avoid_: Event, job, task

**Start window**:
The range of days a check may start in: from its due date minus its early-start allowance, up to its due date. Checks can only move earlier, never later.
_Avoid_: Slack, flexibility

**Rebuild**:
Re-placing an aircraft's later checks after one of its checks moves, so the maintenance interval rules stay satisfied.
_Avoid_: Cascade, reschedule

### Schedule quality

**Availability**:
The number of aircraft not in maintenance on a given day.

**Worst-day availability**:
The lowest availability over the forecast horizon; the primary measure of a schedule.
_Avoid_: Floor, min avail

**Smoothness**:
How evenly availability is spread across days, measured by its standard deviation; lower is better and it is the secondary measure.
_Avoid_: Bumpiness, variance

### Operational constraints

**Busy period**:
A date window in which worst-day availability must not drop below a required level. A schedule that breaks one is not acceptable.
_Avoid_: Availability-max window, protected period, surge

**Displacement limit**:
The furthest a check may move from its as-loaded start, including moves caused by a rebuild.
_Avoid_: Nearby move limit, surrounding-event limit

**Dependency group**:
A set of aircraft of which at least a stated number must be available on every day.
_Avoid_: Aircraft dependency, linked aircraft

### Methods and comparison

**Baseline**:
The frozen Iteration 1 priority-based selection hill-climb with its default settings.
_Avoid_: Current method, priority VNS

**Tuned baseline**:
The baseline hill-climb run with the best settings found by the hyperparameter study; the bar a new method must beat.

**Candidate method**:
Basin-hopping with tabu polish built on the baseline's neighbourhoods; the annealing approach being evaluated for adoption.
_Avoid_: SA (when the basin-hop method is meant)

**Best-so-far**:
The best schedule found during a search. It is what we report, even if the search has since moved on to a worse schedule.

**Tightened acceptance**:
The fallback rule that rejects any move lowering worst-day availability, and anneals only when that worst day is unchanged.
_Avoid_: Fair acceptance, staged acceptance

**Classic SA**:
Single-chain simulated annealing on the baseline's neighbourhoods; kept as an ablation, not a candidate.

**Typical result**:
The median outcome of three runs with fixed seeds, reported alongside the spread. Never compare a best-of-three against a single baseline run.
_Avoid_: Best run, headline result

**Start schedule**:
The schedule a search begins from. Stagger variants (bunched, as-loaded, spread) are different start schedules for the same checks and due dates.
_Avoid_: Initial stagger (when a different dataset is meant)
