# Iteration 2 remaining work

Status: ready-for-agent

## Problem Statement

Semester 2 set out to judge whether annealing beats the frozen baseline, and whether dummy operational limits can be added without breaking usable schedules. The search and the acceptance layer exist, and a hill-climb settings study already found better neighbourhoods than the published defaults. What is missing is a fair comparison, the operational limits, controlled start schedules, a short settings sweep, and a handover that says what to keep.

## Solution

Finish the remaining work against the heavy forecast, without changing the published baseline defaults.

Use the candidate method (basin-hopping with tabu polish) as the method under test, and classic SA only as an ablation that already exists. Let temperature accept a worse schedule early, including a lower worst-day availability, and always report the best-so-far. Also run tightened acceptance, which never lowers the worst day, as the fallback.

Compare like with like. The bar is the tuned baseline: the same hill-climb as the baseline, on the half-step neighbourhoods, not the published default neighbourhoods. Judge the candidate method by its typical result, the median of three fixed seeds, and never by its best seed.

Add three dummy constraint scenarios in a separate config. Busy periods, displacement limits, and dependency groups are hard rules for every method, at every temperature. The settings sweep and the start-schedule runs stay unconstrained. Cap the settings sweep at one hour. Write the keep-or-drop recommendation into a handover document.

## User Stories

1. As a fleet planner, I want a better move to always be kept, so that a clear improvement is never thrown away.
2. As a fleet planner, I want a worse move, including a lower worst-day availability, to be possible early in the candidate method and rare later, so that the search can leave a trap and then settle.
3. As a fleet planner, I want the reported schedule to be the best-so-far, so that a temporary worse schedule is not what I am given.
4. As a fleet planner, I want tightened acceptance available as a fallback, so that a move which lowers worst-day availability can be banned if temperature acceptance hurts the worst day.
5. As a fleet planner, I want every reported schedule to satisfy maintenance rules and non-overlap, so that the plan is usable.
6. As a researcher, I want the published baseline defaults left unchanged, so that the Iteration 1 result stays reproducible.
7. As a researcher, I want the tuned baseline to use the half-step neighbourhoods (28 with 14, then 14 with 7, then 7 with 3, then 3 with 1, either direction) and a 400-iteration cap, so that the bar is the best hill-climb already measured.
8. As a researcher, I want the candidate method judged on those same neighbourhoods, so that a gain is from how moves are accepted and not from a different neighbourhood.
9. As a researcher, I want the typical result to be the median of seeds 1, 2, and 3, with the spread reported beside it, so that a lucky seed cannot win the comparison.
10. As a researcher, I want the baseline and the tuned baseline run once, so that a deterministic result is not dressed up as a sample.
11. As a stakeholder, I want the candidate method kept only if its typical smoothness beats the tuned baseline by at least 0.005, every seed still has worst-day availability 18, and a typical run finishes within 5 minutes, so that the keep-or-drop rule is numeric.
12. As a stakeholder, I want the handover to recommend the tuned baseline settings, passed in by the caller, when that rule fails, so that we take the smoother hill-climb without editing the published defaults.
13. As a stakeholder, I want classic SA mentioned as an ablation that did not beat the baseline, so that it is not mistaken for the method under test.
14. As a fleet planner, I want operational limits supplied as dummy scenarios in their own config, so that the maintenance workbook stays the canonical forecast.
15. As a fleet planner, I want a busy period to demand a worst-day availability inside a date window, so that a known busy stretch is protected.
16. As a fleet planner, I want a displacement limit measured from the as-loaded start of each check, including moves that a rebuild causes, so that a check cannot drift arbitrarily far from the loaded plan.
17. As a fleet planner, I want a dependency group to require at least a stated number of its aircraft available on every day, so that aircraft that must operate together are not all in maintenance at once.
18. As a fleet planner, I want three scenarios, loose, medium, and tight, so that I can see the search cope and then fail as the limits get harder.
19. As a fleet planner, I want the loose scenario to use a 70-day displacement limit, the medium 42, and the tight 21, so that the three levels match the agreed gradient.
20. As a fleet planner, I want each scenario to name one or two busy periods over stretches that are already busy in the as-loaded schedule, so that the windows are realistic rather than arbitrary.
21. As a fleet planner, I want the loose and medium busy-period levels set so the as-loaded schedule already satisfies them, so that the search starts from a legal plan.
22. As a fleet planner, I want the tight scenario to be beyond the as-loaded schedule, so that we see the "constraints break feasibility" outcome without building a repair step.
23. As a fleet planner, I want two dependency groups of four aircraft, each requiring at least three available every day, named explicitly in the config, so that the groups are not inferred from the fleet sheet's other naming.
24. As a researcher, I want a move that breaks a busy period, a displacement limit, or a dependency group to be neither proposed nor accepted, for the baseline and the candidate method alike, so that annealing cannot bypass a hard rule while it is hot.
25. As a researcher, I want an as-loaded schedule that already breaks a scenario to be reported as infeasible, not repaired, so that the prototype stays a judge of the limits rather than a fixer of them.
26. As a researcher, I want constraint satisfaction reported separately from smoothness and worst-day availability, so that a smoother illegal plan cannot look like a win.
27. As a researcher, I want the settings sweep and the start-schedule comparison to run with no operational limits, so that those effects are not mixed with constraint effects.
28. As a researcher, I want the displacement limit, when constraints are on, to stay measured from the as-loaded plan even if the search started from a bunched or spread start schedule, so that the limit means one thing.
29. As a researcher, I want an as-loaded start schedule, a bunched one, and a spread one, all for the same checks and due dates, so that the start effect is separated from the method.
30. As a researcher, I want the bunched start to move each aircraft's first check, inside its start window, toward the median first-check date across the fleet, and then rebuild, so that the fleet's opening checks cluster.
31. As a researcher, I want the spread start to move that first check away from the same median, inside its start window, and then rebuild, so that the opening checks fan out.
32. As a researcher, I want each start schedule's own worst-day availability and smoothness reported before any search, so that a good start is visible on its own.
33. As a researcher, I want both the tuned baseline and the candidate method run from each start schedule, so that the comparison holds the start fixed.
34. As a researcher, I want the settings sweep to change one candidate-method setting at a time on the tuned neighbourhoods, so that a change has a single cause.
35. As a researcher, I want the decision runs to happen even if the sweep is cut short, so that the keep-or-drop call does not depend on the sweep finishing.
36. As a researcher, I want the sweep capped at one hour, screening a single seed in this order: escape temperature 1.0 and 2.0, escape cycles 8 and 25, plateau moves 15 and 45, polish iterations 200 and 800, so that the hour is spent on the settings most likely to matter.
37. As a researcher, I want a second seed only for the best sweep variant, and only if time remains, so that the hour is not spent repeating losers.
38. As a researcher, I want the earlier cloud settings study kept only as a footnote, so that results from a regenerated workbook are not compared with the canonical forecast.
39. As a stakeholder, I want a handover in Markdown and a Word document that states the measured worst-day availability, smoothness, and runtime, the keep-or-drop call, and the slide discrepancy on worse worst days, so that someone who was not in the experiments can see what was decided.
40. As a stakeholder, I want the handover to say that worst-day availability 19 is infeasible, so that later work does not spend itself hunting a floor the forecast cannot reach.
41. As a developer, I want new behaviour written test-first against small synthetic fleets, so that acceptance, limits, and start schedules can be checked without a heavy-forecast run.
42. As a developer, I want the existing baseline and annealing tests to keep passing, so that the finished search behaviour does not regress.
43. As a presenter, I want the deck left as it was given, so that manual edits in the live presentation are not overwritten.

## Implementation Decisions

- The published baseline defaults stay as they are. Callers pass the half-step neighbourhoods and the iteration cap in. Nothing in the baseline module is edited.
- The method under test is basin-hopping with tabu polish. Classic SA is not re-run for this study. The handover describes it as an existing ablation that stayed at the baseline smoothness.
- Acceptance for the candidate method stays temperature-based on the lexicographic score (worst-day availability, then smoothness, then average). A lower worst day can be accepted when the draw falls under the temperature curve. Tightened acceptance is a switch on that same function: if the candidate's worst-day availability is lower, reject it before the temperature draw.
- The schedule returned and compared is the best-so-far, not the schedule the search happens to be on at the end.
- Decision runs, outside the one-hour sweep: the tuned baseline once; the candidate method on the half-step neighbourhoods for seeds 1, 2, and 3; tightened acceptance for seeds 1, 2, and 3. A candidate run that exceeds 5 minutes fails the runtime criterion.
- Keep the candidate method only when all three hold: the median smoothness is at least 0.005 better than the tuned baseline, every seed has worst-day availability 18, and the typical run is within 5 minutes. Otherwise recommend the tuned baseline settings.
- Operational limits live in one config with three scenarios (loose, medium, tight). The maintenance workbook is not modified. Aircraft in the config use the maintenance-event names, not the fleet sheet's other names.
- Each scenario has: one or two busy periods (a date window and a required worst-day availability), one displacement limit in days (70, 42, and 21), and two dependency groups of four aircraft requiring at least three available on every day.
- Busy-period windows are chosen from stretches that are already busy in the as-loaded schedule. Loose and medium levels are set so the as-loaded schedule satisfies them. The tight scenario is set so the as-loaded schedule does not, and the result is reported as infeasible. There is no repair.
- A proposed move is legal only if the rebuilt schedule satisfies maintenance rules, non-overlap, and every limit in the active scenario. This filter applies to the baseline and the candidate method at every temperature. With no scenario active, only the maintenance rules apply.
- Displacement is the absolute day gap from that check's as-loaded start, after the rebuild. It is not measured from the start schedule.
- Start schedules are three schedules of the same checks and due dates. As-loaded is the loaded forecast. Bunched moves each aircraft's first check, inside its start window, toward the median of those first-check dates, then rebuilds. Spread moves it away from that median, then rebuilds. Each variant records its own worst-day availability and smoothness before search. Both methods then run from each variant, unconstrained.
- The settings sweep uses the tuned neighbourhoods, no operational limits, and seed 99, changing one of: escape temperature, escape cycles, plateau moves, polish iterations. It stops at 60 minutes even if the list is unfinished. The default point (temperature 1.5, 15 cycles, 30 plateau moves, 400 polish iterations) is the decision-run setting and is not repeated inside the hour. A second seed is used only for the best completed variant, and only with time left.
- The handover is a Markdown document and a Word document. It records the decision-run table, the sweep results that finished, the start-schedule comparison, the three constraint scenarios, the infeasibility of worst-day availability 19, the cloud-study footnote, and the difference from the deck's "never lower the worst day" slide. It does not invent numbers for runs that did not finish.

## Testing Decisions

- Test external behaviour on a small synthetic fleet: given a schedule and a scenario, is it legal; given two scores, a temperature, and a draw, is the move accepted; given a loaded fleet, do the bunched and spread start schedules keep the same checks and due dates and stay inside start windows.
- One seam. The existing annealing tests already call acceptance and neighbour generation directly on synthetic fleets, rather than running the heavy forecast. New tests use that same seam. Constraint checks and start-schedule construction are pure functions on a schedule, called the same way. The heavy-forecast decision runs, the sweep, and the start-schedule comparison are experiment runs checked by their written results, not by unit tests.
- A good test states a schedule, a limit, and the expected legal-or-not answer. It does not assert how the search walked there.
- Prior art is the existing acceptance tests: a scripted random draw, a score pair, and an assert on the accept-or-reject result. Constraint tests follow that shape. The baseline and annealing suites must still pass.

## Out of Scope

- Editing the published baseline module, including its default neighbourhoods.
- Editing the live execution-plan deck. The handover notes the slide difference instead.
- Treating classic SA as a method under test, or re-running it.
- Repairing a start schedule that breaks a scenario.
- Hunting worst-day availability 19. That floor is already shown to be infeasible.
- Regenerating the heavy forecast, or comparing against the cloud study's regenerated workbook.
- Repeating the hill-climb neighbourhood study. Its winning neighbourhoods are the tuned baseline.
- Real operational dates, groups, or limits from the sponsor. The scenarios are dummy data.
- A settings sweep longer than one hour, or a sweep that blocks the decision runs.

## Further Notes

- The loose 70-day displacement limit may change little. A check's start window already ends on its due date and starts 42 days earlier for an A check, or 70 days earlier for a B, C, or D check, so a 70-day leash from the as-loaded start often sits outside the window the rules already enforce. The medium (42) and tight (21) limits do bind. This was left at 70 / 42 / 21 because that gradient was agreed before the overlap was spelled out.
- Decision runs are not inside the one-hour cap. The cap is only the settings sweep.
- Commit at the end of each phase: fair comparison, constraints, start schedules, sweep, handover.
- Tests are written before the behaviour they cover.
- Domain words in this spec are defined in the project glossary. The acceptance decision is recorded as an architectural decision: temperature may lower the worst day, and tightened acceptance is the fallback.
