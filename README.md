# flourishing-mi-sim

Public release workspace for the MI counseling-agent simulation study.

This repository contains the self-play simulation package, the authoritative
Japanese script corpus used for expert ratings, public script mapping metadata,
the frozen English SAP materials, anonymized analysis datasets, analysis code,
executed model outputs, and run logs.

## Language and Authority

The study analyzed and rated Japanese counseling scripts. The machine-readable
CSV files under `data/counseling_scripts/scripts/` are the authoritative rating
materials. The English transcript rendering under
`data/counseling_scripts/english_renderings/` is only a nonauthoritative
orientation aid and should not be treated as the rated source material.

## Repository Map

- `src/mi_sim/`: public Python package for running self-play simulations.
- `src/mi_sim/config/`: model settings, client profiles, prompt rules, rubrics,
  and Layer3/Layer4 action-prompt configuration.
- `data/counseling_scripts/scripts/`: 60 generated Japanese counseling scripts.
- `data/counseling_scripts/english_renderings/`: nonauthoritative English
  transcript rendering for orientation only.
- `data/script_inventory/`: public script inventory, data dictionary, and
  behavior-code rules.
- `SAP/`: English SAP v3.7 and public appendices.
- `analysis_steps/`: executed Python/R analysis code for SAP v3.7.
- `results/sap_v3_7/`: anonymized analysis datasets, validation outputs,
  model tables, sensitivity analyses, analysis report, and run logs.
- `docs/reproducibility_crosswalk.md`: stage-by-stage map from study procedure
  to files in this repository.
- `RELEASE_MANIFEST.md`: release inventory and known exclusions.
- `LICENSE.md`: license terms for this public release.

## Installation

Python 3.11+ and an OpenAI API key are required to run new simulations.

```bash
python -m pip install -e .
```

Create a `.env` file based on `.env.example` and set at least
`OPENAI_API_KEY`.

```bash
cp .env.example .env
```

## Run Self-Play Simulations

Run a single self-play session:

```bash
mi-sim self-play --max-turns 5
```

Run all 15 public client profiles in a batch:

```bash
mi-sim self-play --all-cases --max-turns 8
```

By default, new simulation outputs are written to `logs/mi_sim/` under the
current working directory. Local logs are intentionally ignored by git.

## Inspect or Rerun Analyses

The public analysis outputs are under `results/sap_v3_7/`. The executed analysis
scripts are under `analysis_steps/`.

The Python builder `analysis_steps/01_run_sap_v3_7_analysis.py` documents the
full executed pipeline from the internal source workbook to public analysis
datasets and reports. The internal workbook is not released because it contains
nonpublic file links and direct evaluator-name columns.

The R model script can be rerun against the included public analysis datasets:

```bash
Rscript analysis_steps/sap_v3_7_models.R results/sap_v3_7
```

## Public Scope

Included:

- Authoritative Japanese scripts and public script inventory.
- Nonauthoritative English transcript rendering for reader orientation.
- Model settings, prompts, client profiles, phase-slot rubrics, and Layer3/Layer4
  prompt configuration.
- Anonymized rater-level analysis datasets and adjudication flags.
- English SAP v3.7, analysis code, result tables, and logs.

Excluded:

- API keys, `.env`, and local run logs.
- Internal source workbooks with evaluator names or nonpublic file links.
- Audio recordings, TTS cache files, and Python cache files.
