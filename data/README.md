# Data

This directory contains public data materials for the study.

## Authoritative Script Corpus

- `counseling_scripts/scripts/`: 60 Japanese counseling-script CSV files.

These CSV files are the authoritative materials rated by expert raters. They
should be used instead of English transcript renderings.

## English Orientation Rendering

- `counseling_scripts/english_renderings/generated_dialogue_scripts_english_rendering_v1.0.md`:
  nonauthoritative English rendering of the generated dialogue scripts.

The English rendering is provided only for reader orientation and auditability.
It was not rated and may contain line-break, spacing, blank-cell, or extraction
artifacts.

## Script Inventory And Metadata

- `script_inventory/analysis_script_list_v1.0.csv`: public blinded mapping from
  script IDs to design metadata and script files.
- `script_inventory/data_dictionary_v1.0.csv`: variable definitions for the
  public release and analysis datasets.
- `script_inventory/behavior_coding_rules_v1.0.md`: system-derived behavior-code
  extraction and aggregation rules.
- `script_inventory/appendix_manifest_v1.0.json`: checksum manifest for the
  script-inventory appendices.

## Analysis Datasets

The anonymized analysis datasets used for SAP v3.7 are stored in
`../results/sap_v3_7/01_analysis_datasets/`.

The internal source workbook is not included because it contains direct
evaluator-name columns and nonpublic file links.
