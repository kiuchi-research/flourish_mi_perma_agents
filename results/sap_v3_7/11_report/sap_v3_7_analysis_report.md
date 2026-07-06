# SAP v3.7 Analysis Report

Created at: 2026-06-06T10:55:28

## Inputs and Fixed Decisions

- Input data: nonpublic source workbook
- Layer mapping: `draft_response_text` was treated as Layer3, and `text` was treated as Layer4.
- Analysis values: for outcomes with initial ICC(2,k) below 0.50, the post-re-rating/adjudicated values in the nonpublic source workbook were used; that is, current rating columns rather than `rater_*_initial_*` columns.
- Existing Layer-specific result files were not used for model selection or adjudication decisions.

## Data Validation

| check | passed | detail |
| --- | --- | --- |
| script_id_count | True | 60 |
| pair_id_count | True | 30 |
| each_pair_has_layer3_layer4 | True | violations=0 |
| global_rating_rows | True | 1200 |
| global_rating_range | True | 1.0-5.0 |
| global_rating_half_steps | True | 0.5-step values |
| client_naturalness_rows | True | 240 |
| client_naturalness_range | True | 1-10 |
| behavior_pair_rows | True | 30 |
| behavior_nonnegative_integer | True | nonnegative integers |
| presentation_order_large_imbalance | True | max_within=9.267; overall_diff=2.150 |

## Initial and Analysis-Value Reliability

| timing | metric | n_cases | n_raters | ICC_A_1_absolute_single | ICC_A_k_absolute_average | krippendorff_alpha | mean_within_case_sd | mean_rating |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| initial | CCT | 60 | 4 | 0.067 | 0.223 | 0.002 | 0.732 | 3.515 |
| initial | SST | 60 | 4 | 0.004 | 0.017 | -0.154 | 0.898 | 3.758 |
| initial | PAR | 60 | 4 | 0.002 | 0.009 | -0.028 | 0.616 | 3.523 |
| initial | EMP | 60 | 4 | 0.016 | 0.061 | -0.094 | 0.740 | 3.123 |
| initial | overall_counselor_rating | 60 | 4 | 0.050 | 0.174 | 0.008 | 0.520 | 3.373 |
| initial | client_naturalness | 60 | 4 | 0.010 | 0.040 | -0.129 | 1.841 | 4.575 |
| analysis | CCT | 60 | 4 | 0.342 | 0.675 | 0.309 | 0.446 | 3.604 |
| analysis | SST | 60 | 4 | 0.280 | 0.608 | 0.211 | 0.503 | 3.750 |
| analysis | PAR | 60 | 4 | 0.223 | 0.535 | 0.199 | 0.434 | 3.517 |
| analysis | EMP | 60 | 4 | 0.219 | 0.529 | 0.184 | 0.430 | 3.252 |
| analysis | overall_counselor_rating | 60 | 4 | 0.187 | 0.479 | 0.150 | 0.423 | 3.373 |
| analysis | client_naturalness | 60 | 4 | 0.238 | 0.556 | 0.154 | 1.194 | 4.658 |
| analysis | technical_global | 60 | 4 | 0.319 | 0.652 | 0.265 | 0.443 | 3.677 |
| analysis | relational_global | 60 | 4 | 0.226 | 0.539 | 0.193 | 0.391 | 3.384 |

## Hypothesis 1: Descriptive Comparison With Prior Reference Values

| outcome | reference | n_scripts | layer3_mean | layer3_sd | bootstrap_ci_low | bootstrap_ci_high | reference_mean | difference_layer3_minus_reference | point_estimate_exceeds_reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CCT | GPT-SMDP | 30 | 3.579 | 0.448 | 3.417 | 3.733 | 3.410 | 0.169 | True |
| CCT | Opus-SMDP | 30 | 3.579 | 0.448 | 3.417 | 3.733 | 3.440 | 0.139 | True |
| SST | GPT-SMDP | 30 | 3.704 | 0.389 | 3.567 | 3.842 | 3.220 | 0.484 | True |
| SST | Opus-SMDP | 30 | 3.704 | 0.389 | 3.567 | 3.842 | 3.380 | 0.324 | True |
| PAR | GPT-SMDP | 30 | 3.513 | 0.379 | 3.383 | 3.650 | 3.200 | 0.312 | True |
| PAR | Opus-SMDP | 30 | 3.513 | 0.379 | 3.383 | 3.650 | 2.990 | 0.522 | True |
| EMP | GPT-SMDP | 30 | 3.225 | 0.376 | 3.096 | 3.358 | 3.120 | 0.105 | True |
| EMP | Opus-SMDP | 30 | 3.225 | 0.376 | 3.096 | 3.358 | 3.220 | 0.005 | True |
| overall_counselor_rating | GPT-SMDP | 30 | 3.379 | 0.340 | 3.258 | 3.496 | 3.220 | 0.159 | True |
| overall_counselor_rating | Opus-SMDP | 30 | 3.379 | 0.340 | 3.258 | 3.496 | 3.280 | 0.099 | True |

## Hypothesis 2: Layer Effects for Primary Outcomes

| outcome | n | engine | fallback_step | OR | CI_low | CI_high | CI_method | p_value | holm_p | model_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CCT | 240 | clmm | 1 | 1.273 | 0.603 | 2.686 | profile_likelihood | 0.528 | 1 | ok |
| SST | 240 | clmm | 1 | 1.764 | 0.705 | 4.419 | profile_likelihood | 0.229 | 1 | ok |
| PAR | 240 | clmm | 1 | 1.111 | 0.626 | 1.972 | profile_likelihood | 0.719 | 1 | ok |
| EMP | 240 | clmm | 1 | 1.429 | 0.776 | 2.629 | profile_likelihood | 0.256 | 1 | ok |
| overall_counselor_rating | 240 | clmm | 1 | 0.974 | 0.545 | 1.741 | profile_likelihood | 0.930 | 1 | ok |

## Hypotheses 3 and 4: Situation and PERMA Profile Main Effects

These analyses correspond to manuscript Hypothesis 3, the situation main effect, and Hypothesis 4, the PERMA profile main effect. The results were written to `09_exploratory/global_situation_perma_effects.csv`, but were omitted from the previous report body.

The model was `rating_ord ~ layer + situation + perma_profile + rater_id + (1 | script_id)`. Each main effect was evaluated by a likelihood-ratio test against a reduced model omitting the corresponding factor. Multiplicity was handled using Holm correction within the five situation-effect outcomes and within the five PERMA-profile-effect outcomes.

| outcome | effect | n | p_value | Holm-adjusted p-value | model_status |
| --- | --- | --- | --- | --- | --- |
| CCT | situation | 240 | 0.275 | 1.000 | ok_or_warning |
| SST | situation | 240 | 0.367 | 1.000 | ok_or_warning |
| PAR | situation | 240 | 0.020 | 0.099 | ok_or_warning |
| EMP | situation | 240 | 0.509 | 1.000 | ok_or_warning |
| overall_counselor_rating | situation | 240 | 0.799 | 1.000 | ok_or_warning |
| CCT | perma_profile | 240 | 0.616 | 1.000 | ok_or_warning |
| SST | perma_profile | 240 | 0.499 | 1.000 | ok_or_warning |
| PAR | perma_profile | 240 | 0.130 | 0.649 | ok_or_warning |
| EMP | perma_profile | 240 | 0.479 | 1.000 | ok_or_warning |
| overall_counselor_rating | perma_profile | 240 | 0.905 | 1.000 | ok_or_warning |

For the situation main effect, only PAR had an unadjusted p value of 0.020, but its Holm-adjusted p value was 0.099, so it was not treated as a significant main effect under the SAP criterion. All PERMA profile main effects had Holm-adjusted p values of at least 0.05. Therefore, the analyses corresponding to Hypotheses 3 and 4 did not detect a clear main effect of situation or PERMA profile.

## Secondary Analysis: Good-Threshold Achievement

| outcome | n | engine | OR | CI_low | CI_high | p_value | holm_p | model_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| good_technical_global | 240 | glmer | 1.355 | 0.575 | 3.194 | 0.487 | 0.975 | ok |
| good_relational_global | 240 | glmer | 0.928 | 0.435 | 1.980 | 0.847 | 0.975 | ok |

## Exploratory Analyses

### Client Naturalness

| analysis | n | interaction_p_value_ml_lrt | source_layer_beta | model_status | warnings | variance_summary |
| --- | --- | --- | --- | --- | --- | --- |
| client_naturalness_context_lmm | 240 | 0.095 | 0.135 | ok_or_warning |  |  Groups           Name        Std.Dev. |  source_script_id (Intercept) 0.46386  |  pair_id          (Intercept) 0.61435  |  Residual                     0.88324  |

### Behavior-Code Models

| summary | n | engine | interaction_p_value | model_status | poisson_aic | negbin_aic |
| --- | --- | --- | --- | --- | --- | --- |
| Q | 30 | poisson_primary | 0.956 | ok_or_warning | 161.605 | 163.605 |
| total_reflection | 30 | poisson_primary | 0.935 | ok_or_warning | 186.455 | 188.455 |
| pct_complex_reflection | 30 | lm_supplement | 0.001 | ok_or_warning |  |  |
| reflection_question_ratio | 30 | lm_supplement | 0.050 | ok_or_warning |  |  |
| Total_MI_Adherent | 30 | poisson_primary | 0.969 | ok_or_warning | 168.354 | 170.354 |
| Total_MI_Non_Adherent | 30 | poisson_primary | 1.000 | ok_or_warning | 30.000 |  |

## Script-Level Aggregate Sensitivity Analysis

| outcome | n_pairs | mean_pair_diff_layer4_minus_layer3 | sd_pair_diff | median_pair_diff | min_pair_diff | max_pair_diff | n_pair_diff_positive | n_pair_diff_zero | n_pair_diff_negative |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CCT | 30 | 0.050 | 0.467 | 0.062 | -1.000 | 0.875 | 15 | 1 | 14 |
| SST | 30 | 0.092 | 0.512 | 0.000 | -0.750 | 1.000 | 14 | 5 | 11 |
| PAR | 30 | 0.008 | 0.394 | 0.000 | -1.000 | 0.875 | 13 | 4 | 13 |
| EMP | 30 | 0.054 | 0.381 | 0.125 | -0.750 | 0.750 | 16 | 3 | 11 |
| overall_counselor_rating | 30 | -0.013 | 0.372 | 0.000 | -1.000 | 0.625 | 14 | 6 | 10 |

## Notes

- No binary success/failure or supported/unsupported judgment is made for Hypothesis 2 as a whole.
- Behavior codes are summaries of system action labels derived from Layer2, not MITI behavior counts assigned by human coders.
- The `source_layer` term for client naturalness is a contextual adjustment/descriptive variable and should not be interpreted as a confirmatory Layer effect on counselor quality.
