# Analysis Steps

This directory contains the executed SAP v3.7 analysis code.

- `01_run_sap_v3_7_analysis.py`: Python pipeline that built analysis datasets,
  validation summaries, reliability outputs, descriptive tables, adjudication
  flags, and the final Markdown report from the internal source workbook.
- `sap_v3_7_models.R`: R model script for primary, secondary, exploratory, and
  sensitivity models.

The Python script is retained for auditability. Its original input workbook is
not released because it contains nonpublic file links and direct evaluator-name
columns. The public derived datasets created by this script are included under
`../results/sap_v3_7/01_analysis_datasets/`.

The R model script can be rerun from the public repository root:

```bash
Rscript analysis_steps/sap_v3_7_models.R results/sap_v3_7
```

Rerunning this command writes model outputs and logs back into
`results/sap_v3_7/`.
