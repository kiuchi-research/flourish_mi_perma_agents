# Results

This directory contains the public SAP v3.7 analysis outputs.

## Directory Map

- `sap_v3_7/00_logs/`: run timestamps, package versions, R stdout/stderr, and
  run summary.
- `sap_v3_7/01_analysis_datasets/`: anonymized analysis datasets derived from
  the internal source workbook.
- `sap_v3_7/02_validation/`: validation summaries.
- `sap_v3_7/03_reliability/`: inter-rater reliability summaries.
- `sap_v3_7/04_adjudication/`: inferred adjudication/change flags.
- `sap_v3_7/05_descriptives/`: descriptive tables.
- `sap_v3_7/06_hypothesis1/`: prior-reference comparison.
- `sap_v3_7/07_primary_models/`: primary Layer-effect model outputs.
- `sap_v3_7/08_secondary_models/`: secondary model outputs.
- `sap_v3_7/09_exploratory/`: exploratory model outputs.
- `sap_v3_7/10_sensitivity/`: sensitivity-analysis outputs.
- `sap_v3_7/11_report/`: rendered analysis report.

## Exclusion

The internal base export with direct identifiers is not included because it
contains nonpublic file links and nonpublic workbook-derived fields. Use
`../data/script_inventory/analysis_script_list_v1.0.csv` for the public script
mapping.
