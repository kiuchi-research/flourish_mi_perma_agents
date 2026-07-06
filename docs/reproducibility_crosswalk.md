# Reproducibility Crosswalk

This document maps the study stages to public files in this repository.

## Stage-To-File Map

| Study stage | Public files |
| --- | --- |
| Model selection and runtime settings | `src/mi_sim/config/model_settings.yaml` |
| Client profiles and case definitions | `src/mi_sim/config/client_profiles.yaml`; `src/mi_sim/config/client_prompt_rules.md` |
| MI knowledge and counselor guidance | `src/mi_sim/config/mi_knowledge.md`; `src/mi_sim/mi_prompt_knowledge.py` |
| Phase-slot quality rubrics | `src/mi_sim/config/phase_slot_quality_rubrics.yaml` |
| Layer3/Layer4 action prompts | `src/mi_sim/config/layer3_layer4_action_prompts.yaml`; embedded prompt assembly in `src/mi_sim/mi_counselor_agent.py` |
| Self-play simulation engine | `src/mi_sim/cli.py`; `src/mi_sim/self_play_batch.py`; `src/mi_sim/conversation_environment.py`; `src/mi_sim/perma_client_agent.py`; `src/mi_sim/mi_counselor_agent.py` |
| LLM client adapters | `src/mi_sim/openai_llm.py`; `src/mi_sim/client_llm_loader.py`; `src/mi_sim/counselor_llm_loader.py` |
| Authoritative Japanese rating scripts | `data/counseling_scripts/scripts/*.csv` |
| Nonauthoritative English orientation rendering | `data/counseling_scripts/english_renderings/generated_dialogue_scripts_english_rendering_v1.0.md` |
| Script-to-design mapping | `data/script_inventory/analysis_script_list_v1.0.csv` |
| Data dictionary | `data/script_inventory/data_dictionary_v1.0.csv` |
| Behavior-code rules | `data/script_inventory/behavior_coding_rules_v1.0.md` |
| SAP and analysis plan | `SAP/SAP_v3.7_en.md` |
| Dataset construction and reliability/descriptive pipeline | `analysis_steps/01_run_sap_v3_7_analysis.py` |
| Ordinal, mixed, exploratory, and sensitivity models | `analysis_steps/sap_v3_7_models.R` |
| Public rater-level analysis datasets | `results/sap_v3_7/01_analysis_datasets/` |
| Validation logs and run metadata | `results/sap_v3_7/00_logs/`; `results/sap_v3_7/02_validation/` |
| Primary model outputs | `results/sap_v3_7/07_primary_models/primary_layer_effects.csv` |
| Secondary, exploratory, and sensitivity outputs | `results/sap_v3_7/08_secondary_models/`; `results/sap_v3_7/09_exploratory/`; `results/sap_v3_7/10_sensitivity/` |
| Human-readable executed analysis report | `results/sap_v3_7/11_report/sap_v3_7_analysis_report.md` |

## Nonpublic Source Materials

The internal source workbook and direct evaluator-name mapping are not included.
They contain nonpublic file links and direct evaluator-name columns. Public
verification should use:

- the authoritative Japanese scripts in `data/counseling_scripts/scripts/`;
- the public script inventory in `data/script_inventory/`;
- the anonymized rater-level datasets in `results/sap_v3_7/01_analysis_datasets/`;
- the executed code and result tables listed above.

## Analysis Dataset Notes

Rater IDs are anonymized as `rater_1` to `rater_4`. The public release does not
include the mapping from these IDs to personal names.

The internal base export with direct identifiers is intentionally omitted. It
was an intermediate internal workbook export containing nonpublic file links and
nonpublic fields; it is not required for interpreting the public result tables.
