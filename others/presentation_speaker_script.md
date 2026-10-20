# Iteration 1 — Full Speaking Script

Read this naturally. It is written to last about twelve to fifteen minutes if you speak at a normal pace. Pause where it feels right, and skip a sentence if you are running long.

---

## Slide 1 — What this project is about

Thanks everyone, and welcome if you are joining us for the first time.

I will start with a bit of context so we are all on the same page. This project is about scheduling heavy maintenance for a fleet of aircraft. Each aircraft needs a sequence of planned checks over a long forecast horizon — A, B, C, and D checks — and those checks have legal windows for when they can start. The operational problem is that if too many aircraft go into maintenance at the same time, fleet availability drops, and that hurts the ability to fly the mission.

So the goal is not to cancel maintenance. The goal is to stagger it. We shift when each check starts, still inside the allowed windows, so the dips in availability are as shallow as possible and the day-to-day curve is as smooth as we can make it.

The way we score a schedule reflects that. First we try to raise the minimum number of aircraft available on the worst day in the forecast. If two schedules have the same floor, we prefer the one with less variation. If those are still tied, we look at average availability. And alongside quality, the method has to finish in a practical amount of time, because once the dataset gets large, a slow optimiser is hard to use.

What I am going to walk through today is Iteration 1: how we started with a simple proof of concept, tried a few search strategies on a heavier dataset, and ended up with a priority-based method that improves the schedule and runs much faster than the earlier approaches.

---

## Slide 2 — Title / Iteration 1 results

This is Iteration 1, results and review. The short version of the outcome is that we moved from exhaustive neighbourhood search to priority-based selection, and that is what made the optimiser practical.

On the heavy dataset, the priority method lifted minimum availability from fifteen aircraft to eighteen, and it reduced the standard deviation from about 1.96 down to 1.44. Average availability barely changed. That is actually fine for us, because the objective is deliberately lexicographic. We care about the worst day first. A schedule that protects the floor is more valuable than one that only lifts the average.

I will show the path we took to get there, milestone by milestone.

---

## Slide 3 — Overview

There are four milestones in this iteration.

Milestone one was a simple fleet dataset. The point there was to prove that the optimisation objective and the feasibility rules worked at all.

Then we moved to a heavy multi-year forecast with twenty-four aircraft and two hundred and seventy-eight maintenance events. On that dataset we tried three search strategies. First, full neighbourhood search. Second, a shortcut that randomly sampled two hundred neighbours. Third, priority-based selection, which is where we landed.

The story is fairly straightforward. First make it work. Then see what breaks when you scale. Then stop searching blindly and start searching where the availability problem actually is.

---

## Slide 4 — Milestone 1 · Simple dataset

Milestone one used a small random fleet plan with eighty maintenance events. The optimiser shifts event start times inside feasible windows, rejects overlapping maintenance on the same aircraft, and scores each schedule with that same order I mentioned: maximise minimum availability, then minimise variation, then maximise the average.

We used variable neighbourhood search, so we try larger shifts first and then move to finer ones. That helps escape poor local solutions without jumping straight into tiny adjustments.

The important result from this milestone was not that we had an industrial-ready system. It was that we could stagger a schedule under hard constraints and improve that lexicographic score. One thing I want to flag early: please do not compare runtimes from this simple dataset with the heavy-dataset timings later. They are different problem sizes, and treating them as a direct speed comparison would be misleading.

---

## Slide 5 — Extended heavy maintenance dataset

This is the dataset that really stressed the algorithms.

Maintenance follows the repeating cycle A, B, A, C, A, B, A, D. The forecast is at least twelve years long, which is about one and a half maintenance cycles. There are twenty-four aircraft, each with roughly eleven to twelve events in the forecast, for two hundred and seventy-eight events in total.

Once you are at that scale, every candidate move becomes more expensive. Deep-copying schedules, checking feasibility, and recomputing availability add up quickly if you do it for every aircraft, every event, and every shift. The next three milestones all use this same heavy dataset, so those comparisons are fair. The simple dataset stays in the story as the proof of concept, not as the benchmark for speed.

---

## Slide 6 — Milestone 2 · Full neighbourhood

Full neighbourhood search is the thorough baseline. For every aircraft and every event, we try the shift sizes: plus or minus twenty-eight days, then fourteen, seven, and three. Each candidate is created by deep-copying the whole fleet schedule. Then we check feasibility and score the full schedule.

That approach does improve quality, but the cost grows with fleet size times number of events times number of shifts. On this heavy dataset it took about fifteen minutes — around nine hundred and twenty seconds. That is acceptable if you are running a one-off experiment. It is not ideal if you want to iterate, debug, or eventually plug the optimiser into a planning workflow.

So the next question was obvious: can we keep most of the quality while evaluating fewer candidates?

---

## Slide 7 — Milestone 3 · 200 random samples

Milestone three uses the same heavy dataset and the same shift sets, but with a sampling cutoff. If the neighbourhood contains more than two hundred feasible neighbours, we randomly keep two hundred and only score those.

That did reduce runtime. It came down to about seven and a half minutes, around four hundred and fifty-one seconds. So sampling helped. But it also introduced a real trade-off. Because the selection is random, you can miss the best improving move in that neighbourhood. Unless you fix a seed, the run is also non-deterministic. And importantly, we were still deep-copying full schedules and fully revalidating candidates, so a large part of the computational cost was still sitting there.

This was a useful intermediate step. It showed that thinning the search can help, but random thinning is not really a search strategy. It is a compromise. That motivated a smarter, deterministic way to choose which candidates to evaluate.

---

## Slide 8 — Milestone 4 · Priority-based selection

This is the method I want to spend the most time on, because it is the main technical result of Iteration 1.

Priority-based selection changes the question we ask. Instead of asking “what happens if we try every feasible move?” or “what happens if we try a random subset?”, we ask “which maintenance events are actually hurting the worst days in the availability curve?”

Every event gets a priority equal to the lowest fleet availability on any day that event is in the hangar. So if an event overlaps a day when only fifteen aircraft are available, that event is priority fifteen. Those events are the ones we search first, because they are the ones sitting on the availability floor.

When we move one check, we do not leave the rest of that aircraft’s plan sitting in a potentially broken state. We rebuild the later events using the A, B, C, D maintenance rules. Larger checks reset the smaller ones in the cycle, due windows are recalculated, and starts are kept where they are still legal or clamped into the new legal window. If a rebuild cannot produce a valid downstream plan, we reject that candidate.

We also changed how scoring works. We do not deep-copy the entire fleet for every trial. We rebuild one aircraft, then update availability incrementally: remove that aircraft’s old hangar intervals from the stored availability array, add the rebuilt intervals, and score once. That is much cheaper than recomputing availability from scratch for every neighbour.

On the heavy dataset, that gave us a better schedule — minimum availability from fifteen to eighteen, standard deviation from about 1.96 to 1.44 — and a median runtime of about fifteen seconds. So the quality improved, and the method became practical.

---

## Slide 9 — How priority levels work

I want to walk through the mechanics of those priority levels, because this is usually where the detailed questions come up.

Take the starting heavy schedule. The global minimum availability is fifteen. First, we score every event. For each event we look at fleet availability on every day that event is in the hangar, and the priority is the minimum of those days. For example, if an event covers days with availability eighteen, fifteen, sixteen, and so on, its priority is fifteen.

Second, we split the events into exclusive buckets by that priority. In our starting schedule we had twenty events at level fifteen, ten at sixteen, nine at seventeen, and larger groups at higher levels. An event sits in only one bucket: the bucket for its own worst day. So the twenty events at fifteen and the ten at sixteen are different events. They are not stages of the same repair ladder.

Third, we search worst first. For a shift set like plus and minus twenty-eight, level fifteen is about twenty events times two shifts, so around forty candidates. If any of those moves improve the score, we stop at that level for the iteration and take the best improving move. We only expand to level sixteen, then seventeen, and so on if the worse levels find nothing.

That is why the method is both targeted and fast. We are not randomly discarding most of the neighbourhood. We are concentrating effort on the events that touch the availability floor, and we only widen the search when we have to.

One detail that sometimes confuses people: on a day when availability is fifteen, only nine aircraft are actually in maintenance, because twenty-four minus fifteen is nine. That does not mean there are only nine priority-fifteen events. Priority is assigned across the whole timeline. Many different events can each brush a fifteen-day dip at some point, so twenty events can carry priority fifteen even though only nine aircraft are down on any single trough day.

---

## Slide 10 — Measured comparison

Here are the measured results on the same heavy dataset.

For schedule quality under the priority method, minimum availability went from fifteen to eighteen, standard deviation from 1.96 to 1.44, and average availability stayed almost flat at about 21.76 to 21.75.

For runtime, full neighbourhood search took about nine hundred and twenty seconds, which is roughly fifteen minutes. The two-hundred random sample method took about four hundred and fifty-one seconds, which is roughly seven and a half minutes. Priority selection took about fifteen point four seconds as the median of three runs.

So we improved the worst-case availability and the variation, and we cut runtime by about sixty times compared with full neighbourhood search, and by about thirty times compared with random sampling. That is the Iteration 1 result we wanted to demonstrate: better schedules, and a method you can actually run repeatedly.

---

## Slide 11 — Future work

Looking ahead to Semester Two and Iteration 2, the plan is to investigate a simulated annealing and variable neighbourhood search hybrid, bring in additional operational and logistics constraints, analyse hyperparameters more carefully, and test whether the initial stagger of the schedule changes the final outcome. In the nearer term that also includes thinking about windows where we maximise availability and allow surrounding events to move, while controlling standard deviation inside those windows.

That is Iteration 1. I am happy to take questions, especially on the priority-based method.

---

# Priority-based selection — Q&A notes

These are full answers you can use if someone asks. Speak them in your own words; you do not need to read them verbatim unless you want to.

### Why is priority faster than the two-hundred random sample method?

Because random sampling still paid most of the expensive cost. In that implementation we generated neighbours by deep-copying whole fleet schedules, and only afterwards kept two hundred of them to score. Priority never deep-copies the full fleet for each candidate. It rebuilds one aircraft, patches the availability array, and usually only evaluates the events in the worst priority bucket first. So it does less copying, less full recomputation, and fewer pointless evaluations.

### Doesn’t rebuilding the aircraft make each candidate slower?

Yes, rebuild is more work than shifting one date and leaving later events untouched. But it is still much cheaper than deep-copying twenty-four aircraft and recomputing availability from scratch for every neighbour. Rebuild also keeps the candidate operationally meaningful. Without it, an early move can break later due windows or create illegal overlaps.

### What does priority fifteen mean? Is that twenty samples?

No. Fifteen is an availability level, not a sample size. It means the event overlaps at least one day when fleet availability was fifteen. In our starting schedule, twenty events had that property. We evaluate those events against the current shift sizes. That is not the same thing as randomly sampling twenty neighbours from the whole neighbourhood.

### Are the priority buckets nested? Is level sixteen inside level fifteen?

No. They are an exclusive partition. Each event gets one priority: its own worst day. Level fifteen and level sixteen contain different events.

### If only nine aircraft are in maintenance on a day-fifteen trough, why were there twenty events at priority fifteen?

Because those two numbers answer different questions. Nine is how many aircraft are unavailable on one calendar day. Twenty is how many events, across the whole forecast, touch some day when availability bottoms out at fifteen. An event can brush a trough without being one of nine simultaneous hangar jobs on that exact day, and many events across time can each touch a fifteen-day dip.

### Do you always only search level fifteen?

No. We search worst first. If level fifteen has no improving move for that shift set, we expand to the next levels. If we find an improvement at fifteen, we take the best one and move to the next iteration.

### Is the method deterministic?

Yes, given the same schedule and the same shift sets. Events are ordered by priority, then by start time, aircraft name, and index. There is no random sampling in the priority method.

### What if several moves improve the score?

We keep the improving candidates at that priority level and choose the best score under the same lexicographic order: higher minimum availability first, then lower standard deviation, then higher average.

### Why does average availability barely change?

Because average is only the third tie-break. The operational story is to protect the worst day. It is completely consistent to raise the floor and smooth the curve while the long-run average stays almost the same.

### How do the A/B/C/D rebuild rules work when you move a check?

Events before the selected move stay unchanged. The selected check moves by the candidate shift. Later checks are recalculated from the due-date logic, including the way larger checks reset smaller ones. If an old start is still legal we keep it; otherwise we clamp it into the new legal window. If the rebuild cannot produce a valid plan, the candidate is rejected.

### Could you score moves without rebuilding?

You could numerically, but then the candidate may violate maintenance rules downstream. Rebuild is what makes the move a realistic schedule change rather than just shuffling one date in isolation.

### Will this still scale if the fleet gets bigger?

That is the reason we moved to priority search. The cost is tied much more to events near the bottleneck than to evaluating every event with a full fleet copy. Iteration 2 still needs more constraints and more stress testing, but the scaling direction is better than exhaustive search or random sampling.

### Why not just use an integer programming model?

That is a fair longer-term question. Iteration 1 was about building a practical local-search path we could implement, validate with rules, and time on the heavy forecast. Priority-based variable neighbourhood search sits in that lane. Exact optimisation methods are a possible research direction later, especially once more operational constraints are in place.
