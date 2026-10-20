# Priority based selection extensive hyperparameter analysis

Status: ready-for-agent

Create a Word report for the deterministic priority based selection optimiser.
Audit the existing 74-trial study, reproduce the production default, validate
the leading settings, and extend the analysis with selection interactions,
neighbourhood ablations, ordering, and controlled feasible start schedules.
Keep production code, maintenance rules, and source workbooks unchanged.
Use a fixed forecast horizon, lexicographic scores, full rule replay, and
fresh independent availability calculation for validation. Preserve raw
results, traces, source hashes, and recommended schedules locally.
Report distinct settings separately from repeats. Timings use three serial
repetitions for finalists. Start variants are sensitivity tests of the same
forecast, not independent datasets or random search seeds.
