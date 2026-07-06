# Release Manifest

Release stage: public repository preparation  
Prepared from working repository state: 2026-06-10

## Included Materials

- Self-play simulation package: `src/mi_sim/`
- Model and prompt configuration: `src/mi_sim/config/`
- Authoritative Japanese counseling scripts: 60 CSV files in
  `data/counseling_scripts/scripts/`
- Nonauthoritative English transcript rendering for orientation only:
  `data/counseling_scripts/english_renderings/generated_dialogue_scripts_english_rendering_v1.0.md`
- Public script inventory and metadata: `data/script_inventory/`
- English SAP and public appendices: `SAP/`
- Analysis code: `analysis_steps/`
- Public SAP v3.7 outputs and logs: `results/sap_v3_7/`
- File-stage crosswalk: `docs/reproducibility_crosswalk.md`

## Intentionally Excluded

- `.env` files and API keys
- Internal source workbooks used during preparation
- Direct evaluator-name mapping files
- Nonpublic source-file links
- Audio recordings and TTS cache files
- Python caches and local run logs

## Notes

The rater-level analysis datasets use anonymized rater IDs such as `rater_1` to
`rater_4`. The mapping from anonymized rater IDs to individual names is not
included in this release.

The internal base export with direct identifiers was not copied from the
working analysis outputs because it contains nonpublic source-file links and
nonpublic workbook-derived fields.

Raw counselor/client free-text evaluation memo fields are not included in this
release. If memo-derived descriptive material is shared later, it should be
released as an English translated/derived public artifact rather than as raw
Japanese workbook text.
