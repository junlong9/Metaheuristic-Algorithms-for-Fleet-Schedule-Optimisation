# What I found when I tuned the priority-based optimiser

I spent this study on the deterministic search in `vn_priority_based_selection.py`, not the simulated-annealing hybrid. That module only has a few real knobs: how far a check is allowed to jump, the order those jump sizes are tried, how many iterations you will pay for, and whether the search looks at one priority bucket or all of them before it picks a move. There is no temperature and no random seed. The same settings always produce the same schedule.

I left the production file alone. A quiet copy of the search loop in `run_hyperparameter_study.py` reused the existing scoring, rebuild, and neighbour code so the study would not drift from the live algorithm. Every finished schedule was checked with `is_rule_compliant_schedule`. All 74 of them passed.

The workbook was the local `heavy_maintenance_forecast.xlsx` on 17 September 2026: 24 aircraft, 278 events, a 4,480-day horizon. Off the sheet, the fleet sits at minimum availability 15 and standard deviation 1.950. Mean availability is 21.713, and that mean never moved in any trial. That is not a measurement quirk. Check durations are fixed, so the optimiser can only slide work around the calendar. Total downtime is conserved. The only things it can change are the worst day and how bumpy the rest of the timeline is.

The whole sweep took 3,151 seconds, a bit over 52 minutes. One later repeat of an already-known winner sat in the machine for 16 minutes; the first time that same setting finished in 95 seconds. I treat that long run as machine noise, not as a property of the algorithm.

## The short answer

Minimum availability 19 did not appear. The floor stayed at 18.

The published default settings still do what Iteration 1 said they do: they lift the forecast from 15 to 18 and cut the standard deviation to 1.413971 in about 15 seconds. They are not the best settings.

The best configuration I found keeps the current “look at the worst-availability events first, then take the best improving move in that bucket” rule, keeps a 400-iteration cap, and changes the neighbourhoods to:

```python
shift_sets = [
    (-28, -14, 14, 28),
    (-14, -7, 7, 14),
    (-7, -3, 3, 7),
    (-3, -1, 1, 3),
]
max_iters = 400
```

That run reached min 18 and standard deviation **1.391860** after 319 accepted moves. Relative to the default, the floor is the same and the timeline is about 1.6 percent smoother. It is also smoother than the 1.405740 keep-gate that was used to judge the annealing work. In other words, a better neighbourhood on the original hill-climber beat the smoothness target that annealing was asked to clear.

If you want something simpler that still beats the default, this ladder of ordinary plus-or-minus pairs is the next best:

```python
shift_sets = [(-28, 28), (-21, 21), (-14, 14), (-7, 7), (-3, 3), (-1, 1)]
```

That one finished at std 1.396502. A cheap, almost-default upgrade is just to put a 42-day jump in front of the current ladder. That reaches 1.404311 in 20 seconds.

## What I actually varied

I started by reproducing the published run, then walked through the knobs one family at a time.

1. **Iteration budget.** Same default neighbourhoods, caps of 5, 10, 20, 40, 80, 160, 400, and 800.
2. **A single jump size.** Only ±1, then ±2, ±3, ±5, ±7, ±10, ±14, ±21, ±28, ±35, ±42, ±56, and ±70. This asks whether variable neighbourhoods are doing any work, or whether one well-chosen step would do.
3. **Different VNS ladders.** Wider first steps, finer last steps, geometric sizes, two-level and three-level shortcuts, and a denser weekly ladder.
4. **Order.** The same sizes tried small-first, interleaved, or wide-then-tiny.
5. **Richer neighbourhoods.** Extra offsets inside each level, one giant union of every offset, and left- or right-heavy asymmetric sets.
6. **Selection policy.** The current first-priority-level exit, versus picking the best improving move across every priority level, versus taking the first improving move found.
7. **A refine pass.** The six best distinct settings were rerun at 80, 200, and 800 iterations, and again with all-levels selection, to see whether extra budget or a wider look would push them further.

I did not invent a new objective. Ranking is the same lexicographic rule the optimiser already uses: raise the worst day first, then smooth the series, then raise the mean. Because the mean never moved, every comparison after “did we hold 18?” is a smoothness comparison.

## The default is honest, and it needs more than 160 moves

The baseline with

```text
(-28, 28), (-14, 14), (-7, 7), (-3, 3)
```

and `max_iters=400` accepted 280 moves and stopped because nothing else improved. Score: min 18, std 1.413971, mean 21.713. That matches the published Iteration 1 hill-climb. Raising the cap to 800 did nothing. The search is already finished at 280.

Cutting the budget is where the default falls apart.

| Iteration cap | Minimum | Std   | What happened |
| ---: | ---: | ---: | --- |
| 5 | 16 | 1.873 | Barely off the sheet |
| 10 | 17 | 1.810 | Hits 17 immediately |
| 20 | 17 | 1.758 | Still climbing inside 17 |
| 40 | 17 | 1.675 | |
| 80 | 17 | 1.569 | |
| 160 | 17 | 1.468 | Close, but still not 18 |
| 400 | 18 | 1.414 | Natural stop at move 280 |
| 800 | 18 | 1.414 | Same schedule as 400 |

So the printed default of 400 is not magic. It is just comfortably above the 280 moves this workbook actually uses. If someone “speeds the algorithm up” by dropping `max_iters` to 200 on the default ladder, they should expect to lose the floor.

The same pattern showed up later on the better ladders. Several of them still sat at min 17 after 200 moves and only reached 18 in the 260–350 move range. A 400 cap is enough. An 80 or 200 cap is not, even on the winning neighbourhoods.

## One jump size is not a substitute for a ladder

This was the most useful negative result. If you only allow one pair of shifts, most sizes never reach min 18.

±5, ±7, and ±14 were the only single neighbourhoods that got the floor to 18. The best of those, ±7, stopped at std 1.471. That is a long way behind the default ladder’s 1.414. A variable neighbourhood is doing real work. It is not just extra code around a 7-day nudge.

Two surprises sat in the middle of that sweep. ±10, which looks like a reasonable “about a week and a bit” step, stalled at min 17. ±3, which is the last rung of the default ladder, also stalled at 17 even after 400 grinding little moves. Tiny steps can polish a schedule that is already at 18. They cannot get you there from the raw forecast. At the other end, ±56 almost did nothing useful (min 16, 28 moves) and ±70 barely moved at all (min 15, two moves). Those jumps are so large that the rule rebuild usually refuses them.

That is why the default order — large first, then smaller — exists. The large rungs lift the floor. The small rungs tidy the standard deviation afterwards.

## Order matters more than people might expect

When I reversed the default ladder and tried small steps first, the search never reached min 18. It spent its 400 iterations taking the same kind of tiny improving moves that ±3 alone would take, and it died at min 17, std 1.590. Small-first on a weekly ladder was even worse: min 17, std 1.765, which is essentially the ±1-only result.

An interleaved order, starting at ±14 then jumping to ±28 then down to ±3 and ±7, still reached 18 and even beat the default slightly (std 1.408). Starting with ±42 and immediately dropping to ±1 did not: it got stuck at 17.

The lesson I would actually keep is simple. Try the bigger legal jumps first. Do not “be conservative” and start with a day or two. On this workbook that conservatism costs you the availability floor.

## Adding rungs beats widening a single rung

Once the large-first order was locked, the next question was which sizes to put on the ladder.

The coarse ladder of only ±70, ±42, and ±28 never reached 18. Two-level shortcuts reached 18 but left a bumpier series (std 1.437 for ±28 then ±7). Adding a one-day last step to the default, or a 42-day first step, both beat the published settings. The geometric ladder ±32 / ±16 / ±8 / ±4 / ±2 was already better than default (1.404470). Putting ±1 on the end of that geometric ladder improved it again (1.399695).

The best ordinary plus-or-minus ladder was the dense weekly one:

```text
±28, ±21, ±14, ±7, ±3, ±1
```

at std 1.396502. Filling the gaps between the default rungs helps. The search no longer has to jump from a fortnight to a week to three days with nothing in between.

A very wide dense ladder that also included ±56 and ±42 was a little worse than that (1.402084) but much faster on the first pass, 29 seconds instead of 83. If runtime matters more than the last 0.005 of standard deviation, that is the practical pick.

## The winner was not a new size. It was extra offsets on each rung

`generate_neighbors` does not have to be called with a pair. It will try every integer in the tuple. The default only ever tries “exactly k days earlier or later.” I also tried giving each VNS level its half-step as well:

```text
level 28:  -28, -14, +14, +28
level 14:  -14,  -7,  +7, +14
level 7:    -7,  -3,  +3,  +7
level 3:    -3,  -1,  +1,  +3
```

That is the winner: min 18, std **1.391860**, 319 moves, about 96 seconds. The last successful neighbourhood was the smallest one, which is what you want. The big rungs did the lifting, then the half-steps finished the polish.

Dumping every offset into one giant union was worse, not better. `(-28, -14, -7, -3, 3, 7, 14, 28)` as a single neighbourhood came back at 1.413656, almost exactly the default. A denser union including ±21 and ±1 reached 1.406534, better than default and still behind the layered version. The layering is load-bearing. If every offset is available at once, the search grabs the lexicographically best move from the whole set and never gets the “try a big move, then a medium one, then a small one” discipline that VNS is there for.

Asymmetric sets (more left than right, or the other way around) did not help. Right-heavy was roughly default. Left-heavy was a bit worse.

## The current selection rule is the right one

The live algorithm does not consider every improving neighbour in the fleet. It walks priority levels from the worst availability days, and as soon as one level has any improving move, it returns that bucket and takes the best move in it. I compared that with two alternatives on the default ladder.

Looking across every priority level and taking the global best improving move was slightly worse (std 1.415233) and more than four times slower. Taking the first improving move found was worse again (1.421370). When I later forced all-levels selection onto the winning neighbourhoods, they all lost a little smoothness. The winner went from 1.391860 to 1.403198.

That surprised me less after I thought about it. The objective cares about the worst day first. Restricting attention to events that sit on the worst days is not a speed hack that happens to work. It is aligned with the score. Letting a smoother move on a comfortable day beat a floor-relevant move is how you spend runtime without gaining the thing you said you wanted.

I would not change the selection policy.

## What did not happen

Nobody reached min 19. Forty-six of the 74 trials held the floor at 18. Twenty-five finished at 17, two at 16, and the ±70-only run stayed at 15. Every schedule was rule-valid. Mean availability was identical in every trial.

Raising `max_iters` past the natural stop never found a hidden extra move. The refine pass at 800 iterations reproduced the first-pass scores of those configs. It did not improve them.

I also would not read this as “annealing is pointless.” This study only retuned the hill-climber. It says the neighbourhood the hill-climber was using was leaving smoothness on the table. It does not say a later escape-and-polish method cannot find min 19 from this new, smoother 18. If that experiment happens, it should warm-start from this winner, not from the old default.

## What I would actually ship

Use the half-step VNS ladder above, keep `max_iters=400`, and keep first-priority-level selection. On this workbook that is the best lexicographic score I measured.

If 96 seconds is too slow for interactive use, use the dense ±k ladder or the “add ±42 in front of the default” ladder. Both beat the published default and still finish in half a minute or less.

Do not start with small steps. Do not collapse the ladder into one union of every offset. Do not cut the iteration cap to 200 and assume you will still get min 18.

The raw trial table is in `hyperparameter-results.json` in this folder. The study can be repeated with:

```bash
python .scratch/priority-based-selection/run_hyperparameter_study.py
```

It skips names it has already written, so a rerun will not throw the 52 minutes away.
