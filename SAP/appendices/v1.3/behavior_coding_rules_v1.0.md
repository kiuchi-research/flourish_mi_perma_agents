# Behavior Coding Extraction and Aggregation Rules v1.0

This document defines the public-release rule set for extracting counselor behavior codes from the simulation outputs.

## Scope

- Unit of extraction: counselor turns.
- Primary source field: `main_action` recorded in the simulation log metadata.
- Primary implementation references:
  - `simulation_code/app/mi_counselor_agent.py`
  - `simulation_code/app/session_log_tools.py`
  - `simulation_code/DsPy/mi_dspy_programs.py`
  - `simulation_code/DsPy/mi_dspy_metrics.py`

The behavior codes are system-derived codes, not independent human MITI behavior counts.

## Raw Action Labels

The current counselor action labels are:

- `REFLECT`
- `REFLECT_SIMPLE`
- `REFLECT_COMPLEX`
- `REFLECT_DOUBLE`
- `QUESTION`
- `SCALING_QUESTION`
- `CLARIFY_PREFERENCE`
- `SUMMARY`
- `ASK_PERMISSION_TO_SHARE_INFO`
- `PROVIDE_INFO`

Raw counts for these labels should be retained whenever simulation logs are available.

## SAP Behavior Summary Mapping

For SAP v1.3 behavior summaries, use the following deterministic mapping unless a later frozen appendix supersedes it before behavior analyses begin.

| SAP variable | Source action labels | Rule |
|---|---|---|
| `Q` | `QUESTION`, `SCALING_QUESTION`, `CLARIFY_PREFERENCE` | Count as question-like counselor actions. |
| `SR` | `REFLECT_SIMPLE` | Count as simple reflections. |
| `CR` | `REFLECT`, `REFLECT_COMPLEX`, `REFLECT_DOUBLE` | Count as complex or enriched reflections. |
| `GI` | `PROVIDE_INFO` | Count as information sharing. |
| `Seek` | `ASK_PERMISSION_TO_SHARE_INFO` | Count as seeking collaboration / permission before information sharing. |
| `AF` | explicit affirmation mode or affirmation metadata when available | If no affirmation metadata is available, report as not extractable from `main_action` alone. |
| `Persuade`, `Persuade_with_Permission`, `Emphasize`, `Confront` | no direct `main_action` equivalent in the current public snapshot | Report as not extractable unless a frozen extraction field is added before analysis. |

`SUMMARY` is retained as a raw action count. For MITI-style SR/CR summaries, `SUMMARY` must not be silently forced into SR or CR unless a documented, frozen classification rule is added before behavior analyses begin.

## Derived Scores

Use these formulas:

```text
total_reflection = SR + CR
pct_complex_reflection = CR / (SR + CR)
reflection_question_ratio = (SR + CR) / Q
good_pct_complex_reflection = 1 if pct_complex_reflection >= 0.50 else 0
good_reflection_question_ratio = 1 if reflection_question_ratio >= 2.00 else 0
```

## Zero-Division Rules

- If `total_reflection = 0`, `pct_complex_reflection` is missing for continuous summaries and `good_pct_complex_reflection = 0`.
- If `Q = 0` and `total_reflection > 0`, `reflection_question_ratio` is infinite; exclude it from mean/SD summaries and count it separately. For the descriptive Good indicator, set `good_reflection_question_ratio = 1`.
- If `Q = 0` and `total_reflection = 0`, `reflection_question_ratio` is missing and `good_reflection_question_ratio = 0`.

## Layer Handling

Behavior codes are treated as pair-level data when they are determined before the Layer4 final-writing step. The analysis dataset should contain one row per `pair_id`. If both 3Layer and 4Layer rows exist for a pair, values must be identical; otherwise, the source data should be checked before analysis.

## Reporting Limits

These behavior variables are exploratory and descriptive. They should not be interpreted as standard MITI human-coded behavior counts unless independently coded and validated by human coders.
