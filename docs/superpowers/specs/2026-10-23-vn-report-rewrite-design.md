# VN report concise rewrite

## Goal

Rewrite `vn-hyperparameter-analysis2.docx` as a natural, self-contained report that reads as the first presentation of the analysis. Target approximately two A4 pages.

## Audience and tone

Write for a project stakeholder who needs the decision and supporting evidence without the full experiment history. Use plain English, short paragraphs, and direct claims. Do not refer to earlier studies, follow-up work, the report date, the user's recollection, cloud agents, or later adoption of a setting.

## Content

Use this structure:

1. Recommendation
2. What was tested
3. Best result for each forecast
4. What the results show
5. Limitations and next step

Retain:

- the recommendation of the ±56, ±42, ±28, ±14, ±7, ±3, ±1 ladder at 400 iterations;
- the baseline definition of ±28, ±14, ±7, ±3, ±1;
- one compact table containing the best setting for each forecast;
- the key comparison between the recommendation and baseline;
- the findings that large steps help, coarse-to-fine order matters, and 400 iterations is sufficient;
- the material limitations: three related forecasts, deterministic runs, small differences between leading strategies, no global-optimum claim, and operational scenarios not enforced.

Remove:

- the complete 13-strategy table;
- references to previous studies or reruns;
- SHA256 and reproducibility details;
- cloud-machine and comparative timing details;
- the runtime chart;
- secondary strategy comparisons that do not affect the recommendation;
- repeated numerical evidence.

The detailed results remain available in `summary2.xlsx`.

## Implementation and verification

Update the report builder so the document can be reproduced, then regenerate the existing `vn-hyperparameter-analysis2.docx`. Keep the evidence checks that protect factual claims. Verify the output is two A4 pages in Microsoft Word, inspect the rendered pages for layout problems, scan the document for prohibited historical wording, and run the VN analysis tests.
