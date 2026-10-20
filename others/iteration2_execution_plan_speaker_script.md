# Iteration 2 — Execution Plan Speaking Script

Read this naturally. About ten to twelve minutes. Skip a sentence if you are running long.

---

## Slide 1 — Title

Thanks everyone.

Today is the Iteration 2 execution plan. Last semester we built a practical optimiser for staggering aircraft maintenance. This semester we look at four next steps: simulated annealing, extra constraints, settings analysis, and whether the starting schedule changes the result.

---

## Slide 2 — Iteration 1 recap

Quick recap of where we landed.

On the heavy dataset, we raised the worst-day availability from fifteen aircraft to eighteen, in about fifteen seconds.

What works well is how we search: we focus on the worst days, rebuild an aircraft’s plan when we move a check, and update availability cheaply.

What is still limited is decision-making. Today we only keep better moves, and we stop when nothing improves. That is why we are looking at simulated annealing next.

---

## Slide 3 — Four workstreams

Four workstreams for Semester 2.

One: simulated annealing — I will explain what that means, then how it fits our design.

Two: operational constraints — protect busy windows, and control how surrounding maintenance can move.

Three: settings analysis — find which controls actually change the results.

Four: starting stagger — check whether a good start is doing some of the work for us.

I will spend the most time on annealing next.

---

## Slide 4 — What is simulated annealing

Before I talk about how annealing fits our code, I want to explain what it is in plain language.

Simulated annealing is a search method. The idea comes from metalworking: heat metal so the atoms can move around, then cool it slowly so it settles into a strong structure. In optimisation, “heat” means we are more willing to try unusual moves. “Cooling” means we become stricter over time.

There are three simple steps.

First, search. We propose a change to the maintenance schedule — for example, shift a check a few days earlier or later — then score the new plan.

Second, accept. If the new plan is better, we keep it. That part is familiar. The difference is early in the search we may also keep a slightly worse plan, by chance. That sounds odd, but it is deliberate. A temporary worse move can get us out of a dead end.

Third, cool down. As the search continues, we accept fewer and fewer worse moves. Near the end, we mostly behave like today’s method: keep improvements, reject clear steps backwards.

Here is the picture I want you to keep. Think of walking over hills. Today’s optimiser only walks uphill. That is fast and safe, but you can get stuck on a small hill when a better peak is just nearby. Annealing sometimes takes a downhill step early, so you can leave that trap and reach a better overall schedule. Then, as things cool, those downhill steps become rare, and we settle on the best plan we found along the way.

For our project, that matters because availability scheduling has many local traps. Two schedules can look similar, but one path may need a short step that looks worse before the worst-day availability can rise.

Next I will show how this idea maps onto the optimiser we already built.

---

## Slide 5 — How annealing fits into our design

So how does annealing fit our design?

The important point is we do not throw away Iteration 1. We keep the parts that already work well, and we change the part that is too strict.

On the keep side: we still focus on the worst availability days first. We still rebuild an aircraft’s schedule after a move, so the A, B, C, D rules stay valid. We still update availability cheaply instead of recalculating everything. We still try larger timing shifts, then smaller ones. And we still remember the best schedule we have seen so far.

On the change side: currently we only keep improving moves. That is classic hill-climbing. The new method is annealing acceptance — better moves always; worse moves sometimes, more early, less later. We also drop the improve-only early-exit so worse candidates can actually be tried.

So the fit is clean if we think in layers. Annealing does not replace how we find candidate moves. It replaces how we decide whether to accept them. Keep the smart search. Change the acceptance rule.

That is the verdict: they fit together, but not as a simple plug-in. Next I will show the hybrid design in one line.

---

## Slide 6 — Fair acceptance and how we test

This slide covers two things: how we treat a worse move, and how we know which plan to keep.

Checklist. If the new schedule improves the worst day, keep it. If it makes the worst day worse, reject it. If the worst day stays the same but the plan is bumpier, annealing may accept that sometimes early, less often later.

We keep two plans. Current can go downhill so we can keep searching from it. Best-so-far only updates when something beats it — that is what we report.

Because annealing is random, we run the full search three to five times. We report the typical result, not the lucky best. Today’s method is deterministic, so one run is enough. Do not compare best-of-five annealing with one baseline run.

---

## Slide 7 — Constraints

Second workstream: constraints.

Right now the model mainly cares about maintenance rules and availability. That is fine for a prototype, but real operations have more limits.

So we will add windows where availability must stay high, control how far surrounding events can move, and check those rules separately from the availability score. A nicer curve is not enough if the plan is not operable.

---

## Slide 8 — Settings analysis

Third workstream: settings.

Several choices are already baked into today’s search: how far we move a check, how long we let it run, and whether we stop at the first improvement. If we add annealing, we also choose how quickly we become stricter.

Those choices affect both schedule quality and runtime, but we have not tested which ones actually matter.

So we will change one setting at a time on the heavy forecast, and watch worst-day availability and runtime together. The output should be a short list of settings that move the needle — not endless tuning. Document the result, then decide.

---

## Slide 9 — Initial stagger

Fourth: the starting schedule.

Our method starts from the loaded plan and only makes local changes. That means a well-staggered start can make the final result look better than the algorithm alone deserves. A “win” might just be a luckier start.

So we will build a few controlled starting plans — more bunched versus more spread out — and run the same search from each.

Today’s method and annealing get those same starts. We only call annealing better if it wins from the same starting plans. That keeps the comparison honest.

---

## Slide 10 — Timeline

Order of work.

Freeze the Iteration 1 baseline first. Then add annealing acceptance. Then define the scoring rule for worse moves. Then prototype the new constraints. Then test settings and starting stagger. Then decide: keep annealing, tune it, or stick with today’s method.

Do not invent new ideas before the baseline is locked.

---

## Slide 11 — Success criteria

What we will keep, and when we stop.

Keep annealing if the worst-day availability is at least as good as today, and it is not much slower. New operational rules still have to produce legal, usable schedules. And the gain has to come from the method — not a luckier start or a luckier random seed.

If annealing does not beat today’s method, we keep today’s method. If worse moves start hurting the worst day, we tighten the acceptance rule. If new constraints break feasibility, we do not ship them.

We only keep what the evidence supports.

Happy to take questions.
