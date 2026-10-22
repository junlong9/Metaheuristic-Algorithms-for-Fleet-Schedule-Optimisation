# VN report comparison-focused rewrite

## Goal

Rewrite `vn-hyperparameter-analysis2.docx` as a natural, self-contained report that reads as the first presentation of the analysis. Target approximately three A4 pages and retain enough evidence to compare every tested shift method.

## Audience and tone

Write for a project stakeholder who needs the decision and supporting evidence without the experiment history. Use plain English, short paragraphs, and direct claims. Do not refer to earlier studies, follow-up work, the report date, the user's recollection, cloud agents, or later adoption of a setting.

## Content

Use this structure:

1. Recommendation
2. What was tested
3. Best result for each forecast
4. Comparison of all shift methods at 400 iterations
5. What the results show
6. Limitations and next step

Retain:

- the recommendation of the ±56, ±42, ±28, ±14, ±7, ±3, ±1 ladder at 400 iterations;
- the baseline definition of ±28, ±14, ±7, ±3, ±1;
- one compact table containing the best setting for each forecast;
- one complete table containing all 13 shift methods, with minimum availability and standard deviation for the Original, Moderate and Wide forecasts at 400 iterations;
- the variability-by-strategy graph, with minimum availability labelled on each point;
- the runtime-versus-standard-deviation graph;
- the key comparison between the recommendation and baseline;
- the findings that large steps help, coarse-to-fine order matters, and 400 iterations is sufficient;
- the material limitations: three related forecasts, deterministic runs, small differences between leading strategies, no global-optimum claim, and operational scenarios not enforced.

Exclude:

- references to previous studies or reruns;
- SHA256 and reproducibility details;
- cloud-machine and comparative timing details;
- repeated numerical evidence.

Use `minimum / SD` in the complete comparison table. Mark strategies that reached the 400-iteration limit, since those results may still improve with more passes. Keep the explanation focused on comparisons that affect the recommendation rather than narrating every table row. The detailed results remain available in `summary2.xlsx`.

## Implementation and verification

Update the report builder so the document can be reproduced, then regenerate the existing `vn-hyperparameter-analysis2.docx`. Keep the evidence checks that protect factual claims. Verify the output is three A4 pages in Microsoft Word, check that the sections, tables and figures are distributed readably across those pages, scan the document for prohibited historical wording, and run the VN analysis tests.
