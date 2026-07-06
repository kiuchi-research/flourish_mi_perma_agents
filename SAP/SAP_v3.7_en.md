# Statistical Analysis Plan (SAP) v3.7

**Study title**: Generation of motivational interviewing dialogues using a multilayered agent: a dialogue simulation study targeting flourishing-related issues among middle-aged single men in Japan
**Document type**: SAP (Statistical Analysis Plan)
**Version**: v3.7 preregistration-fixed version (incorporating inter-rater reliability decision rules and median-based re-evaluation rules)
**Date of first draft**: 2026-05-06
**Date of this version**: 2026-05-09
**Status**: This version is fixed as the SAP for preregistration after completion of rater-rating data collection and after the initial inter-rater reliability check, but before reviewing Layer-condition-specific summaries, Hypothesis 1 script-level summaries for the Layer3 condition, or primary analysis model estimates. This version clarifies the median-based re-evaluation and adjudication rules to be applied when the ICC criterion is not met, the use of adjudicated values in the primary analysis, the use of initial unadjudicated values in sensitivity analyses, the inclusion of rater ID in the models, and the approach to handling the context dependence of client naturalness ratings.

---

## 0. Major decisions fixed in v3.7

In this version, the following analytic decisions are fixed.

- The timing of SAP finalization is after completion of rater-rating data collection and after the initial inter-rater reliability check, but before reviewing Layer-condition-specific summaries, Hypothesis 1 script-level summaries for the Layer3 condition, or primary analysis model estimates. This version is fixed in this state as the SAP for preregistration.
- The addition of re-evaluation and adjudication rules based on the initial ICC check is explicitly fixed in this version. Individual rating records and overall variability have been reviewed to the extent necessary for the initial ICC calculation and the development of re-evaluation and adjudication rules, but Layer-condition-specific results, Hypothesis 1 Layer3-condition summaries, and primary analysis model estimates will not be reviewed.
- Global ratings will be treated as a 9-category ordinal scale, ranging from 1.0 to 5.0 in 0.5-point increments, assuming that the rating form permits 0.5-point increments. A 0.5-point score is used only when the response is judged to fall between two adjacent integer anchors.
- In this study, the change goal presupposed in MITI ratings is not fixed in advance for each life situation × PERMA profile. Therefore, `change_goal` is excluded from the analysis data structure, and this point is explicitly stated as a limitation in the interpretation of CCT and SST.
- The reference information for Hypothesis 1 is fixed by extracting the human-rated means and standard deviations for GPT-SMDP and Opus-SMDP from Table 2 of a masked prior reference study on Japanese AI counseling evaluation. The values from the two models are not averaged; instead, each model-specific mean is reported as an independent reference value. The mean is the comparison reference, and the prior-study standard deviation is reported only as descriptive variability.
- Behavior codes are treated not as additional ratings assigned by raters, but as system-output behavior-label counts in which the action policies or behavior labels determined in Layer2 are mapped to MITI behavior categories. Because the behavior codes in this study are common to the Layer3 and Layer4 conditions, they are not used in inferential statistics for Layer comparisons.
- `%CR` and `R:Q` derived from behavior codes are treated as exploratory and descriptive indicators. They are not included in secondary hypotheses regarding Layer effects because they do not involve independent validation by human coders and are common across Layers.
- Behavior codes are examined exploratorily in terms of how they differ across life situation × PERMA profile combinations, not as Layer comparisons. The analysis unit is not duplicated by Layer, but is the `pair_id` unit.
- The primary reporting of behavior codes is based on raw counts. As supplementary descriptive statistics, `Q`, `total_reflection`, and `Total MI-Adherent` per counselor utterance are also reported.
- Client-side naturalness ratings are included in this SAP as an exploratory outcome. The “client naturalness” column in the rating form is used and treated as a numerical scale from 1 to 10. If the input is a string such as “6: somewhat natural,” the leading number is extracted as `client_naturalness`.
- For client naturalness, even when the same client response is used, raters evaluate it within the dialogue context, so values may differ depending on the counselor-response context of the Layer3 and Layer4 conditions. Therefore, Layer3-context and Layer4-context values within the same `pair_id × rater_id` are not simply removed as duplicate values.
- In the primary exploratory analysis of client naturalness, context-embedded ratings are retained at the `source_script_id × rater_id` unit, and a linear mixed model adjusted for `source_layer` and `presentation_order_z` is used. `source_layer` is a variable for adjusting for contextual effects and is not treated as a confirmatory or secondary hypothesis regarding a Layer effect.
- For client naturalness, the number of discrepant Layer3-context and Layer4-context values within the same `pair_id × rater_id`, the distribution of differences, and the mean difference are reported descriptively. The primary sensitivity analysis uses the mean of the two context-specific values within the same `pair_id × rater_id`.
- Technical Global is defined as `(CCT + SST) / 2`, and Relational Global is defined as `(PAR + EMP) / 2`. Whether each is 4.0 or higher is treated as a binary secondary outcome.
- The primary analysis model for global ratings is a CLMM that includes random intercepts for `pair_id` and `script_id` to explicitly account for paired structure. The primary analysis model is `rating_ord ~ layer + rater_id + (1 | pair_id) + (1 | script_id)`.
- In the primary analysis, analyses using post-re-evaluation/adjudication values, and sensitivity analyses using initial unadjudicated values, rater ID (`rater_id`) is incorporated into the model to adjust for systematic leniency or severity across raters. In principle, rater ID is treated as a fixed effect; random-effect models are limited to sensitivity analyses.
- Life situation and PERMA profile are not adjustment variables in the primary analysis, but are handled in exploratory analyses. Because `pair_id` absorbs the same life situation, the same PERMA profile, and the same repeated generation ID, the primary analysis targets within-pair Layer differences.
- The presentation order to raters is independently randomized for each rater, and `presentation_order` is recorded for each `rater_id`. For global ratings, presentation order is not included as a covariate in the primary analysis, but is used to describe the implementation of randomization and check for extreme imbalance. If a pre-defined large imbalance is identified, a sensitivity analysis including presentation order is conducted.
- In Hypothesis 1, “exceeds” is a descriptive expression indicating whether the point estimate in the Layer3 condition exceeds the prior-study reference mean. No binary success/failure judgment, superiority test, non-inferiority test, non-inferiority margin, confirmatory judgment based on p-values, or standardized effect size based on the prior-study standard deviation is used.
- In Hypothesis 1, because the prior-study reference values are presented as means, the Layer3 condition in this study is also summarized by computing the mean across raters within each script and then averaging these script means across the 30 scripts. In the descriptive comparison for Hypothesis 1, median-based re-evaluated and adjudicated values are used when necessary, and the mean and standard deviation are used as the primary summary measures. Prior-study standard deviations are shown only to describe variability in the prior study.
- If the outcome-specific ICC(2,k) is below 0.50, all cells for that outcome are reviewed. Only cells that meet the pre-specified threshold are eligible for modification. For the five counselor-rating indicators, individual ratings that are 1.5 points or more away from the initial median are modified to fall within median ± 1.0, and individual ratings that are 1.0 point or more but less than 1.5 points away from the initial median are modified to fall within median ± 0.5. For client naturalness, using a conversion based on the 1–10 scale, individual ratings that are 3.5 points or more away from the initial median are modified to fall within median ± 2, and individual ratings that are 2.5 points or more but less than 3.5 points away from the initial median are modified to fall within median ± 1.
- As a rule, re-evaluation is conducted by the same rater who provided the initial rating. The analysis lead confirms that the re-evaluated value falls within the pre-defined allowable range and that a reason based on the rating criteria has been recorded. The analysis lead performs this confirmation without reviewing Layer-condition-specific summaries or primary analysis results.
- Raters who do not know the design details of the Layer conditions are not shown Layer-condition labels. Even when a researcher who knows the design details of the Layer conditions is involved in re-evaluation or confirmation, they will not use information beyond the general expected direction of individual responses, and they will not refer to Layer-specific summaries or primary analysis results.
- The values of `adjudication_flag` are fixed as `not_applicable`, `checked_no_change`, `adjudicated_changed`, `adjudicated_confirmed`, and `missing_or_unresolvable`.
- Likelihood ratio tests for fixed effects in the client naturalness LMM are conducted using ML estimation with `REML = FALSE`; estimates and 95% confidence intervals are reported primarily from the same fixed-effect structure re-estimated with `REML = TRUE`.
- Category collapsing is limited to a fallback when the 9-category CLMM fails and there is a category with fewer than 5 observations across the 240 rater × script observations for that outcome. Category collapsing follows the pre-specified outcome-specific collapsing map.
- The confirmatory primary analysis family is always fixed at five outcomes. For outcomes for which the first-choice CLMM is valid, the CLMM p-value for the Layer effect is used. For outcomes that move to a pre-specified fallback analysis, the p-value for the Layer effect from the fallback analysis is used. The five p-values are adjusted using the Holm method.
- For reliability indicators, ordinal Krippendorff’s alpha is reported as a supplementary indicator for global ratings, and interval Krippendorff’s alpha is reported as a supplementary indicator for Technical/Relational Global and client naturalness.
- Even if ICC or Krippendorff’s alpha is low, no rater exclusion, rater-specific weighting, or outcome exclusion is performed on the basis of reliability indicators. If the outcome-specific ICC(2,k) is below 0.50, the pre-specified median-based re-evaluation and adjudication rules are applied, and the adjudicated individual rating values are used as the primary analysis values. The same model using initial unadjudicated values is conducted as a sensitivity analysis.
- In the script-level aggregation analysis for Hypothesis 2, when the ICC criterion is not met, the mean of the four post-re-evaluation/adjudication ratings is used as the primary aggregate value; means and medians based on initial unadjudicated values are treated as sensitivity analyses.
- For the 95% confidence interval of the Layer effect in the primary analysis, the profile likelihood method is the first choice. If the profile likelihood method does not converge, a Wald confidence interval is used and this is reported. For other effects and auxiliary analyses, Wald confidence intervals are used by default.
- If a random-effect variance is near zero, for example variance < 1e-6, it is distinguished from non-convergence and recorded as a boundary estimate or singular fit.
- The primary length indicator in sensitivity analyses adjusting for script length is the number of counselor utterances. Counselor-character count and total script-character count are reported as descriptive statistics.
- Overall counselor rating is a study-specific overall evaluation indicator and is not a standard MITI global rating. It is treated as a study-specific overall counselor rating based on the five-point rubric fixed in this SAP.
- Raters’ post hoc guesses of Layer condition are not recorded. Differences in response characteristics between the Layer3 and Layer4 conditions are part of the Layer effect itself, so guess accuracy does not function as an indicator of blinding quality. This judgment and the corresponding interpretive limitation are stated in Section 24.5.
- For Hypothesis 2, no binary success/failure or supported/not-supported decision is made. For the five outcomes, ORs, 95% confidence intervals, Holm-adjusted p-values, and the number of outcomes in which the OR > 1 direction is observed are reported in parallel.
- `script_id` is treated as nested within `pair_id`. If random intercepts for both `pair_id` and `script_id` cannot be estimated simultaneously, the pre-specified rule is to remove `script_id` first in principle and retain `pair_id` whenever possible.
- Complete cases for ICC refer to scripts with ratings from all four raters for each outcome. Complete cases across all five outcomes are not used.
- Script-level scores for Hypothesis 1 are calculated for scripts with ratings from three or more raters. Scripts with ratings from two or fewer raters are excluded from the comparison for that outcome.
- Rater presentation order was randomized using Excel functions, and no random seed exists. The actual presentation-order list is stored before analysis and cross-checked against `presentation_order`.
- The specific contents of the five life-situation levels and three PERMA-profile levels are fixed in Appendix C.
- The “overall rating” column in the rating form is imported into the analysis data as `overall_counselor_rating`.

## 1. Information sources

This SAP is based on the following information sources.

1. Prior versions of this SAP and revision history.
2. General SAP preparation manual.
3. Moyers, T. B., Manuel, J. K., & Ernst, D. *Motivational Interviewing Treatment Integrity Coding Manual 4.2.1*.
4. MITI 4.2.1-related materials and Japanese translations provided by CASAA (Center on Alcohol, Substance use, And Addictions).
5. Masked prior reference study on Japanese AI counseling evaluation.

Item 5 is used as the source of reference values from prior work for Hypothesis 1. Because its design, target scripts, and rater composition differ from the within-study Layer comparison, it is handled only as a descriptive comparison, not as a confirmatory test. The term “benchmark” is not used; instead, these values are described as “reference values from prior work.”

---

## 2. Administrative information and version control

### 2.1 Rating form specifications

This SAP does not define separate attachments for publication or preregistration. The necessary specifications related to the rating form and rating criteria are fixed within the main text of this SAP as follows.

- `rating_form` sheet: includes `target_id`, `script_link`, `record_link`, `counselor_response_memo`, `CCT`, `SST`, `Partnership`, `Empathy`, `overall_counselor_rating`, `client_response_memo`, `client_naturalness`, and `notes`.
- `rating_criteria` sheet: includes the 1-5 anchors for `CCT`, `SST`, `Partnership`, `Empathy`, and `overall_counselor_rating`, as well as definitions of `change_talk`, `sustain_talk`, `partnership`, and `empathy`.

Raters are presented with the following instructions.

```text
For the responses of the counselor AI, please use MITI 4.2.1 as a reference and
provide global ratings on the five indicators using the presented rubric, on a
1–5 scale in 0.5-point increments. These ratings are strictly ratings of the five
indicators and are not ratings of interview effectiveness or response naturalness.
If you notice anything about those aspects, please write it in the memo or notes fields.

For the responses of the client AI, please rate their naturalness on a scale from
1 to 10. If you notice anything, please write it in the comment field.
```

The “overall rating” column in the rating form refers to the same outcome as Overall counselor rating in this SAP. In the analysis data, it is imported as `overall_counselor_rating`.


### 2.2 Timing of SAP finalization

This SAP is fixed at the following timing.

```text
Before or after reviewing individual records for primary outcomes: After
  (reviewed to the extent necessary for initial ICC calculation and creation of re-evaluation/adjudication rules)
Before or after reviewing overall summaries of primary outcomes: After
  (reviewed to the extent necessary for inter-rater reliability and overall variability checks)
Before or after reviewing primary outcome results by Layer condition: Before
Before or after reviewing Hypothesis 1 script-level summaries for the Layer3 condition: Before
Before or after reviewing primary analysis model estimates: Before
Before or after rater-rating data collection: After
Whether rater-rating data collection is complete: After completion
Before or after fixation of the analysis dataset: Before or at the time of analysis dataset fixation
Before or after rater blinding is lifted: Before, if rater blinding exists
Before or after preregistration submission: Before
```

This version is the SAP for preregistration in which the re-evaluation and adjudication rules are fixed after checking the inter-rater reliability of the initial independent ratings. Therefore, it is not an SAP fixed before rater-rating data collection. However, the analysis policy in this version is fixed before reviewing Layer-condition-specific summaries of primary outcomes, Hypothesis 1 script-level summaries for the Layer3 condition, primary analysis model estimates, or client naturalness summaries by life situation × PERMA profile.

Here, “reviewing individual records for primary outcomes” means reviewing rater-specific individual rating values for CCT, SST, PAR, EMP, and Overall counselor rating to determine inter-rater reliability, deviation from the median, and targets for re-evaluation/adjudication.

For client naturalness as well, this SAP fixes the analysis policy after checking inter-rater reliability, deviation from the median, and the discrepancy status of Layer3-context and Layer4-context values within the same `pair_id × rater_id`. However, the analysis policy is fixed before reviewing life situation × PERMA profile summaries, `source_layer` effects, interaction models, or sensitivity-analysis results.

### 2.3 Revision history

```text
v3.0-draft  2026-05-06  Initial version. Defined the primary analysis model, treatment of raters, pair_id, and multiple-comparison policy.
v3.0  2026-05-07  Resolved unresolved issues and fixed the SAP finalization timing, rating scale, change_goal, reference values, behavior-code assigner, and treatment of Technical/Relational Global.
v3.1  2026-05-07  Incorporated review comments. Removed the pair_id random effect from the primary analysis model and used script_id only. Changed Hypothesis 1 from a simple average to reporting the two models' reference values separately, and changed “benchmark” to “reference value.” Copied the Overall counselor rating rubric into the SAP. Added limitations on behavior-code validity verification, rationale for not verifying rater blinding, interpretation notes for Technical/Relational Global analyses, the relationship between derived indicators and multiple comparisons, and fallback decision timing.
v3.2  2026-05-07  Changed the primary analysis to a paired CLMM including a pair_id random intercept, and moved life situation and PERMA profile to exploratory analyses. Removed change_goal from the analysis data structure and described it as a limitation. Because behavior codes are determined in Layer2 and common across Layers, removed %CR and R:Q from Layer comparisons and changed them to exploratory/descriptive indicators. Extracted Hypothesis 1 reference values from Table 2 of the attached paper and fixed the source information. Reflected the rating form and rating criteria sheet contents in the SAP main text and appendices.
v3.3  2026-05-07  Standardized the main-text description of SAP finalization timing as “before reviewing individual records for primary outcomes.” Added client naturalness ratings as an exploratory outcome. Stated that client naturalness and behavior codes are examined exploratorily for the life situation × PERMA profile interaction rather than for Layer comparisons. Added the life situation × PERMA profile interaction for behavior codes, which had not been explicit in v3.2.
v3.4  2026-05-08  Based on detailed review comments, corrected erroneous references to non-existent sections to Section 24.5. Clarified the 9-category rating form specification, limitations of CCT/SST without change goals, descriptive comparison criteria for Hypothesis 1, treatment of presentation order, criteria for exploratory all-pair comparisons, handling of discrepancies in client naturalness, ML/REML specifications for LMMs, pre-specification limits for behavior-code exploratory models, convergence-failure rules prioritizing retention of pair_id, category-collapsing map, reliability indicators, and script-level aggregate values.
v3.5  2026-05-08  Based on additional review comments, clarified the policy of not making a binary decision for Hypothesis 2, the identical definition of Overall counselor rating and prior-study OVR, nested structure of pair_id and script_id, denominator for category-collapsing decisions, overdispersion criterion for behavior codes, ICC complete-case definition, handling of low ICC or Krippendorff's alpha, use of means in Hypothesis 1, consensus final score rules under low reliability and missingness aggregation rules, verification of the actual presentation-order list, life situation and PERMA levels, Holm adjustment when some outcomes use fallback analysis, description when leave-one-rater-out analysis reverses direction, supplementary checks of the proportional-odds assumption, correspondence between rating form column names and analysis data column names, and storage of convergence-decision logs.
v3.6  2026-05-09  As the prior version before preregistration, organized version, date, and related-document descriptions. Directly fixed in the SAP main text the necessary specifications for the rating form and rating criteria, rater instructions, five life-situation levels, and three PERMA-profile levels.
v3.7  2026-05-09  Revised as the preregistration-fixed version. Explicitly stated that it is fixed after completion of rater-rating data collection and after the initial ICC check, but before reviewing Layer-condition-specific summaries, Hypothesis 1 script-level summaries for the Layer3 condition, or primary analysis model estimates. Added rules for re-evaluation and adjudication using the initial median as the reference, with all cells reviewed when ICC(2,k) is below 0.50. For the five counselor-rating indicators, fixed the rule that median differences of 1.5 points or more are corrected to within median ± 1.0 and differences of 1.0 point or more but less than 1.5 are corrected to within median ± 0.5. For client naturalness, after scale-width conversion, fixed the rule that median differences of 3.5 points or more are corrected to within median ± 2 and differences of 2.5 points or more but less than 3.5 are corrected to within median ± 1. Clarified that adjudicated values are used for the primary analysis, initial unadjudicated values are used for sensitivity analyses, and rater ID is incorporated into all rater-rating models. Treated client naturalness as a rating within dialogue context and fixed a primary exploratory model that does not remove Layer3-context and Layer4-context values as simple duplicates but instead adjusts for source_layer and presentation order, along with a sensitivity analysis using pair_id × rater_id means.
```

---

## 3. Purpose of this SAP

This SAP is a document for defining, before preregistration, the handling of primary outcomes, secondary outcomes, exploratory outcomes, rater differences, paired structure, missingness and division by zero, model diagnostics, multiple comparisons, sensitivity analyses, and SAP deviations using ratings, client naturalness ratings, and behavior codes for 60 Japanese counseling scripts.

The core policies of this SAP are as follows.

- In the primary analysis, outcomes meeting the ICC criterion use the initial global ratings from all four raters. Outcomes with ICC(2,k) below 0.50 use the individual ratings from all four raters after the median-based re-evaluation and adjudication described in Section 14.4.
- In the primary analysis of global ratings, rater differences are included as fixed effects in the statistical model regardless of whether initial values or adjudicated values are used.
- Inter-rater reliability is reported, but is not used to select or exclude raters.
- If the outcome-specific ICC(2,k) is below 0.50, final rating values are created by median-based re-evaluation and adjudication of all cells, rather than by excluding raters. Adjudicated values are treated as primary analysis values, and initial unadjudicated values are treated as sensitivity-analysis values.
- The 30 pairs sharing common client responses are defined as `pair_id`, and a `pair_id` random intercept is included in the primary analysis model.
- Global rating values are treated as a 9-category ordinal scale from 1.0 to 5.0 in 0.5-point increments.
- The effect of Layer condition is the confirmatory primary analysis, and the effects of life situation and PERMA profile are handled as exploratory analyses.
- For Technical Global and Relational Global, achievement of the Good threshold of 4.0 or higher is treated as a binary secondary outcome.
- `%CR` and `R:Q` derived from behavior codes are based on the action policies or behavior labels determined in Layer2 and are common to the Layer3 and Layer4 conditions; therefore, they are not used in inferential statistics for Layer comparisons. They are reported as exploratory and descriptive indicators.
- Behavior codes are examined exploratorily for differences across life situation × PERMA profile combinations.
- Client naturalness is treated as a 1–10 exploratory outcome. Because client naturalness is a rating made within dialogue context, the same client response may have different values depending on the counselor-response context in the Layer3 and Layer4 conditions. In the primary exploratory analysis, context-embedded ratings are retained, and `source_layer` and presentation order are adjusted for. No confirmatory conclusion is drawn regarding a Layer effect.
- In this study, the change goal is not fixed in advance for each life situation × PERMA profile. This point is treated as a limitation in the interpretation of CCT and SST.

## 4. Summary of the study design

This study is a dialogue simulation study that examines dialogue quality with reference to MITI (Motivational Interviewing Treatment Integrity) as a proximal mechanism of an AI counseling agent that may support flourishing.

The analysis targets a total of 60 Japanese counseling scripts generated under the following design.

- Life situation: 5 levels
- PERMA profile: 3 levels
- Layer condition: 2 levels, Layer3 condition and Layer4 condition
- Repeated generation: 2 times per condition
- Total: 5 × 3 × 2 × 2 = 60 scripts

The specific contents of the five life-situation levels and the three PERMA-profile levels are fixed in Appendix C.

PERMA is an acronym for Positive Emotion, Engagement, Relationships, Meaning, and Accomplishment, and refers to a five-component framework of well-being.

For the comparison between the Layer3 and Layer4 conditions, 30 pairs sharing common client responses are defined. Each pair consists of a Layer3 script and a Layer4 script corresponding to the same life situation, the same PERMA profile, and the same repeated generation ID.

Each script is globally rated by four raters. Therefore, for each primary outcome, the rating data consist of 60 scripts × 4 raters = 240 observations. However, these 240 observations are not treated as independent observations; the rater, script, and pair structures are reflected in the statistical model.

The presentation order to raters is independently randomized for each rater. Presentation order is recorded for each `rater_id`.

Because presentation order was randomized using Excel functions, no reproducible random seed exists. Therefore, instead of a random seed, the actual order list presented to raters is stored as an operational record. Before analysis, the actual presentation-order list is checked against `presentation_order` in the analysis dataset.

For global ratings, presentation order is not included as a covariate in the primary analysis. Presentation order is treated as an operational record for assessing possible rater-specific fatigue, learning, or changes in rating standards, and the mean, median, and range of presentation position are checked descriptively by rater, by Layer condition, and by primary outcome. If a large imbalance is observed between Layer condition and presentation position, the presentation-order-adjusted sensitivity analysis in Section 21.9 is conducted.

Here, “large imbalance” is defined as an absolute difference of 10 or more positions in mean presentation position between the Layer3 and Layer4 conditions within any rater, or an absolute difference of 5 or more positions in mean presentation position across all four raters.

Behavior codes are not assigned by raters. Instead, the action policies or behavior labels determined in Layer2 are treated as system-output behavior-label counts mapped to MITI behavior categories. In this study, behavior codes are common to the Layer3 and Layer4 conditions. Therefore, behavior-code-derived indicators are not used in inferential statistics for Layer comparisons and are reported as exploratory and descriptive indicators.

Client naturalness is a 1–10 exploratory outcome based on the “client naturalness” column in the rating form. Although the client response is common to the Layer3 and Layer4 conditions, raters evaluate the client response within dialogue context. Therefore, even for the same client response, the naturalness rating may differ depending on the counselor-response context in the Layer3 and Layer4 conditions.

To address this context dependence, the primary exploratory analysis of client naturalness does not remove Layer3-context and Layer4-context values as duplicate values. Instead, it retains them as context-embedded ratings at the `source_script_id × rater_id` unit. The model adjusts for `source_layer` and `presentation_order_z`, and it exploratorily examines differences in naturalness across life situation × PERMA profile combinations. `source_layer` is a variable used to adjust for contextual effects and is not interpreted as a Layer effect regarding counselor quality.

## 5. Research questions and estimands

### 5.1 Primary research question

The primary research question of this study is defined in the following sentence.

```text
Among pairs that share the same life situation, the same PERMA profile, the same repeated generation ID, and a common client response, is the Layer4 condition more likely than the Layer3 condition to fall into higher rating categories for MITI-informed global ratings and overall counselor evaluation?
```

### 5.2 Primary estimand

The primary estimand is as follows.

- Target: 60 Japanese counseling scripts meeting the eligibility criteria of this SAP.
- Comparison: Layer4 condition versus Layer3 condition within the same `pair_id`.
- Evaluation time point: rater-rating time point for generated scripts.
- Primary outcomes: CCT, SST, PAR, EMP, and Overall counselor rating.
- Summary measure: cumulative odds ratio for the Layer4 condition in the CLMM (cumulative link mixed model).
- Interpretation: a cumulative odds ratio greater than 1 means that, within the same pair, the Layer4 condition is more likely to fall into higher rating categories.

### 5.3 Secondary estimands

The secondary estimands are MITI-related Good-threshold achievement derived from global ratings.

- Technical Global >= 4.0: whether the technical global indicator is at or above the Good level.
- Relational Global >= 4.0: whether the relational global indicator is at or above the Good level.

These are treated as binary outcomes and compare the Layer4 condition with the Layer3 condition.

`%CR` and `R:Q` derived from behavior codes are not included in the secondary estimands because they are determined in Layer2 and common to the Layer3 and Layer4 conditions. They are treated as exploratory and descriptive indicators.

### 5.4 Exploratory estimands

The exploratory estimands are as follows.

- Main effect of life situation on primary outcomes.
- Main effect of PERMA profile on primary outcomes.
- Interactions in primary outcomes, such as Layer × life situation, Layer × PERMA profile, and life situation × PERMA profile.
- Life situation × PERMA profile interaction in client naturalness.
- Life situation × PERMA profile interaction in behavior codes and behavior summary scores.
- Auxiliary analyses including script length, character count, utterance count, and related variables.
- Descriptions of `%CR`, `R:Q`, and related division-by-zero or small-denominator issues derived from behavior codes.

### 5.5 Distinction between confirmatory and exploratory analyses

The confirmatory primary analysis is the Layer effect in Hypothesis 2.

The secondary analyses are the Layer effects in Good-threshold achievement for Technical Global and Relational Global.

The life situation × PERMA profile analyses of client naturalness and behavior codes are pre-planned exploratory analyses. These are reported not as hypothesis tests, but as analyses to understand which condition combinations are more likely to produce unnatural or characteristic client responses or behavior codes.

---

## 6. Assumptions regarding MITI application

### 6.1 Target of MITI evaluation

MITI is a behavioral coding system for evaluating the treatment integrity of MI (Motivational Interviewing), that is, the extent to which an interviewer appropriately uses motivational interviewing.

MITI consists of two components: GLOBAL SCORES and BEHAVIOR COUNTS. GLOBAL SCORES evaluate four indicators: CCT (Cultivating Change Talk), SST (Softening Sustain Talk), Partnership, and Empathy. BEHAVIOR COUNTS tally the frequencies of specific interviewer behaviors.

### 6.2 Handling and limitations of the change goal

In MITI, it is important that a change goal be specified for the interaction being evaluated. If the change goal cannot be identified, the interpretation of CCT and SST may become unstable.

In this study, the change goal is not fixed in advance for each life situation × PERMA profile. In addition, explicit script-specific change goals are not separately presented to raters.

Therefore, this SAP does not treat the change goal as an analysis data column. `change_goal_id` and `change_goal_text` are not included as required columns in the analysis dataset.

CCT and SST ratings in this study are interpreted as approximate evaluations based on the change direction that raters can infer from the script text. This point is explicitly stated as a study limitation in Section 24.5.

CCT and SST are central indicators for evaluating the MI-technique quality of this study, so they are not excluded from the primary outcomes. However, the results for CCT and SST alone are not used to conclude that the scripts have high MI congruence for a specific behavior-change goal.

### 6.3 Treatment of the rating scale

In standard MITI, GLOBAL SCORES are rated on a 1–5 five-point scale. In this study, the rating specification is fixed in this SAP as permitting 0.5-point increments, and ratings are treated as 9 categories from 1.0 to 5.0 in 0.5-point increments.

A 0.5-point score is used when the rating is judged to be located between two adjacent integer anchors. For example, if a response is clearly better than 3 but does not sufficiently meet the description for 4, it is scored as 3.5.

Valid values are limited to the following nine values: `1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0`. Values other than these are checked against the source data or rating records and corrected only when the basis for correction is clear. If correction is not possible, they are treated as missing.

When 9-category ratings are used in this study, this is an operational research-level subdivision of the standard MITI five-point scale. The manuscript will describe it as follows.

```text
Based on the 1–5 MITI 4.2.1 global ratings, this study allowed 0.5-point increments on the rater form; therefore, ratings were analyzed as a 9-category ordinal scale ranging from 1.0 to 5.0.
```

If it is later determined that the rating form allowed only integer ratings, this is recorded as an SAP deviation, and the change to a 1–5 five-category ordinal-scale analysis is explicitly stated.

### 6.4 Evaluated segment

MITI usually assumes evaluation of a fixed segment extracted from an audio interview. Because this study is a text-based dialogue simulation, the primary analysis evaluates each full script.

However, the following are recorded.

- Number of counselor utterances in each script.
- Number of client utterances in each script.
- Number of counselor-response characters.
- Total number of script characters.

The effect of script length is not adjusted for in the primary analysis and is checked in sensitivity analyses. The primary length indicator in script-length-adjusted sensitivity analyses is the number of counselor utterances.

---

## 7. Finalized analytic decisions

### 7.1 Treatment of raters

In the primary analysis of global ratings, raters are treated as fixed effects.

This reflects the idea of adjusting for systematic differences in severity or leniency among the four raters. Because there are only four raters, treating raters as fixed effects is more stable than treating them as a random sample from a broader rater population and estimating a variance component.

A model treating raters as random effects is conducted as a sensitivity analysis.

### 7.2 Treatment of behavior codes

Behavior codes are not assigned by raters to each script. Instead, the action policies or behavior labels determined in Layer2 are treated as system-output behavior-label counts mapped to MITI behavior categories.

In this study, the behavior codes are common to the Layer3 and Layer4 conditions. Therefore, `%CR`, `R:Q`, and their Good-threshold achievement derived from behavior codes are not used in inferential statistics for Layer comparisons.

Behavior-code-derived indicators are reported as exploratory and descriptive indicators. Because they do not involve independent coding by human coders, it is explicitly stated that their nature differs from standard MITI 4.2.1 behavior counts.

For behavior codes, Layer conditions are not duplicated; the data are aggregated at the `pair_id` level, and differences across life situation × PERMA profile combinations are examined exploratorily. If `pair_id` does not exist in the analysis data, it is reconstructed from `situation × perma_profile × generation_id`.

### 7.3 Treatment of client naturalness

Client naturalness is an exploratory outcome based on the “client naturalness” column in the rating form. The score is treated as ranging from 1 to 10, with higher values indicating a more natural client response.

The rating form may contain a mixture of numeric-only inputs and inputs in which a number is followed by descriptive text. For example, “6: somewhat natural” is treated as the numeric value 6. If a numeric value cannot be extracted, the observation is treated as missing.

The client response itself is common to the Layer3 and Layer4 conditions. However, the raters in this study evaluated the client response not as an isolated utterance, but as a response within a dialogue context. Therefore, if Layer3-context and Layer4-context values differ within the same `pair_id × rater_id`, this is not merely an inconsistency in duplicate data; it may reflect evaluation differences due to counselor-response context or presentation order.

For this reason, the primary exploratory analysis of client naturalness does not simply remove Layer3-context and Layer4-context values as duplicates. It retains context-embedded ratings at the `source_script_id × rater_id` unit and adjusts for context differences and rater differences using `source_layer`, `presentation_order_z`, `rater_id`, `pair_id`, and `source_script_id`. `source_layer` is a variable for adjusting for contextual effects and is not treated as a confirmatory or secondary hypothesis regarding a Layer effect.

The primary sensitivity analysis uses the mean of the Layer3-context and Layer4-context values within the same `pair_id × rater_id` and analyzes it as a pair-level naturalness evaluation closer to the client response itself.

### 7.4 Definition and use of `pair_id`

`pair_id` is defined as the pair of Layer3 and Layer4 scripts sharing a common client response.

Specifically, the same `pair_id` is assigned to the Layer3 script and Layer4 script that have the same life situation, the same PERMA profile, and the same repeated generation ID.

`pair_id` is used for the following purposes.

- Explicitly representing paired structure in the primary analysis.
- Checking consistency of paired structure during data validation.
- Conducting paired-difference analyses in script-level aggregate analyses.
- Removing Layer duplicates for client naturalness and behavior codes.
- Fallback analyses when model convergence fails.

### 7.5 Positioning of hypotheses

Hypothesis 2, that is, the effect of Layer condition, is the confirmatory primary analysis.

The life-situation effect in Hypothesis 3 and the PERMA-profile effect in Hypothesis 4 are treated as secondary/exploratory analyses. Because life situation has five levels and PERMA profile has three levels, with few independent replications relative to the number of levels, strong confirmatory conclusions are avoided.

The life situation × PERMA profile interactions in client naturalness and behavior codes are treated as pre-planned exploratory analyses.

### 7.6 Treatment of the 9 categories

The primary analysis retains the nine categories 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, and 5.0.

Categories are not rounded to a 1–5 five-point scale.

However, if it is later confirmed that the rating form allowed integer ratings only, this is recorded as an SAP deviation and the analysis is conducted as a 1–5 five-category ordinal scale.

Although 0.5-point increments were allowed on the rating form, if some categories are not used in the actual data, the data are analyzed as a 9-category ordinal scale in principle. Only if the model fails are the category-collapsing rules pre-defined in Section 22.1 used.

### 7.7 Direction of tests

All tests are two-sided.

Although there is a directional hypothesis that the Layer4 condition will be rated higher than the Layer3 condition, one-sided tests are not used, prioritizing clarity and conservativeness for peer review.

### 7.8 Treatment of interactions

No interaction terms are included in the confirmatory primary analysis model.

Interactions in primary outcomes, such as Layer × life situation, Layer × PERMA profile, and life situation × PERMA profile, are conducted as exploratory analyses.

For client naturalness and behavior codes, Layer interactions are not evaluated because the Layer condition is common for these indicators. The life situation × PERMA profile combination, that is, the interaction, is treated as a pre-planned exploratory interest.

### 7.9 Treatment of script length

In the primary analysis, script length indicators such as the number of counselor utterances, character count, and token count are not adjusted for as covariates.

Because Layer4 may change response naturalness, conciseness, or verbosity, script length may be part of the Layer effect. Adjusting for length in the primary analysis may remove too much of the Layer4 effect.

Models adjusted for script length are conducted as sensitivity analyses.

### 7.10 Python-R integration

The analysis is conducted primarily in Python.

Data shaping, validation, descriptive statistics, reliability analysis, visualization, and export of CSV files for analysis are conducted in Python. Cumulative link mixed models, linear mixed models, and binary logistic mixed models are run in R by calling `Rscript` from Python via `subprocess`.

CSV files passed from Python to R are output as UTF-8 with BOM, that is, with `encoding="utf-8-sig"` in Python.

---

## 8. Hypotheses

### 8.1 Hypothesis 1: comparison with reference values from prior work

The mean scores of the Layer3 condition for the four MITI-informed global rating indicators, namely CCT, SST, PAR, and EMP, as well as Overall counselor rating, are predicted to exceed pre-defined reference mean values from prior Japanese AI counseling research, specifically the human-rated means for GPT-SMDP and Opus-SMDP.

Because this comparison is with prior research that differs in target scripts and evaluation design, it is treated as a descriptive comparison rather than a confirmatory test. Therefore, “testing” Hypothesis 1 refers not to a p-value-based superiority test or non-inferiority test, but to a descriptive evaluation in which the pre-fixed reference mean values are presented alongside the script-level mean scores for the Layer3 condition in this study. The prior-study standard deviations are reported only as descriptive variability and are not used for a success/failure decision, non-inferiority margin, or standardized effect size.

### 8.2 Hypothesis 2: structural improvement hypothesis

The Layer4 condition is predicted to show higher ratings than the Layer3 condition in MITI-informed global ratings and Overall counselor rating.

This hypothesis is the confirmatory primary analysis of this study.

### 8.3 Hypothesis 3: main effect of life situation

Differences are predicted across the five life situations in MITI-informed global ratings and Overall counselor rating.

This hypothesis is treated as a secondary/exploratory analysis.

### 8.4 Hypothesis 4: main effect of PERMA profile

Differences are predicted across the three PERMA-profile categories in MITI-informed global ratings and Overall counselor rating.

This hypothesis is treated as a secondary/exploratory analysis.

### 8.5 Secondary hypothesis regarding Good-threshold achievement

For Good-threshold achievement derived from global ratings, the Layer4 condition is predicted to be more likely to achieve the threshold than the Layer3 condition.

The following two Good thresholds are targeted.

- Technical Global >= 4.0
- Relational Global >= 4.0

This analysis is treated as a secondary analysis linked to Hypothesis 2. Differences in Good-threshold achievement by life situation and PERMA profile are examined exploratorily.

`%CR >= 50%` and `R:Q >= 2.0` derived from behavior codes are not included in this secondary hypothesis because they are determined in Layer2 and common to the Layer3 and Layer4 conditions.

### 8.6 Exploratory hypothesis regarding client naturalness

Client naturalness may differ by life situation × PERMA profile combination.

However, naturalness is an indicator rated within dialogue context. Even for the same client response, the naturalness rating may differ depending on the counselor-response context in the Layer3 and Layer4 conditions. Therefore, the primary exploratory analysis adjusts for `source_layer` and presentation order, and differences between Layer3-context and Layer4-context values are treated as descriptions of context dependence.

This analysis is an exploratory analysis to understand in which life situation/PERMA profile combinations the client AI responses are more likely to become unnatural. It is not a test of a Layer effect regarding counselor quality.

### 8.7 Exploratory hypothesis regarding behavior codes

Behavior codes and behavior summary scores may differ by life situation × PERMA profile combination.

However, because behavior codes are determined in Layer2 and common to the Layer3 and Layer4 conditions, the effect of Layer condition is not tested. This analysis is an exploratory analysis to understand in which life situation/PERMA profile combinations behavior patterns such as questions, reflections, affirmations, and emphasis on autonomy are more likely to differ.

---

## 9. Outcomes

### 9.1 Primary outcomes: global ratings

The primary outcomes are the following five indicators.

- CCT: Cultivating Change Talk.
- SST: Softening Sustain Talk.
- PAR: Partnership.
- EMP: Empathy.
- Overall counselor rating: an overall counselor evaluation. This is a study-specific overall evaluation indicator.

CCT, SST, PAR, and EMP are based on the MITI 4.2.1 global ratings. Overall counselor rating is not a standard MITI global rating, but is treated as a study-specific outcome evaluating the overall quality of the counselor response.

#### 9.1.1 Rubric for Overall counselor rating

Overall counselor rating is fixed in this SAP as the following five-level rubric. This rubric follows the format of MITI global ratings and uses anchor descriptions from 1 point (lowest) to 5 points (highest). Because this study permits 0.5-point increments, it is operated as nine categories from 1.0 to 5.0.

```text
1 point (lowest)
The clinician points out and blames the client’s problems. Or, the clinician
markedly restricts the client’s autonomy and tries to impose the clinician’s own
opinion.

2 points
The clinician shows a negative attitude toward the client. Alternatively, the
clinician is not open, and appears to conceal negative feelings. Evidence that
the clinician believes in the client’s strengths is not explicit.

3 points
The clinician responds with some degree of acceptance and empathy and shows an
open and genuine attitude. Some evidence is shown that the clinician believes in
the client’s strengths.

4 points
In most cases, the clinician responds with acceptance and empathy and shows an
open and genuine attitude. It is mostly explicit that the clinician believes in
the client’s strengths.

5 points (highest)
The clinician consistently responds with acceptance and empathy and shows an
open and genuine attitude. It is frankly and explicitly shown that the clinician
believes in the client’s strengths.
```

Overall counselor rating is not a derived indicator that simply aggregates CCT, SST, PAR, and EMP; it is an independent rating given by raters for the counselor response as a whole. Therefore, it is included in the confirmatory outcome family for the primary analysis.

Each outcome is treated as a 9-category ordinal scale from 1.0 to 5.0 in 0.5-point increments.

In analysis, the following ordered categories are defined.

```text
1.0 < 1.5 < 2.0 < 2.5 < 3.0 < 3.5 < 4.0 < 4.5 < 5.0
```

### 9.2 Secondary outcomes derived from global ratings

The following two continuous summary scores are calculated from global ratings.

```text
Technical Global = (CCT + SST) / 2
Relational Global = (PAR + EMP) / 2
```

In addition, the following binary outcomes are created.

```text
good_technical_global = 1 if Technical Global >= 4.0
                        0 otherwise

good_relational_global = 1 if Relational Global >= 4.0
                         0 otherwise
```

Technical Global and Relational Global are calculated at the rater level from each rater’s CCT, SST, PAR, and EMP ratings. Therefore, analyses of these Good-threshold achievement outcomes include rater fixed effects in principle.

### 9.3 Exploratory outcomes: behavior summary scores

Behavior scores are defined based on the BEHAVIOR COUNTS of MITI 4.2.1.

In this study, behavior codes are not assigned by raters. Instead, the action policies or behavior labels determined in Layer2 are treated as system-output behavior-label counts mapped to MITI behavior categories. In this study, behavior codes are common to the Layer3 and Layer4 conditions. Therefore, behavior-code-derived outcomes are not used in inferential statistics for Layer comparisons.

The following behavior summary scores are calculated.

#### 9.3.1 Proportion of complex reflections

```text
total_reflection = SR + CR
pct_complex_reflection = CR / (SR + CR)
good_pct_complex_reflection = 1 if pct_complex_reflection >= 0.50
                              0 otherwise
```

Here, SR is Simple Reflection. CR is Complex Reflection.

#### 9.3.2 Reflection-to-question ratio

```text
reflection_question_ratio = (SR + CR) / Q
good_reflection_question_ratio = 1 if reflection_question_ratio >= 2.00
                                 0 otherwise
```

Here, Q is Question.

`good_pct_complex_reflection` and `good_reflection_question_ratio` are not secondary outcomes for Layer effects, but are treated as exploratory and descriptive achievement indicators.

### 9.4 Descriptive statistics for behavior codes

For each behavior code, the mean frequency and standard deviation are reported.

Based on MITI 4.2.1, at least the following behavior codes are included.

- Giving Information (GI)
- Persuade
- Persuade with Permission
- Question (Q)
- Simple Reflection (SR)
- Complex Reflection (CR)
- Affirm (AF)
- Seeking Collaboration (Seek)
- Emphasizing Autonomy (Emphasize)
- Confront

In addition, the following derived indicators are reported as descriptive statistics.

```text
Total reflections = SR + CR
%CR = CR / (SR + CR)
R:Q = (SR + CR) / Q
Total MI-Adherent = Seeking Collaboration + Affirm + Emphasizing Autonomy
Total MI Non-Adherent = Confront + Persuade
Q per counselor utterance = Q / counselor_utterance_count
total_reflection per counselor utterance = (SR + CR) / counselor_utterance_count
Total MI-Adherent per counselor utterance = Total MI-Adherent / counselor_utterance_count
```

Rates per counselor utterance are descriptive indicators for supplementarily assessing the influence of script length and are not used in the primary inferential models.

Because Good thresholds are not defined in MITI 4.2.1 for Total MI-Adherent or Total MI Non-Adherent, these are not treated as primary targets for inferential statistics and are handled as descriptive statistics.

### 9.5 Treatment of summaries

Summaries are not treated as an independent behavior code. Instead, they are classified as SR or CR according to the MITI 4.2.1 reflection codes.

A simple summary, meaning a summary that combines multiple client utterances without adding additional meaning or direction, is coded as SR.

A summary that includes direction, added meaning, focusing, or deeper understanding beyond the client’s utterance is coded as CR.

If it is unclear whether a summary is SR or CR, it is conservatively coded as SR.

### 9.6 Exploratory outcome: client naturalness

Client naturalness is treated as a 1–10 numerical scale based on the “client naturalness” column in the rating form.

```text
client_naturalness = 1, 2, 3, ..., 10
```

Higher values indicate that the client response is more natural.

If the input is a string such as “6: somewhat natural,” the leading number is extracted and treated as `client_naturalness = 6`. If a number cannot be extracted, or if a value outside the 1–10 range is identified, the source data are checked. If correction is not possible, the value is treated as missing.

Client naturalness is treated as an indicator rated within dialogue context rather than as a rating of an isolated client response. Therefore, if the Layer3-context and Layer4-context values corresponding to the same client response differ, the discrepancy is not treated as a simple duplicate-data error. In the primary exploratory analysis, context-embedded ratings are retained, and `source_layer` and presentation order are adjusted for. In the primary sensitivity analysis, the mean of the two context-specific values within the same `pair_id × rater_id` is used.

Client naturalness is an indicator for exploratorily examining differences across life situation × PERMA profile combinations. Differences associated with `source_layer` may reflect the influence of counselor-response context or presentation order and are therefore not used for confirmatory conclusions regarding Layer effects.

## 10. Data structure

### 10.1 Global rating data

Global rating data are analyzed in long format by outcome.

The required columns are as follows.

```text
script_id
pair_id
layer
situation
perma_profile
generation_id
rater_id
outcome
rating_initial
initial_median
absolute_median_diff
adjudication_flag
rating_final
rating_analysis
presentation_order
```

`layer` uses Layer3 as the reference category and Layer4 as the comparison category.

`rating_initial` is the initial independent rating value and must be in 0.5-point increments from 1.0 to 5.0. `rating_final` is the final rating value when the median-based re-evaluation and adjudication rules in Section 14.4 are applied. For outcomes to which the re-evaluation/adjudication rules are not applied, `rating_final` is identical to `rating_initial`. `rating_analysis` is the rating value used in the primary analysis; it is `rating_final` for outcomes with ICC(2,k) below 0.50 and `rating_initial` for outcomes with ICC(2,k) of 0.50 or higher. `adjudication_flag` indicates whether the relevant cell was modified through re-evaluation/adjudication, checked only, or not applicable.

The correspondence between column names in the rating form and outcome or column names in the analysis data is fixed as follows.

```text
Rating form column name | outcome or column name in analysis data
CCT | CCT
SST | SST
Partnership | PAR
Empathy | EMP
Overall rating | overall_counselor_rating
Client naturalness | client_naturalness_initial / client_naturalness_analysis
```

When all outcomes are stored in long format, the theoretical number of rows is as follows.

```text
60 scripts × 4 raters × 5 outcomes = 1200 rows
```

In analyses by outcome, the number of rows per outcome is as follows.

```text
60 scripts × 4 raters = 240 rows
```

### 10.2 Technical Global and Relational Global data

Technical Global and Relational Global are calculated by rater and script.

The required columns are as follows.

```text
script_id
pair_id
layer
situation
perma_profile
generation_id
rater_id
CCT
SST
PAR
EMP
technical_global
relational_global
good_technical_global
good_relational_global
presentation_order
```

`CCT`, `SST`, `PAR`, and `EMP` are the wide-format values of `rating_analysis` for each outcome. For outcomes with ICC(2,k) below 0.50 to which the median-based re-evaluation and adjudication rules are applied, adjudicated values are used; for outcomes with ICC(2,k) of 0.50 or higher, initial values are used. Technical Global and Relational Global based on initial unadjudicated values are created separately for sensitivity analyses.

The theoretical number of rows is as follows.

```text
60 scripts × 4 raters = 240 rows
```

### 10.3 Behavior code data

Behavior code data are treated as system-output behavior-label counts in which action policies or behavior labels determined in Layer2 are mapped to MITI behavior categories.

The required columns are as follows.

```text
pair_id
situation
perma_profile
generation_id
behavior_source
behavior_coding_rule_version
counselor_utterance_count
GI
Persuade
Persuade_with_Permission
Q
SR
CR
AF
Seek
Emphasize
Confront
```

Because behavior codes are determined in Layer2 and are common to the Layer3 and Layer4 conditions, they are treated in principle as 30-row data at the `pair_id` unit. If the analysis dataset is provided in a 60-row format containing Layer3 and Layer4 rows, duplicates are removed at the `pair_id` unit. If behavior code values do not match within the same `pair_id`, this is treated as a data inconsistency and checked against the source data.

Behavior code data do not include `rater_id`. Rater fixed effects are not included in behavior score analyses.

The theoretical number of rows is as follows.

```text
30 pair-level rows = 5 situations × 3 PERMA profiles × 2 generations
```

### 10.4 Client naturalness data

Client naturalness data are organized at the `source_script_id × rater_id` unit for the primary exploratory analysis and at the `pair_id × rater_id` unit for the sensitivity analysis.

The required columns for the primary exploratory analysis data are as follows.

```text
source_script_id
pair_id
source_layer
situation
perma_profile
generation_id
rater_id
presentation_order
presentation_order_z
client_naturalness_raw
client_naturalness_initial
client_naturalness_initial_median
client_naturalness_absolute_median_diff
client_naturalness_adjudication_flag
client_naturalness_final
client_naturalness_analysis
```

`source_script_id` is the ID of the source script in which the naturalness rating was entered. `source_layer` indicates whether the rating was made in the context of the Layer3 condition or the Layer4 condition. `presentation_order` is the presentation order for each rater, and `presentation_order_z` is the presentation order standardized within rater to mean 0 and standard deviation 1. If the standard deviation is 0, `presentation_order_z = 0`.

`client_naturalness_raw` is the original input on the rating form. `client_naturalness_initial` is the initial independent rating value normalized to a 1–10 numeric value. `client_naturalness_final` is the final rating value when the median-based re-evaluation and adjudication rules in Section 14.4 are applied. When the re-evaluation/adjudication rules are not applied, `client_naturalness_final` is identical to `client_naturalness_initial`. `client_naturalness_analysis` is the value used in the primary exploratory analysis; it is `client_naturalness_final` if ICC(2,k) is below 0.50 and `client_naturalness_initial` if ICC(2,k) is 0.50 or higher.

The client response itself is common to the Layer3 and Layer4 conditions, but the naturalness rating was made within dialogue context. Therefore, if Layer3-context and Layer4-context values differ within the same `pair_id × rater_id`, this discrepancy is not treated as an error requiring selection of a primary value. Both context-specific values are retained in the primary exploratory analysis.

For the Layer3-context and Layer4-context values within the same `pair_id × rater_id`, the following are calculated and reported.

```text
client_naturalness_layer_diff = Layer4 context value − Layer3 context value
client_naturalness_abs_layer_diff = |Layer4 context value − Layer3 context value|
```

For the primary sensitivity-analysis data, the mean of the Layer3-context and Layer4-context values within the same `pair_id × rater_id` is used to create the following.

```text
client_naturalness_pair_mean_initial
client_naturalness_pair_mean_final
client_naturalness_pair_mean_analysis
client_naturalness_pair_available_source_count
```

If both the Layer3-context and Layer4-context values are available, the mean of the two values is used. If only one value is available, the available value is used and `client_naturalness_pair_available_source_count = 1` is recorded. If both are missing, the value is treated as missing.

The theoretical number of rows for the primary exploratory analysis data is as follows.

```text
60 source scripts × 4 raters = 240 rows
```

The theoretical number of rows for the pair-mean sensitivity-analysis data is as follows.

```text
30 pairs × 4 raters = 120 rows
```


## 11. Data validation and preprocessing

Before analysis, the following will be checked.

- There are 60 `script_id` values.
- There are 30 `pair_id` values.
- Each `pair_id` contains one Layer3 script and one Layer4 script.
- In principle, each script has global rating data from four raters.
- `rating_initial`, `rating_final`, and `rating_analysis` are within the range 1.0–5.0.
- `rating_initial`, `rating_final`, and `rating_analysis` are in 0.5-point increments.
- `client_naturalness_initial`, `client_naturalness_final`, and `client_naturalness_analysis` are within the range 1–10.
- Leading numeric values are correctly extracted from string-format naturalness ratings.
- The correspondence among `layer`, `source_layer`, `situation`, `perma_profile`, and `generation_id` is consistent with the generation conditions.
- The actual presentation-order list and `presentation_order` in the analysis dataset match for each `rater_id`.
- `presentation_order_z` is correctly standardized within rater.
- No labels or information from which the Layer condition can be inferred remain in the rating data. However, the analysis dataset retains `layer` and `source_layer` for modeling.
- Behavior codes are non-negative integers.
- If behavior codes are duplicated across Layer conditions within the same `pair_id`, the values are identical.
- For client naturalness, when Layer3-context and Layer4-context values exist within the same `pair_id × rater_id`, the number of discrepancies, distribution of differences, and missingness status are recorded according to Section 10.4.

If the median-based re-evaluation/adjudication rule is applied, the following will also be checked.

- For global ratings, the initial median for each `script_id × outcome` is correctly calculated from the available initial ratings.
- For client naturalness, the initial median for each `source_script_id` is correctly calculated from the available initial ratings.
- The absolute median difference for each individual rating is correctly calculated.
- For the five counselor evaluation indicators, adjudicated values with absolute median differences of at least 1.5 points fall within initial median ±1.0.
- For the five counselor evaluation indicators, adjudicated values with absolute median differences of at least 1.0 but less than 1.5 points fall within initial median ±0.5.
- For client naturalness, adjudicated values with absolute median differences of at least 3.5 points fall within initial median ±2.
- For client naturalness, adjudicated values with absolute median differences of at least 2.5 but less than 3.5 points fall within initial median ±1.
- For cells outside the adjudication target, the initial and analysis values are in principle identical.
- The adjudication log matches `adjudication_flag` or `client_naturalness_adjudication_flag` in the analysis dataset.

If invalid values are found, the source data or rating records will be checked. Values will be corrected only when the correction rationale is clear. If correction is not possible, the value will be treated as missing.

---

## 12. Handling of missing values and division by zero

### 12.1 Missingness in global ratings

If global ratings have missing values, analysis will use available data by outcome.

If a rater is missing only a specific outcome, that rater’s other outcome ratings will be used.

The number and proportion of missing values will be reported by outcome, rater, and Layer condition.

### 12.2 Missingness in Technical Global and Relational Global

Technical Global is calculated only when both CCT and SST are available. If either CCT or SST is missing, Technical Global is missing.

Relational Global is calculated only when both PAR and EMP are available. If either PAR or EMP is missing, Relational Global is missing.

An average will not be created by imputing from only one of the two indicators.

### 12.3 Missingness in client naturalness

If client naturalness has missing values, analyses will use available data.

The number and proportion of missing values will be reported by rater, source_layer, situation, PERMA profile, and situation × PERMA profile.

If no numeric value can be extracted from a string, the value will be treated as missing. If a value outside the 1–10 range is found, the source data will be checked. If correction is not possible, the value will be treated as missing.

### 12.4 Division by zero in behavior scores

Because behavior summary scores may involve division by zero, the following prespecified rules will be used.

#### 12.4.1 When `total_reflection = 0`

```text
total_reflection = SR + CR = 0
```

In this case, `%CR = CR / (SR + CR)` cannot be calculated.

For descriptive Good attainment indicators, `good_pct_complex_reflection = 0` will be used. This is a conservative rule that treats the Good threshold for the percentage of complex reflections as not attained.

For descriptive statistics and models of continuous `%CR`, the observation will be treated as missing.

#### 12.4.2 When `Q = 0` and `total_reflection > 0`

In this case, `R:Q` is mathematically infinite.

For descriptive Good attainment indicators, when there are zero questions and at least one reflection, `good_reflection_question_ratio = 1` will be used.

For descriptive statistics, such observations will not be included in the mean or standard deviation of `R:Q`; the count will be reported separately as observations for which the ratio is infinite because Q = 0. If modeling is needed, an exploratory analysis of `log1p(R:Q)` using finite values only will be conducted.

#### 12.4.3 When `Q = 0` and `total_reflection = 0`

In this case, `R:Q` cannot be calculated.

For descriptive Good attainment indicators, `good_reflection_question_ratio = 0` will be used.

For descriptive statistics and models of continuous `R:Q`, the observation will be treated as missing.

---

## 13. Descriptive statistics

### 13.1 Global ratings

For each primary outcome, the following will be reported.

- Overall rating distribution.
- Mean.
- Standard deviation.
- Median.
- Interquartile range.
- Minimum and maximum.
- Distribution by Layer condition.
- Distribution by situation.
- Distribution by PERMA profile.
- Distribution by situation × PERMA profile.
- Mean, standard deviation, and median by rater.

Because the ratings are ordinal scales, medians, interquartile ranges, and distributions will be emphasized. Means and standard deviations will also be reported for comparison with prior-study reference values and for reader understanding.

For outcomes to which the median-based re-evaluation/adjudication rule is applied because ICC(2,k) is below 0.50, descriptive statistics based on adjudicated values will be reported as the main descriptive results, and descriptive statistics based on initial non-adjudicated values will be reported supplementarily. The number and percentage of adjudicated cells and the mean change before and after adjudication will also be reported.

### 13.2 Technical Global and Relational Global

For Technical Global and Relational Global, the following will be reported.

- Overall mean, standard deviation, median, and interquartile range.
- Mean, standard deviation, median, and interquartile range by Layer condition.
- Proportion attaining `Technical Global >= 4.0`.
- Proportion attaining `Relational Global >= 4.0`.
- Attainment proportion by rater.
- At the script level, the number of scripts for which 0, 1, 2, 3, or 4 raters judged the script as Good.

### 13.3 Behavior codes

For each behavior code, the mean frequency and standard deviation aggregated at the `pair_id` level will be reported.

The same descriptive statistics will also be reported by situation, PERMA profile, and situation × PERMA profile. For the 15 situation × PERMA profile cells, values from the two repetitions in each cell will be shown as far as possible so that variability in individual values, not only the mean, is visible.

For behavior summary scores, the following will be reported.

- `%CR`
- `R:Q`
- Proportion attaining `%CR >= 50%`
- Proportion attaining `R:Q >= 2.0`
- Number of cases with `Q = 0`
- Number of cases with `SR + CR = 0`
- Number of cases with `SR + CR` equal to 1–2
- `Q per counselor utterance`
- `total_reflection per counselor utterance`
- `Total MI-Adherent per counselor utterance`

Because `%CR` and `R:Q` are likely to have skewed distributions, medians and interquartile ranges will also be reported in addition to means and standard deviations.

### 13.4 Client naturalness

For client naturalness, the following will be reported.

- Overall mean, standard deviation, median, interquartile range, minimum, and maximum.
- Mean, standard deviation, and median by rater.
- Mean, standard deviation, and median by `source_layer`.
- Number of matching and non-matching Layer3-context and Layer4-context values within the same `pair_id × rater_id`.
- Distribution of `client_naturalness_layer_diff` and `client_naturalness_abs_layer_diff`.
- Mean, standard deviation, and median by situation.
- Mean, standard deviation, and median by PERMA profile.
- Mean, standard deviation, and median by situation × PERMA profile.
- Distribution or individual values for the 15 situation × PERMA profile cells.

If the median-based re-evaluation/adjudication rule is applied for client naturalness, descriptive statistics based on adjudicated values will be reported as the main results, and descriptive statistics based on initial non-adjudicated values will be reported supplementarily.

---

## 14. Inter-rater reliability

Inter-rater reliability will be reported to show the quality of global ratings and client naturalness ratings. However, it will not be used for rater selection.

### 14.1 Reliability of global ratings

For each primary outcome, the following will be calculated.

- ICC(2,1): absolute-agreement reliability for a single rater.
- ICC(2,k): absolute-agreement reliability when the mean of four raters is used.
- Ordinal Krippendorff’s alpha: a supplementary indicator of agreement for ordinal scales.

ICC stands for intraclass correlation coefficient. ICC(2,1) and ICC(2,k) are estimated based on a two-way random-effects model with an absolute-agreement definition.

Because ICC approximately treats ratings as interval-scaled, ordinal Krippendorff’s alpha will also be reported supplementarily, taking into account that the ratings are nine-category ordinal scales.

If missing values exist, the primary ICC report will be based on outcome-specific complete cases. That is, for each outcome’s ICC calculation, only scripts with ratings from all four raters for that outcome will be treated as complete cases. Analyses using only scripts with complete ratings from all four raters across all five outcomes will not be used as the primary reliability report.

For each outcome’s ICC report, the number of missing values, the number of complete cases, and “N = X scripts with complete ratings from four raters” will be stated.

### 14.2 Reliability of Technical Global and Relational Global

For Technical Global and Relational Global, ICC(2,1), ICC(2,k), and interval Krippendorff’s alpha will be reported supplementarily.

However, because these are derived indicators created from CCT, SST, PAR, and EMP, the primary reliability assessment will prioritize the four original indicators.

If missing values exist, complete cases for Technical Global are scripts for which all four raters have calculable Technical Global values; complete cases for Relational Global are scripts for which all four raters have calculable Relational Global values.

Technical Global and Relational Global are averages of two 0.5-increment global ratings and are treated as derived continuous quantities in 0.25 increments. Therefore, Krippendorff’s alpha will be calculated as interval alpha rather than ordinal alpha.

### 14.3 Reliability of client naturalness

For client naturalness, inter-rater reliability will be reported supplementarily.

- ICC(2,1)
- ICC(2,k)
- Interval Krippendorff’s alpha

Because client naturalness is treated as a 1–10 numerical scale, it is approximated as continuous for ICC. Because the primary exploratory analysis retains context-including ratings, the main reliability report will calculate context-including reliability at the `source_script_id` level. If missing values exist, `source_script_id` values with naturalness ratings from all four raters will be used as complete cases for the primary report, and the number of missing values and complete cases will be reported.

As supplementary information, reliability may also be reported using pair-mean naturalness values at the `pair_id` level.

The scale settings for reliability indicators are fixed as follows.

```text
Indicator | ICC | Krippendorff's alpha
CCT, SST, PAR, EMP, Overall | Report ICC(2,1), ICC(2,k) as continuous approximations | Supplementary ordinal alpha
Technical Global, Relational Global | Report ICC(2,1), ICC(2,k) as continuous approximations | Supplementary interval alpha
Client naturalness | Report ICC(2,1), ICC(2,k) as continuous approximations | Supplementary interval alpha
Behavior codes | Not calculated | Not calculated
```

### 14.4 Re-evaluation/adjudication rule when the ICC criterion is not met

Inter-rater reliability is treated as a descriptive and supplementary indicator of measurement quality and interpretive uncertainty. The inter-rater reliability criterion is that the outcome-specific ICC(2,k) is at least 0.50. If ICC(2,k) is below 0.50, the following median-based re-evaluation/adjudication rule is applied for that outcome.

Even when ICC(2,k) is below 0.50, that alone will not lead to rater exclusion, rater-specific weighting, outcome exclusion, or downgrading of an outcome from a primary outcome to an exploratory outcome. Under low reliability, rather than excluding raters, all cells are reviewed, individual ratings are rechecked using the initial median as the reference, and final post-adjudication rating values are created.

As a rule, re-evaluation is conducted by the same rater who provided the initial rating. The analysis lead confirms that the re-evaluated value falls within the pre-defined allowable range and that a reason based on the rating criteria has been recorded. The analysis lead performs this confirmation without reviewing Layer-condition-specific summaries, Hypothesis 1 script-level summaries for the Layer3 condition, or primary analysis model estimates.

Raters who do not know the design details of the Layer conditions are not shown Layer-condition labels. Even when a researcher who knows the design details of the Layer conditions is involved in re-evaluation or confirmation, they will not use information beyond the general expected direction of individual responses, and they will not refer to Layer-specific summaries or primary analysis results.

The values of `adjudication_flag` and `client_naturalness_adjudication_flag` are fixed as follows.

```text
not_applicable: not subject to adjudication because the ICC criterion is met
checked_no_change: outcome subject to adjudication, but no change made
adjudicated_changed: value changed by re-evaluation/adjudication
adjudicated_confirmed: threshold met, but initial value retained after rechecking
missing_or_unresolvable: missing or unresolvable
```

#### 14.4.1 Re-evaluation/adjudication rule for the five counselor-rating indicators

The five counselor-rating indicators, namely CCT, SST, PAR, EMP, and Overall counselor rating, are ratings in 0.5-point increments from 1.0 to 5.0, giving a total of nine categories. If ICC(2,k) is below 0.50 for these outcomes, all `script_id × rater_id` cells for the 60 scripts are reviewed and the following rules are applied.

For each `script_id × outcome`, the initial median is calculated from the four initial rating values. If missing values exist, the median is calculated from the available initial ratings of three or more raters. If two or fewer raters are available, the relevant `script_id × outcome` is recorded as unadjudicable, and its treatment in the primary analysis follows the missing-data rules in Chapter 12.

For each rater’s initial rating, the following are calculated.

```text
Median difference = initial rating value − initial median
Absolute median difference = |initial rating value − initial median|
```

```text
Individual ratings with an absolute median difference of 1.5 points or more:
    Re-evaluate/adjudicate so that the final rating falls within initial median ± 1.0.

Individual ratings with an absolute median difference of 1.0 point or more but less than 1.5 points:
    Re-evaluate/adjudicate so that the final rating falls within initial median ± 0.5.

Individual ratings with an absolute median difference of less than 1.0 point:
    Retain the initial rating in principle.
```

Here, initial median ± 1.0 or initial median ± 0.5 refers to the allowable range from the median. Mechanical agreement with the median is not required. Within the allowable range, the rater selects the most appropriate value in light of the rating criteria for the relevant outcome. Preserving the direction of the initial rating is allowed, but artificially creating variability is not intended.

Final ratings are selected in principle from valid values in 0.5-point increments between 1.0 and 5.0. Even when the median of four raters is the mean of the two central values and thus becomes a 0.25-increment value such as 3.25 or 3.75, the allowable range is calculated using that initial median as the reference. The final rating is selected from the valid 0.5-increment values within the allowable range.

#### 14.4.2 Re-evaluation/adjudication rule for client naturalness

Client naturalness is a numerical scale from 1 to 10. In the primary reliability evaluation, given that naturalness ratings were made within dialogue context, `source_script_id` is used as the evaluation-target unit. If the context-embedded ICC(2,k) for client naturalness is below 0.50, all `source_script_id × rater_id` cells for the 60 `source_script_id` values are reviewed and the following rules are applied.

For each `source_script_id`, the initial median is calculated from the initial naturalness ratings of the four raters. If missing values exist, the median is calculated from the available initial ratings of three or more raters. If two or fewer raters are available, the relevant `source_script_id` is recorded as unadjudicable, and its treatment in the primary analysis follows the missing-data rules in Chapter 12.

Because the scale width of the five counselor-rating indicators is 4 and the scale width of client naturalness is 9, the following rules are used for client naturalness by converting the counselor-rating criteria according to scale width.

```text
Individual ratings with an absolute median difference of 3.5 points or more:
    Re-evaluate/adjudicate so that the final rating falls within initial median ± 2 points.

Individual ratings with an absolute median difference of 2.5 points or more but less than 3.5 points:
    Re-evaluate/adjudicate so that the final rating falls within initial median ± 1 point.

Individual ratings with an absolute median difference of less than 2.5 points:
    Retain the initial rating in principle.
```

This rule converts the counselor-rating criteria “median difference of 1.5 points or more” and “median difference of 1.0 point or more but less than 1.5 points” to the 1–10 client naturalness scale. For client naturalness as well, mechanical agreement with the median is not required; within the allowable range, the most appropriate value is selected in light of the naturalness of the client response.

Final ratings for client naturalness are selected in principle from integer values from 1 to 10. If the initial median is a 0.5-increment value such as 5.5, an integer value within the allowable range is selected.

When the pair-mean sensitivity analysis is conducted, post-adjudication values are first created at the `source_script_id` unit, and then Layer3-context and Layer4-context values within the same `pair_id × rater_id` are averaged.

#### 14.4.3 Re-evaluation/adjudication log

If re-evaluation/adjudication is conducted, the following are stored as a log.

- `script_id` or `source_script_id`
- `pair_id`
- `source_layer` (for client naturalness)
- `outcome`
- `rater_id`
- Initial rating value
- Initial median
- Absolute median difference
- Applied adjudication category
- Allowable range
- Final rating value
- Reason for modification or confirmation result
- Adjudication date
- Adjudicator or confirmer

The re-evaluation/adjudication log is stored separately from the analysis dataset. In reporting, the number of adjudicated cells, adjudication rate, mean change, and ICCs before and after adjudication are described by outcome.

#### 14.4.4 Analytical handling of adjudicated and initial non-adjudicated values

For outcomes to which the re-evaluation/adjudication rules are applied because ICC(2,k) is below 0.50, the adjudicated individual rating values are used as the primary analysis values. The same model using initial unadjudicated values is conducted as a sensitivity analysis.

For outcomes with ICC(2,k) of 0.50 or higher to which the re-evaluation/adjudication rules are not applied, the initial rating values are used as the primary analysis values.

Even when adjudicated values are used, the individual rating structure at the rater × script unit or rater × source_script unit is retained. In the primary analysis models, secondary analysis models, exploratory models, and sensitivity analyses using initial unadjudicated values, `rater_id` is incorporated into the model to adjust for systematic rater severity or leniency. In principle, `rater_id` is treated as a fixed effect, and rater random-effect models are limited to sensitivity analyses.

The post-adjudication ICC is not an indicator of inter-rater reliability for the initial independent ratings. It is interpreted as the degree of agreement in the median-based re-evaluated/adjudicated data.

### 14.5 Reporting and interpretation of reliability indicators

For outcomes with low ICC or Krippendorff's alpha, the following are reported.

- ICC(2,1), ICC(2,k), Krippendorff's alpha based on initial independent ratings, and their 95% confidence intervals where possible.
- Mean, standard deviation, median, and rating distribution by rater.
- Whether median-based re-evaluation/adjudication was applied.
- Number of adjudicated cells, adjudication rate, and mean change before and after adjudication.
- ICC(2,1), ICC(2,k), and Krippendorff's alpha based on adjudicated data.
- Consistency with sensitivity analyses using initial unadjudicated values.

Even if reliability is low and the direction or magnitude of the Layer effect changes substantially in sensitivity analyses, the primary analysis results are not replaced. Instead, the report states in the main text or limitations that the certainty of the conclusion for the relevant outcome is low, that results may depend on between-rater variability, and that the outcome should be interpreted cautiously.

If data inconsistencies such as input errors, out-of-range scale values, rater ID mix-ups, or duplicate registration of the same script are found during the reliability calculation process, the source data are checked according to the data-validation rules in Chapter 11. Corrections of data inconsistencies are limited to correcting record errors and are not performed for the purpose of improving reliability indicators.

### 14.6 Reliability and validity of behavior codes

The behavior codes in this study are not assigned by raters. Instead, they are treated as system-output behavior-label counts in which action policies or behavior labels determined in Layer2 are mapped to MITI behavior categories. Therefore, inter-rater reliability is not calculated for behavior codes.

For behavior codes, the following are recorded instead.

- `behavior_source`
- `behavior_coding_rule_version`
- Description of extraction and aggregation rules
- That behavior codes are determined in Layer2 and common to the Layer3 and Layer4 conditions

#### 14.6.1 Explicit limitations regarding behavior-code validity

System-output behavior-label counts in which action policies or behavior labels determined in Layer2 are mapped to MITI behavior categories do not involve independent coding by human coders. Therefore, the behavior-code-derived summary scores in this study (`%CR`, `R:Q`, and their Good-threshold achievement) differ in nature from indicators that have undergone standard MITI 4.2.1 inter-human-coder reliability verification.

Given this point, analyses based on behavior summary scores are reported as exploratory and descriptive. In this study, because behavior codes are common across Layers, no Layer effect is estimated. The main exploratory interest regarding behavior codes is differences across life situation × PERMA profile combinations.

---

## 15. Primary analysis: global ratings

### 15.1 Model type

Because the primary outcomes are 9-category ordinal scales, the primary analysis uses a CLMM (cumulative link mixed model).

A CLMM is a model that can handle ordinal-scale outcomes while including random effects such as pair differences and script differences.

### 15.2 Primary analysis model

For each outcome, the following model is fitted.

```text
rating_ord ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

Here:

- `rating_ord` is the 9-category ordinal rating created from `rating_analysis`.
- `layer` has two levels, Layer3 and Layer4, with Layer3 as the reference category.
- `rater_id` is the ID of the four raters and is included as a fixed effect.
- `(1 | pair_id)` is the random intercept for pairs sharing the same life situation, the same PERMA profile, the same repeated generation ID, and a common client response.
- `(1 | script_id)` is the random intercept representing correlations among ratings from four raters for the same script.

In the primary analysis, rating values are not aggregated to script-level means or medians; individual ratings at the rater × script unit are used. If the median-based re-evaluation and adjudication rules in Section 14.4 are applied because the outcome-specific ICC(2,k) is below 0.50, adjudicated individual rating values are used as the primary analysis values. If ICC(2,k) is 0.50 or higher, initial rating values are used as the primary analysis values. The `rater_id` fixed effect is included to adjust for systematic severity or leniency that may exist among the four raters. The same model using initial unadjudicated values is conducted as the sensitivity analysis in Section 21.8.

Each `script_id` belongs to only one `pair_id`, and each `pair_id` contains two `script_id` values, one for the Layer3 condition and one for the Layer4 condition. Therefore, in the data structure, `script_id` is nested within `pair_id`. In this SAP, the `pair_id` random intercept is treated as within-pair covariation, and the `script_id` random intercept is treated as the correlation among multiple rater ratings for the same script.

However, because each `pair_id` contains only two `script_id` values, simultaneous identification of the `pair_id` variance and `script_id` variance may be unstable. Whether both random effects can be estimated simultaneously is determined based on the convergence checks and boundary-estimate checks in Section 22.1. If simultaneous estimation is unstable, the fallback procedure removes the `script_id` random effect first in principle and retains the `pair_id` random effect as much as possible, given that the primary estimand is the within-pair Layer difference.

Life situation and PERMA profile are absorbed within pairs by `pair_id`; therefore, they are not included as fixed effects in the confirmatory primary analysis model. Effects of life situation and PERMA profile are handled in exploratory analyses.

The conceptual R model formula is as follows.

```r
ordinal::clmm(
  rating_ord ~ layer + rater_id +
    (1 | pair_id) + (1 | script_id),
  data = dat,
  link = "logit"
)
```

### 15.3 Hypothesis 2: test of the Layer effect

The Layer effect is the confirmatory test in the primary analysis.

The significance of the Layer effect is evaluated using a likelihood ratio test comparing the following full and reduced models.

Full model:

```text
rating_ord ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

Reduced model:

```text
rating_ord ~ rater_id + (1 | pair_id) + (1 | script_id)
```

The cumulative odds ratio for the Layer4 condition is reported as the effect size.

```text
OR = exp(beta_layer4)
```

OR means odds ratio. OR > 1 means that, within the same pair, the Layer4 condition is more likely to fall into higher rating categories.

The following values are reported.

- Coefficient estimate
- Cumulative odds ratio
- 95% confidence interval
- p-value
- Holm-adjusted p-value
- Estimated category probabilities or high-rating category probabilities by condition

For Hypothesis 2, no single binary decision such as “supported” or “not supported” is made. For all five outcomes, the OR estimate, 95% confidence interval, unadjusted p-value, and Holm-adjusted p-value are reported in parallel. The number of outcomes showing the OR > 1 direction and the outcomes with Holm-adjusted p-values below 0.05 are described. Interpretation of Hypothesis 2 is described comprehensively based on the direction of OR estimates, confidence intervals, significance, and consistency across outcomes.

### 15.4 Exploratory test of the life-situation effect

The life-situation effect is treated as an exploratory analysis.

Because life situation and PERMA profile are directly included in the model, the exploratory model does not include a `pair_id` random effect. This is because `pair_id` corresponds to life situation, PERMA profile, and repeated generation ID, and including `pair_id` simultaneously with life situation and PERMA profile would make identification unstable.

The exploratory model is as follows.

```text
rating_ord ~ layer + situation + perma_profile + rater_id + (1 | script_id)
```

The significance of the life-situation effect is evaluated using a likelihood ratio test against a reduced model that removes `situation` from the above model.

A “main effect is observed” means that the p-value for the life-situation main effect from the likelihood ratio test is below 0.05 after Holm adjustment within the five primary outcomes.

For outcomes in which a main effect is observed, all pairwise comparisons between life situations are conducted. Model-based contrasts are used for all pairwise comparisons, and p-values are adjusted using the Holm method within the set of contrasts conducted. However, because this is an exploratory analysis, effect sizes, confidence intervals, and rating distributions are emphasized more than p-values.

### 15.5 Exploratory test of the PERMA-profile effect

The PERMA-profile effect is treated as an exploratory analysis.

The exploratory model is the same as in Section 15.4.

```text
rating_ord ~ layer + situation + perma_profile + rater_id + (1 | script_id)
```

The significance of the PERMA-profile effect is evaluated using a likelihood ratio test against a reduced model that removes `perma_profile` from the above model.

A “main effect is observed” means that the p-value for the PERMA-profile main effect from the likelihood ratio test is below 0.05 after Holm adjustment within the five primary outcomes.

For outcomes in which a main effect is observed, all pairwise comparisons between PERMA profiles are conducted. Model-based contrasts are used for all pairwise comparisons, and p-values are adjusted using the Holm method within the set of contrasts conducted. However, because this is an exploratory analysis, effect sizes, confidence intervals, and rating distributions are emphasized more than p-values.

### 15.6 Exploratory interactions for primary outcomes

For primary outcomes, the following interactions are examined exploratorily.

- Layer × life situation
- Layer × PERMA profile
- Life situation × PERMA profile

The model is as follows.

```text
rating_ord ~ layer * situation + layer * perma_profile + situation * perma_profile + rater_id
             + (1 | script_id)
```

Because the model is complex relative to the sample size and estimation may be unstable, this analysis is reported exploratorily. If the model does not converge, simplified models including each interaction separately are used.

### 15.7 Checking the proportional odds assumption

The CLMM assumes the proportional odds assumption, meaning that the effects of explanatory variables are the same at each threshold.

The primary analysis is conducted using the planned CLMM, and the following are checked supplementarily.

- Distribution of rating categories.
- Presence of extremely sparse categories.
- Consistency of direction with a linear mixed model treating ratings as numeric scores.
- Supplementary tests of the proportional odds assumption.
- Results of proportional-odds-relaxed models or category-collapsed models when pre-specified criteria are met.

Supplementary tests of the proportional odds assumption are conducted for each primary outcome using an auxiliary CLM without random effects. The auxiliary CLM has the following fixed-effect structure.

```text
rating_ord ~ layer + rater_id
```

For this auxiliary CLM, `ordinal::nominalTest` and `ordinal::scaleTest` are conducted. For outcomes in which at least one of the two tests has a p-value below 0.05, concern regarding the proportional odds assumption is noted and a model relaxing the proportional odds assumption is checked supplementarily. If both p-values are 0.05 or higher, the proportional-odds-relaxed model is not conducted.

The proportional-odds-relaxed model does not replace the primary analysis. If an equivalent relaxed model cannot be stably estimated in a CLMM with random effects, results from the auxiliary CLM or a partial proportional odds model are reported as reference information.

Even when concern regarding the proportional odds assumption exists, the primary analysis model is not changed post hoc for convenience. The issue is described as a limitation in the interpretation of results.

---

## 16. Hypothesis 1: comparison with reference values from prior work

Hypothesis 1 descriptively compares the 30 scripts in the Layer3 condition with human-rated values from prior work, referred to as reference values from prior work.

Because this comparison is not a randomized comparison within the same experiment, it is not treated as a confirmatory test. Because this study and the prior study differ in target scripts, rater composition, and evaluation design, the reference values in this section are positioned not as benchmarks in the strict sense of external criteria, but as literature values reported in parallel. To emphasize this point, this SAP avoids the term “benchmark” and uses the expression “reference value.”

In Hypothesis 1, “exceeds” is a descriptive expression indicating whether the point estimate for the Layer3 condition is higher than each pre-fixed reference mean for GPT-SMDP and Opus-SMDP. No binary success/failure judgment is made, and no superiority test, non-inferiority test, non-inferiority margin, p-value-based confirmatory judgment, or standardized effect size based on the prior-study standard deviation is used. Whether the 95% confidence interval crosses the reference mean is used to describe uncertainty but not as a criterion for success.

### 16.1 Fixed reference values

The reference information comprises the human-rated means and standard deviations for GPT-SMDP and Opus-SMDP obtained from Section 2.2 and Table 2 of the masked prior reference study; each model-specific mean is fixed as an independent reference value. The values for the two models are not combined into a simple average. This is because a simple average would lose information and because reporting them separately enables a stricter descriptive comparison of whether both model-specific means are exceeded.

```text
                  GPT-SMDP mean (SD)   Opus-SMDP mean (SD)
CCT reference         3.41 (0.74)          3.44 (0.87)
SST reference         3.22 (0.85)          3.38 (0.85)
PAR reference         3.20 (0.79)          2.99 (0.96)
EMP reference         3.12 (0.91)          3.22 (0.96)
OVR/Overall reference 3.22 (0.65)          3.28 (0.83)
```

Table 2 of the masked prior reference study presents descriptive statistics for CCT, SST, PAR, EMP, and OVR for each counselor AI, namely Opus-SMDP, GPT-zero, and GPT-SMDP, by rater group: Human, Sonnet, o3, and Gemini. In this SAP, the means and standard deviations in the Human column for Opus-SMDP and GPT-SMDP are extracted and reported as reference information. The prior-study mean is the point estimate used for the descriptive comparison. The prior-study standard deviation is reported only to describe variability in the prior study and is not used to make a success/failure decision, conduct a superiority or non-inferiority test, define a non-inferiority margin, or calculate a standardized effect size.

The prior study’s OVR and this study’s Overall counselor rating are the same definition of overall counselor evaluation based on the same five-point rubric. Therefore, the reference-value comparison for Overall counselor rating is treated as a descriptive comparison with prior-study reference values, just as for CCT, SST, PAR, and EMP. However, because target scripts, rater composition, and evaluation design differ, the comparison is limited to descriptive comparison and is not a confirmatory test.

### 16.2 Comparison procedure

In Hypothesis 1, because the reference values from prior work are presented as means, this study also uses the mean as the primary comparison metric. The prior-study standard deviations are included only as descriptive context. However, the unit of comparison is the script, not a simple average of the 120 rater × script rows treated as independent observations.

Low reliability is defined as an outcome-specific ICC(2,k) below 0.50 based on initial independent ratings. The decision uses ICC(2,k) based on the outcome-specific complete cases defined in Chapter 14. The low-reliability decision, median-based re-evaluation/adjudication, creation of adjudicated values, and Hypothesis 1 script-level summaries for the Layer3 condition are conducted before reviewing Layer-condition-specific summaries and primary analysis model estimates.

For outcomes with ICC(2,k) of 0.50 or higher, the following regular procedure is used.

1. Extract the 30 scripts in the Layer3 condition.
2. For each script, calculate the mean of the four raters’ initial ratings.
3. Using the 30 scripts as the unit, calculate the mean, standard deviation, median, and interquartile range.
4. Calculate a 95% confidence interval using script-level bootstrapping.
5. Describe the difference from the pre-fixed GPT-SMDP and Opus-SMDP reference means.

For outcomes with ICC(2,k) below 0.50, after applying the median-based re-evaluation and adjudication rules defined in Section 14.4, the following procedure is used.

1. Extract the 30 scripts in the Layer3 condition.
2. For each script, calculate the mean of the four raters’ adjudicated ratings.
3. Using the 30 scripts as the unit, calculate the mean, standard deviation, median, and interquartile range.
4. In the primary descriptive comparison for Hypothesis 1, use the mean and standard deviation based on the adjudicated-rating means, and compare the Layer3 mean point estimate with the pre-fixed GPT-SMDP and Opus-SMDP reference means.
5. Calculate a 95% confidence interval using script-level bootstrapping.
6. Describe the difference from the pre-fixed GPT-SMDP and Opus-SMDP reference means.
7. Report the same aggregation using means of the four initial unadjudicated ratings as a sensitivity analysis.

When all four raters have ratings for all scripts, the simple average of the 120 rater × script rows and the mean of script means across the 30 scripts are numerically identical. However, if missing values exist, the simple average of 120 rows gives greater weight to scripts with more raters, so it is not used as the primary aggregation method.

If missing values occur in the regular procedure, for each outcome, only scripts with ratings from three or more available raters are used in the Hypothesis 1 comparison. When ratings from three or more raters are available, the mean of the available raters is used as the value for that script. Scripts with two or fewer available raters are excluded from the Hypothesis 1 comparison for that outcome. If scripts are excluded because of missingness, the number excluded, the number of scripts included in the comparison, and the number of available raters for each script are reported.

When re-evaluated/adjudicated values are used, only scripts with ratings from three or more available raters are used in the Hypothesis 1 comparison. If some ratings are unadjudicable, the mean of the available adjudicated ratings is used as the value for that script. If two or fewer raters are available, that script is excluded from the Hypothesis 1 comparison for that outcome.

Because global ratings are ordinal scales, the mean is treated as a practical summary indicator for ensuring comparability with prior-study reference values. Means and standard deviations are reported for this study and for the prior study, but the Hypothesis 1 comparison is based on mean point estimates. Prior-study standard deviations are not used for success/failure decisions, superiority tests, non-inferiority margins, or standardized effect sizes. Medians, interquartile ranges, and rating-category distributions are also reported, and the rating distribution is not interpreted based only on means. For outcomes using re-evaluated/adjudicated values, differences from results based on initial unadjudicated values are described.

Bootstrap specifications are fixed as follows.

```text
Unit: 30 scripts in the Layer3 condition
Method: nonparametric bootstrap at the script level
Number of iterations: 10,000
Confidence interval: two-sided 95% confidence interval using the percentile method
seed: 20260507
Quantity calculated during resampling: If ICC(2,k) is 0.50 or higher, each outcome's initial rater mean is used as the script value. If ICC(2,k) is below 0.50, the rater mean after median-based re-evaluation/adjudication is used as the script value. The 30-script mean and the difference from each reference mean are recalculated.
```

When reporting, the following descriptive categories are used as needed.

- The point estimate exceeded both reference means.
- The point estimate exceeded only one reference mean.
- The point estimate did not exceed either reference mean.

A reporting example is as follows.

```text
The Layer3-condition script-level mean CCT score was X.XX, with a standard
deviation of X.XX (95% CI: [X.XX, X.XX]), and was compared with the pre-defined
reference values from prior work (GPT-SMDP: 3.41; Opus-SMDP: 3.44). The
difference from GPT-SMDP was +X.XX, and the difference from Opus-SMDP was +X.XX.
The corresponding prior-study standard deviations were reported descriptively
(GPT-SMDP: 0.74; Opus-SMDP: 0.87) and were not used for a decision rule,
non-inferiority margin, or standardized effect size.
If ICC(2,k) was below 0.50 and median-based re-evaluation/adjudication was
applied, the report states whether it was applied, the number of adjudicated
cells, that adjudicated values were used, and the results of the sensitivity
analysis using initial unadjudicated values. Because the design and target differ
from prior work, the results were interpreted descriptively.
```

---

## 17. Secondary analysis: Good-threshold achievement for Technical/Relational Global

### 17.1 Target outcomes

The secondary outcomes for Good-threshold achievement are the following two outcomes.

```text
good_technical_global
good_relational_global
```

`good_technical_global` and `good_relational_global` are binary outcomes derived from global ratings.

`good_pct_complex_reflection` and `good_reflection_question_ratio` derived from behavior codes are not included as secondary outcomes in this section because they are based on behavior codes common across Layers.

### 17.2 Analysis model

Good-threshold achievement for Technical Global and Relational Global is a binary outcome created from rater-specific ratings. Therefore, the observation unit in the analysis is rater × script (240 observations).

For CCT, SST, PAR, and EMP, which constitute Technical Global and Relational Global, if the median-based re-evaluation and adjudication rules in Section 14.4 are applied because ICC(2,k) is below 0.50, Technical Global and Relational Global are calculated from adjudicated values and used as the primary analysis values. The same analysis using Technical Global and Relational Global calculated from initial unadjudicated values is conducted as a sensitivity analysis. In all analyses, rater ID is incorporated into the model.

For each outcome, the following model is fitted.

```text
good_outcome ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

The conceptual R model formula is as follows.

```r
lme4::glmer(
  good_outcome ~ layer + rater_id +
    (1 | pair_id) + (1 | script_id),
  data = dat,
  family = binomial(link = "logit")
)
```

If convergence is unstable with `lme4::glmer`, an equivalent model using `glmmTMB` is attempted.

The odds ratio from this model refers to “the probability that a given rater rates a script in a given condition as Good,” and has a different interpretation from a script-level consensus-based achievement rate, such as how many of the four raters rated the script as Good. This point is also reflected in Section 24.5 (interpretive notes).

### 17.3 Test of the Layer effect

For Good-threshold achievement outcomes, the Layer effect is a secondary analysis.

The significance of the Layer effect is evaluated using a likelihood ratio test comparing a full model including Layer and a reduced model excluding Layer.

The following values are reported.

- Odds ratio for the Layer4 condition
- 95% confidence interval
- p-value
- Holm-adjusted p-value
- Good-threshold achievement proportion by condition
- Model-estimated achievement probability by condition
- Number of scripts for which 0, 1, 2, 3, or 4 raters judged the script as Good in each Layer condition

### 17.4 Exploration of life situation and PERMA effects

For Good-threshold achievement of Technical Global and Relational Global, main effects of life situation and PERMA profile are examined exploratorily.

The exploratory model is as follows.

```text
good_outcome ~ layer + situation + perma_profile + rater_id + (1 | script_id)
```

Interactions such as life situation × PERMA profile are described exploratorily after checking convergence status and achievement counts in each cell. If complete separation occurs, reporting centers on condition-specific achievement proportions and script-level distributions of the number of Good ratings, rather than insisting on model estimation.

### 17.5 Handling complete and quasi-complete separation

For binary outcomes, if all or nearly all observations in the full data or in a specific condition achieve the Good threshold, complete or quasi-complete separation may occur in logistic models.

In that case, the following steps are used.

1. Switch from `glmer` to `glmmTMB`.
2. If the `script_id` random-effect variance is a boundary estimate, record this as a boundary estimate and fit a supplementary model without `script_id`.
3. If the `pair_id` random effect is a boundary estimate, but the model converges and the Layer effect can be estimated, prioritize reporting the model retaining `pair_id`. The model excluding `pair_id` is treated as a supplementary analysis.
4. If models including random effects are unstable, conduct a supplementary fixed-effect logistic regression, `good_outcome ~ layer + rater_id`.
5. If complete or quasi-complete separation remains, report Firth-corrected logistic regression or descriptive statistics for condition-specific achievement proportions.
6. State that model estimation was not valid, and center reporting on condition-specific achievement proportions, the script-level distribution of the number of Good ratings, and paired differences.

---

## 18. Exploratory analysis: client naturalness

### 18.1 Analysis unit

As a client response itself, client naturalness is common to the Layer3 and Layer4 conditions. However, because raters evaluated the client response within dialogue context, the same client response may have different naturalness ratings depending on the counselor-response context in the Layer3 and Layer4 conditions.

Therefore, in the primary exploratory analysis, Layer3-context and Layer4-context values are not removed as simple duplicates; instead, they are analyzed as context-embedded ratings at the `source_script_id × rater_id` unit.

The theoretical number of analysis rows is as follows.

```text
60 source scripts × 4 raters = 240 rows
```

In the sensitivity analysis, Layer3-context and Layer4-context values within the same `pair_id × rater_id` are averaged and analyzed as data at the `pair_id × rater_id` unit.

```text
30 pairs × 4 raters = 120 rows
```

### 18.2 Primary exploratory model

Client naturalness is treated as a 1–10 numerical scale, and the primary exploratory model uses a linear mixed model.

If the context-embedded ICC(2,k) for client naturalness is below 0.50 and the median-based re-evaluation/adjudication rules in Section 14.4 are applied, adjudicated values are used as the primary exploratory analysis values. The same model using initial unadjudicated values is conducted as a sensitivity analysis. In all analyses, `rater_id` is included as a fixed effect to adjust for systematic severity or leniency among raters.

The primary exploratory model is as follows.

```text
client_naturalness_analysis ~ situation * perma_profile + source_layer
                              + presentation_order_z + rater_id
                              + (1 | pair_id) + (1 | source_script_id)
```

Here:

- `client_naturalness_analysis` is the 1–10 naturalness rating; it is the adjudicated value when ICC(2,k) is below 0.50 and the initial value when ICC(2,k) is 0.50 or higher.
- `situation * perma_profile` represents life situation, PERMA profile, and their interaction.
- `source_layer` indicates whether the naturalness rating was made in the context of the Layer3 condition or the Layer4 condition. It is an adjustment variable for contextual effects and is not interpreted as a Layer effect regarding counselor quality.
- `presentation_order_z` is the presentation order standardized within rater and is included to adjust for possible fatigue, learning, or changes in rating standards.
- `rater_id` is a fixed effect adjusting for rater leniency or severity.
- `(1 | pair_id)` is a random intercept representing correlations among ratings derived from the same client-response pair.
- `(1 | source_script_id)` is a random intercept representing correlations among multiple rater ratings for the same script context.

The conceptual R model formula is as follows.

```r
lme4::lmer(
  client_naturalness_analysis ~ situation * perma_profile + source_layer +
    presentation_order_z + rater_id +
    (1 | pair_id) + (1 | source_script_id),
  data = dat_client,
  REML = TRUE
)
```

### 18.3 Test of the interaction

The presence of the life situation × PERMA profile interaction is evaluated exploratorily by comparing the following full and reduced models.

Full model:

```text
client_naturalness_analysis ~ situation * perma_profile + source_layer
                              + presentation_order_z + rater_id
                              + (1 | pair_id) + (1 | source_script_id)
```

Reduced model:

```text
client_naturalness_analysis ~ situation + perma_profile + source_layer
                              + presentation_order_z + rater_id
                              + (1 | pair_id) + (1 | source_script_id)
```

The test is based on a likelihood ratio test. Because models with different fixed-effect structures are compared, both the full and reduced models are fitted using ML estimation with `REML = FALSE`. Results are interpreted exploratorily, emphasizing means, medians, and distributions in the 15 life situation × PERMA profile cells, not only p-values.

The conceptual R code for the likelihood ratio test is as follows.

```r
fit_full_ml <- lme4::lmer(
  client_naturalness_analysis ~ situation * perma_profile + source_layer +
    presentation_order_z + rater_id +
    (1 | pair_id) + (1 | source_script_id),
  data = dat_client,
  REML = FALSE
)

fit_reduced_ml <- lme4::lmer(
  client_naturalness_analysis ~ situation + perma_profile + source_layer +
    presentation_order_z + rater_id +
    (1 | pair_id) + (1 | source_script_id),
  data = dat_client,
  REML = FALSE
)

anova(fit_reduced_ml, fit_full_ml)
```

When reporting final estimates, 95% confidence intervals, and cell estimated means, results from re-estimating the same fixed-effect structure with `REML = TRUE` are used by default. The report table states that the LRT p-value is based on ML estimation and the estimates are based on REML estimation.

The coefficient for `source_layer` and the difference between Layer3-context and Layer4-context values within the same `pair_id × rater_id` are reported as descriptive and supplementary information indicating context dependence. They are not treated as confirmatory or secondary tests of a Layer effect.

### 18.4 Handling model instability

If the `source_script_id` random effect or the `pair_id` random effect variance is near zero, or if the model does not converge, the following steps are used.

1. A supplementary model excluding the `source_script_id` random effect is conducted.

```text
client_naturalness_analysis ~ situation * perma_profile + source_layer
                              + presentation_order_z + rater_id
                              + (1 | pair_id)
```

2. If the `pair_id` random effect is a boundary estimate but the model converges and the main fixed effects can be estimated, the model retaining `pair_id` is prioritized for reporting.

3. If estimation is impossible in a model retaining `pair_id`, a supplementary linear model without random effects is conducted.

```text
client_naturalness_analysis ~ situation * perma_profile + source_layer
                              + presentation_order_z + rater_id
```

4. If instability remains, the sensitivity-analysis model using means at the `pair_id × rater_id` unit is reported.

```text
client_naturalness_pair_mean_analysis ~ situation * perma_profile + rater_id
                                        + (1 | pair_id)
```

5. If instability still remains, no model estimation is conducted; reporting centers on descriptive statistics for the 15 cells, descriptive statistics by `source_layer`, and the distribution of within-`pair_id × rater_id` differences.

### 18.5 Pair-mean sensitivity analysis

As the primary sensitivity analysis, the mean of the Layer3-context and Layer4-context values within the same `pair_id × rater_id` is used.

```text
client_naturalness_pair_mean_analysis ~ situation * perma_profile + rater_id
                                        + (1 | pair_id)
```

This sensitivity analysis is used to check whether the results for life situation × PERMA profile are consistent with the primary context-embedded model after averaging contextual differences.

In the pair-mean sensitivity analysis, `source_layer` is not included in the model because it is averaged out. If the effect of presentation order needs to be checked supplementarily, a model adding the mean of the two presentation orders within the same `pair_id × rater_id` as `presentation_order_pair_mean_z` can be conducted supplementarily. However, this model is treated as supplementary and not as the primary sensitivity analysis.

### 18.6 Reporting policy

For client naturalness, the following are reported.

- Overall and rater-specific descriptive statistics.
- Descriptive statistics by `source_layer`.
- Number of matches, number of discrepancies, and distribution of differences between Layer3-context and Layer4-context values within the same `pair_id × rater_id`.
- Descriptive statistics for the 15 life situation × PERMA profile cells.
- Estimates, 95% confidence intervals, and p-values from the primary context-embedded model.
- Results of the pair-mean sensitivity analysis.
- If the model is unstable, the reason for model failure and descriptive statistics.

The `source_layer` result for client naturalness is a description of context dependence indicating how the same client response was perceived in different counselor-response contexts. It is not reported as a confirmatory result for a Layer effect regarding counselor quality.

---

## 19. Exploratory analysis: differences in behavior codes across life situation × PERMA profile

### 19.1 Analysis unit

Behavior codes are determined in Layer2 and are common to the Layer3 and Layer4 conditions. Therefore, Layer-condition rows are not duplicated; behavior-code data are analyzed at the `pair_id` unit.

The theoretical number of analysis rows is as follows.

```text
30 pairs = 5 situations × 3 PERMA profiles × 2 generations
```

### 19.2 Primary reporting approach

For behavior codes, the sample size is 30 pairs, with only two repeated generations in each of the 15 life situation × PERMA profile cells. Therefore, the primary report is descriptive statistics rather than inferential statistics.

The following will be reported.

- Mean, standard deviation, median, and individual values of each behavior code by life situation × PERMA profile.
- Mean, standard deviation, median, and individual values of `%CR`, `R:Q`, Total reflections, Total MI-Adherent, and Total MI Non-Adherent by life situation × PERMA profile.
- Counts of cells or pairs for which `Q = 0`, `SR + CR = 0`, or `SR + CR` is 1 to 2.

### 19.3 Exploratory models

In addition to descriptive statistics, exploratory models for major behavior summary scores will be conducted supplementarily. However, the primary report remains the descriptive statistics for the 15 cells, and inferential models will not be used for confirmatory conclusions.

The major behavior summary scores to be modeled are as follows.

- `Q`
- `total_reflection = SR + CR`
- `%CR`
- `R:Q`
- `Total MI-Adherent`
- `Total MI Non-Adherent`

The model is as follows.

```text
behavior_summary ~ situation * perma_profile
```

For count indicators, model results may be unstable because of overdispersion or many zero values; therefore, linear-model results will be treated as auxiliary. Additional models are not freely selected after reviewing results; they are limited to the following prespecified models.

```text
Q: Poisson GLM. A negative binomial GLM is added only when overdispersion is clear.
total_reflection = SR + CR: Poisson GLM. A negative binomial GLM is added only when overdispersion is clear.
%CR: A linear model is added supplementarily. If values are concentrated at 0 or 100, no model is fitted and only descriptive statistics are reported.
R:Q: A log1p(R:Q) linear model using only finite values is added supplementarily.
Total MI-Adherent: Poisson GLM. A negative binomial GLM is added only when overdispersion is clear.
Total MI Non-Adherent: If zeros are frequent, no model is fitted and only descriptive statistics are reported.
```

Here, “overdispersion is clear” means that, under the same fixed-effect structure, the AIC of the negative binomial GLM is at least 4 lower than the AIC of the Poisson GLM. If the AIC difference is less than 4, the negative binomial GLM is not reported as a supplementary analysis, and the Poisson GLM results and descriptive statistics are reported. If the negative binomial GLM does not converge, this is recorded as failure of the negative binomial GLM, and the results are described exploratorily based on the Poisson GLM and the descriptive statistics for the 15 cells.

Because there are only two repetitions per cell, model p-values are treated only as auxiliary screening indicators, and conclusions in the main text are based on descriptive statistics.

Because `R:Q` is prone to skewness and may take infinite values, an exploratory model using `log1p(R:Q)` among finite values only is also conducted supplementarily.

### 19.4 Describing Good-threshold achievement

Good-threshold achievement derived from behavior codes is not a secondary outcome for Layer effects. The following two indicators are reported as descriptive statistics by life situation × PERMA profile.

```text
good_pct_complex_reflection
good_reflection_question_ratio
```

For each of the 15 cells, the number and proportion of achievements are reported. Because each cell has only two repetitions, interaction tests using logistic regression are not conducted in principle. If they must be conducted supplementarily, complete separation is checked, and Firth-corrected regression or descriptive statistics are prioritized.

### 19.5 Reporting policy

For the behavior-code analysis by life situation × PERMA profile, the following will be reported.

- Descriptive statistics for the 15 cells.
- Exploratory model results for major behavior summary scores.
- If models are unstable, the reasons for model failure and descriptive statistics.
- The reason why Layer comparisons are not conducted.

---

## 20. Multiple comparisons

### 20.1 Confirmatory primary analysis family

The confirmatory primary analysis family is the Layer effect in Hypothesis 2.

The target outcomes are the following five outcomes.

- CCT
- SST
- PAR
- EMP
- Overall counselor rating

The p-values for the Layer effect for these five outcomes will be adjusted using the Holm method.

The confirmatory family is always fixed as the above five outcomes. For each outcome, if the first-choice CLMM is valid, the CLMM p-value for the Layer effect is used. If the first-choice CLMM is not valid according to prespecified criteria and the analysis moves to the fallback analysis in Section 22.1, the Layer-effect p-value obtained from that prespecified fallback analysis is used for that outcome. Therefore, an outcome is not excluded from the Holm-adjusted family merely because it moved to a fallback analysis.

If a valid p-value cannot be calculated even in the fallback analysis, the outcome is reported as having no p-value, and the main Holm-adjustment table explicitly marks the outcome as “not estimable.” Even in this case, the target outcome is not replaced post hoc with another outcome.

Moving to a fallback analysis according to prespecified conditions is not itself treated as an SAP deviation. However, if the fallback decision or the set of outcomes included in the Holm adjustment is changed after reviewing the Layer-effect estimate, p-value, or condition-specific results, this is recorded as an SAP deviation.

Primary conclusions are described based on Holm-adjusted p-values, effect sizes, 95% confidence intervals, and consistency of direction across outcomes. No binary success/failure or supported/not-supported decision is made for Hypothesis 2 as a whole.

### 20.2 Secondary family for Good-threshold achievement

For the Layer effect on Good-threshold achievement, the following two outcomes are treated as one secondary family.

- Technical Global >= 4.0
- Relational Global >= 4.0

The p-values for the Layer effect for these two outcomes will be adjusted using the Holm method.

### 20.3 Exploratory families for life situation and PERMA profile

Life-situation effects and PERMA-profile effects are treated as exploratory analyses.

For each of these effects, p-values for main-effect tests across the five primary outcomes will be adjusted using the Holm method.

A “main effect is observed” means that, after Holm adjustment within the five primary outcomes for the relevant main-effect test, the adjusted p-value is less than 0.05. Pairwise comparisons are conducted only for outcomes in which the main effect is observed. P-values for pairwise comparisons are also adjusted using the Holm method within the set of contrasts actually conducted.

In exploratory analyses, interpretation emphasizes effect sizes, confidence intervals, rating distributions, and condition-specific estimates, not p-values alone.

### 20.4 Exploratory analyses of client naturalness and behavior codes

The analyses of life situation × PERMA profile for client naturalness and behavior codes are prespecified exploratory analyses.

Because client naturalness is a single outcome, no multiple-comparison adjustment is applied to the test of the life situation × PERMA profile interaction itself. However, numerous pairwise comparisons among the 15 cells are not conducted in principle. If conducted, they are treated as exploratory results and adjusted using the Holm method.

In the client-naturalness model, `source_layer` is a variable for adjusting and describing contextual effects. It is not included in the confirmatory primary or secondary Layer-effect families.

For behavior codes, multiple codes and derived indicators are handled. Therefore, p-values are treated as auxiliary screening indicators. The primary report is the descriptive statistics for the 15 cells, and strong conclusions are not drawn on the basis of statistical significance after multiple-comparison adjustment.

---

## 21. Sensitivity analyses

### 21.1 Rater random-effect model

In the primary analysis of global ratings, raters are treated as fixed effects. As a sensitivity analysis, models treating raters as random effects are conducted.

For global ratings, the following model is used.

```text
rating_ord ~ layer + (1 | rater_id) + (1 | pair_id) + (1 | script_id)
```

For Good-threshold achievement for Technical Global and Relational Global, the following model is used.

```text
good_outcome ~ layer + (1 | rater_id) + (1 | pair_id) + (1 | script_id)
```

For behavior-code-derived indicators, rater information does not exist; therefore, this sensitivity analysis is not conducted.

### 21.2 Leave-one-rater-out analysis

For global ratings, Good-threshold achievement derived from global ratings, and client naturalness, analyses are conducted after excluding one rater at a time.

This is a sensitivity analysis to check whether results depend on a particular rater, not a procedure for selecting raters.

If the four raters are denoted A, B, C, and D, the following four analyses are conducted.

- Excluding rater A
- Excluding rater B
- Excluding rater C
- Excluding rater D

For each analysis, the direction, effect size, 95% confidence interval, and p-value for the Layer effect or the life situation × PERMA profile interaction are compared with the primary analysis or the primary exploratory analysis.

For client naturalness, leave-one-rater-out analysis is conducted for the primary context-embedded model. The model formula is the model in Section 18.2 with the relevant rater excluded.

If the direction of the Layer effect is reversed in the leave-one-rater-out analysis, or if the interpretation of the life situation × PERMA profile interaction for client naturalness changes substantially, the primary conclusion is not automatically changed. Instead, the outcome for which the direction or interpretation changed, the excluded rater, and the effect size with and without that rater are reported. In addition, that rater’s rating characteristics are described, including mean rating, standard deviation, median, difference from the other raters, and presence or absence of an extreme rating distribution by outcome; possible dependence on a specific rater is reported as a limitation.

### 21.3 Linear mixed model treating ratings as numeric scores

As a supplementary analysis, the primary outcomes are treated as numeric scores rather than ordinal scales and analyzed using a linear mixed model.

```text
rating_num ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

This analysis is not the primary analysis. It is an auxiliary analysis to check whether the ordinal-scale model results have the same direction in a simpler model.

### 21.4 Script-level aggregated analysis

For each script, the mean of four rater ratings is calculated, and a simplified analysis at the 60-script level is conducted supplementarily. For outcomes to which the median-based re-evaluation/adjudication rule is applied because ICC(2,k) is below 0.50, the mean of post-adjudication ratings is used as the primary aggregated value; means and medians based on initial unadjudicated values are conducted only as sensitivity analyses.

For Hypothesis 2, a paired analysis using the Layer3–Layer4 differences across the 30 pairs is conducted.

This analysis is used to check whether mixed-model results are consistent with simple script-level aggregated results.

For each script and each outcome, the primary aggregated value is the mean of available rater ratings. Here, rater ratings refer to post-adjudication ratings for outcomes to which the median-based re-evaluation/adjudication rule is applied because ICC(2,k) is below 0.50, and to initial ratings for outcomes with ICC(2,k) of 0.50 or higher. In principle, scripts with ratings from all four raters are used. When missing values exist, the number of available raters is reported, and the mean is calculated only when ratings from three or more raters are available. If ratings from two or fewer raters are available, the script-level aggregated value is treated as missing.

In the supplementary analysis for Hypothesis 2, for each of the 30 pairs, the pair difference is calculated by subtracting the script mean for the Layer3 condition from the script mean for the Layer4 condition. In the sensitivity analysis using median aggregation, it is checked whether the direction is consistent with the mean-aggregation results. If results differ substantially between mean aggregation and median aggregation, this is described as the influence of between-rater variability or outliers, and conclusions from the primary analysis prioritize the mixed model.

### 21.5 Analysis adjusted for script length

As a sensitivity analysis, a model including the number of counselor utterances as a covariate is conducted.

```text
rating_ord ~ layer + rater_id + counselor_utterance_count
             + (1 | pair_id) + (1 | script_id)
```

The primary indicator of script length is the number of counselor utterances. Counselor-character count and total script-character count are reported as descriptive statistics.

This analysis is an auxiliary analysis to check whether the Layer effect remains after adjusting for length differences.

### 21.6 Sensitivity analysis for division-by-zero rules in behavior scores

For observations in which behavior summary scores cannot be calculated because `total_reflection = 0` or `Q = 0`, conservative zero coding is used for descriptive Good-achievement indicators.

As a sensitivity analysis, descriptive statistics treating these observations as missing are also checked.

### 21.7 Non-paired exploratory model including life situation and PERMA profile

Because the primary analysis includes a `pair_id` random effect, life situation and PERMA profile are not included as fixed effects.

As a sensitivity and exploratory analysis, the following non-paired model is conducted.

```text
rating_ord ~ layer + situation + perma_profile + rater_id + (1 | script_id)
```

This model directly estimates the main effects of life situation and PERMA profile. However, conclusions of the confirmatory primary analysis, which targets within-pair comparisons, prioritize the paired CLMM in Section 15.2.

### 21.8 Sensitivity analysis using initial unadjudicated values

For outcomes to which the median-based re-evaluation/adjudication rule in Section 14.4 is applied because ICC(2,k) is below 0.50, sensitivity analyses using initial unadjudicated values are conducted.

For Hypothesis 2 in global ratings, the same model as the primary analysis is fitted using initial unadjudicated values.

```text
rating_ord_initial ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

For Good-threshold achievement for Technical Global and Relational Global, derived indicators are calculated from initial unadjudicated values, and the same model as the primary analysis is fitted.

```text
good_outcome_initial ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

For client naturalness, the initial unadjudicated values are analyzed using a model with the same structure as the primary exploratory model.

```text
client_naturalness_initial ~ situation * perma_profile + source_layer
                             + presentation_order_z + rater_id
                             + (1 | pair_id) + (1 | source_script_id)
```

For the pair-mean sensitivity analysis, a supplementary model using `client_naturalness_pair_mean_initial` based on initial unadjudicated values is also conducted.

```text
client_naturalness_pair_mean_initial ~ situation * perma_profile + rater_id
                                       + (1 | pair_id)
```

For Hypothesis 1, script-level rater means for the Layer3 condition based on initial unadjudicated values are calculated and compared with the mean, standard deviation, and differences from reference means based on adjudicated values. Prior-study standard deviations remain descriptive only and are not used to calculate standardized effect sizes.

In sensitivity analyses using initial unadjudicated values, rater ID is always incorporated into the model. Models not including rater ID are limited to reference descriptive analyses that do not adjust for rater differences and are not treated as the primary sensitivity analyses.

Sensitivity analyses describe how much the effect direction, effect size, 95% confidence interval, p-value, and interpretation of the conclusion change between the primary analysis using adjudicated values and the results using initial unadjudicated values.

### 21.9 Sensitivity analysis adjusted for presentation order

In global ratings, presentation order is not included as a covariate in the primary analysis. However, if the “large imbalance” defined in Chapter 4 is identified, a sensitivity analysis adjusted for presentation order is conducted.

```text
rating_ord ~ layer + rater_id + presentation_order_z
             + (1 | pair_id) + (1 | script_id)
```

`presentation_order_z` is presentation order standardized within rater. This sensitivity analysis is an auxiliary analysis to check whether the Layer effect strongly depends on imbalance in presentation order, and it does not replace the primary analysis.

For Good-threshold achievement for Technical Global and Relational Global, if a large presentation-order imbalance is identified, a sensitivity analysis similarly adding `presentation_order_z` is conducted.

For client naturalness, `presentation_order_z` is included in the primary exploratory model; therefore, the additional sensitivity analysis in this section is not required in principle. However, because presentation order is averaged in the pair-mean sensitivity analysis, a supplementary model adding `presentation_order_pair_mean_z` may be reported if necessary.

---

## 22. Prespecified rules for model non-convergence

### 22.1 Global-rating models

As the first step, the primary analysis model is fitted while retaining the 9 categories.

```text
rating_ord ~ layer + rater_id + (1 | pair_id) + (1 | script_id)
```

Non-convergence is defined as meeting any of the following criteria, and the determination is made before reviewing Layer-effect estimates or condition-specific results.

- A convergence warning is returned by `ordinal::clmm`.
- The condition number of the Hessian matrix is extremely large, or the inverse matrix is judged not computable.

If a random-effect variance is near zero, for example variance < 1e-6, this is distinguished from non-convergence and recorded as a boundary estimate or singular fit.

If a model including random intercepts for both `pair_id` and `script_id` cannot be estimated, this is recorded as instability in identifying variance components under the nested structure. In this case as well, because the primary estimand is the within-pair Layer difference, the `script_id` random effect is removed first in principle.

In the case of boundary estimation, the following supplementary analyses are conducted in order.

1. If the `script_id` random effect is a boundary estimate, a model without the `script_id` random effect is conducted.

```text
rating_ord ~ layer + rater_id + (1 | pair_id)
```

2. Even if the `pair_id` random effect is the first component to become a boundary estimate, if the model converges and the Layer effect can be estimated, the model retaining `pair_id` is prioritized as the primary analysis and reported as having a boundary estimate or singular fit. Because the primary estimand is the within-pair Layer difference, removing `pair_id` is treated as supplementary rather than primary.

3. Only when the `pair_id` random effect is not estimable and a model retaining `pair_id` cannot estimate the Layer effect is a fixed-effect-only CLM conducted supplementarily.

```text
rating_ord ~ layer + rater_id
```

4. If the model still does not converge, the script-level aggregated paired analysis of the 30 pairs is reported.

The analyst is responsible for judging non-convergence or boundary estimation. If non-convergence or boundary estimation occurs, the analysis log records the date and time of judgment, the judge, target outcome, model formula, basis for judgment, type of information checked, and fallback steps implemented. If the issue constitutes an SAP deviation, the deviation-recording format in Appendix B is used. If p-values or estimates for the Layer effect are reviewed at the time of judgment, this is recorded as an SAP deviation at that point.

Category collapsing is performed only when the 9-category CLMM has convergence failure or is not estimable and a category with fewer than 5 observations exists across the 240 rater × script observations for that outcome.

When category collapsing is performed, the following conditions are met.

- Only adjacent categories are collapsed.
- Collapsing proceeds from low-end or high-end categories.
- The collapsing rule and post-collapsing categories are stated explicitly.
- The collapsing method is not changed after reviewing the Layer-effect estimate, p-value, or condition-specific results.

The analysis after category collapsing is treated as a fallback when the primary analysis fails, and this is stated in reporting.

If category collapsing is performed, the following outcome-specific collapsing map is used. The same collapsing scheme is adopted for each outcome, but it is explicitly fixed by outcome so that the destination of collapsing is not changed after reviewing results.

```text
Outcome | First-stage collapsing | Second-stage collapsing | If still invalid after the second stage
CCT | 1.0+1.5, 4.5+5.0 | 1.0+1.5+2.0, 4.0+4.5+5.0 | Move to the 30-pair aggregated analysis
SST | 1.0+1.5, 4.5+5.0 | 1.0+1.5+2.0, 4.0+4.5+5.0 | Move to the 30-pair aggregated analysis
PAR | 1.0+1.5, 4.5+5.0 | 1.0+1.5+2.0, 4.0+4.5+5.0 | Move to the 30-pair aggregated analysis
EMP | 1.0+1.5, 4.5+5.0 | 1.0+1.5+2.0, 4.0+4.5+5.0 | Move to the 30-pair aggregated analysis
Overall | 1.0+1.5, 4.5+5.0 | 1.0+1.5+2.0, 4.0+4.5+5.0 | Move to the 30-pair aggregated analysis
```

If the model still does not converge after the second-stage collapsing, or if sparsity remains in intermediate categories, no additional ad hoc category collapsing is performed. The category-collapsed model is recorded as invalid, and the analysis moves to the 30-pair aggregated analysis.

### 22.2 Good-threshold achievement models

If a binary logistic mixed model does not converge, the following steps are taken in order.

1. Switch from `lme4::glmer` to `glmmTMB`.
2. If the `script_id` random effect is a boundary estimate or is not estimable, conduct a supplementary model without `script_id`.
3. Even if the `pair_id` random effect is a boundary estimate, if the model converges and the Layer effect can be estimated, prioritize the model retaining `pair_id`. A model without `pair_id` is treated as a supplementary analysis.
4. If the model is still unstable, conduct a fixed-effect-only logistic regression.
5. If complete or quasi-complete separation occurs, report Firth-corrected logistic regression, condition-specific achievement proportions, script-level distribution of the number of raters rating Good, and descriptive statistics for pair differences.

### 22.3 Client-naturalness models

If the client-naturalness model does not converge, the sequence in Section 18.4 is followed.

If the model is ultimately unstable, reporting centers on descriptive statistics for the 15 life situation × PERMA profile cells, descriptive statistics by `source_layer`, the distribution of differences between Layer3-context and Layer4-context values within the same `pair_id × rater_id`, and the pair-mean sensitivity analysis.

### 22.4 Behavior-code models

If exploratory models for behavior codes are unstable, no model estimation is conducted, and the descriptive statistics for the 15 life situation × PERMA profile cells are used as the primary report.

---

## 23. Software and implementation policy

Analyses are conducted primarily in Python, with R called as needed.

### 23.1 Processing conducted in Python

Python is used for the following tasks.

- Data loading
- Data validation
- Missingness checks
- Conversion to long format
- Calculation of Technical Global and Relational Global
- Numeric extraction for client naturalness
- Calculation of behavior summary scores
- Descriptive statistics
- Calculation of inter-rater reliability
- Extraction of targets for median-based re-evaluation/adjudication
- Creation of adjudicated values, analysis values, and datasets for sensitivity analyses using initial unadjudicated values
- Visualization
- Exporting CSV files for R analyses
- Reading R analysis results
- Formatting result tables

CSV output is UTF-8 with a byte order mark (BOM).

```python
encoding = "utf-8-sig"
```

### 23.2 Processing conducted in R

R is used for the following tasks.

- Cumulative link mixed models using `ordinal::clmm`
- Model estimates and pairwise comparisons using `emmeans`
- Binary logistic mixed models using `lme4::glmer` or `glmmTMB`
- Linear mixed models using `lme4::lmer`
- Model diagnostics as needed

When R is called from Python, the default approach is to call `Rscript` via `subprocess`, rather than using `rpy2`.

This makes input and output files on both the Python and R sides explicit, improving reproducibility and debuggability.

### 23.3 Reproducibility

During analysis, the following are recorded.

- Python version.
- R version.
- Names and versions of packages used.
- Random seed.
- Creation date and time of the analysis dataset.
- Version of the analysis code.
- Presence or absence of deviations from SAP v3.7.

---

## 24. Reporting policy

### 24.1 Primary analysis results

For each primary outcome, the following are reported.

- Fixed-effect estimates from the CLMM
- Cumulative odds ratio
- 95% confidence interval
- p-value
- Holm-adjusted p-value
- Estimated category probabilities or high-rating category probabilities by condition
- Rating distribution

For Hypothesis 2, Holm-adjusted p-values are reported as important decision information, but no binary success/failure or supported/not-supported decision is made for the hypothesis as a whole. Reporting describes the number of outcomes with OR > 1, outcomes with Holm-adjusted p-values below 0.05, the width of confidence intervals, and consistency of direction across outcomes.

For outcomes to which the median-based re-evaluation/adjudication rule is applied because ICC(2,k) is below 0.50, the primary analysis table explicitly states that adjudicated values were used. In addition, effect sizes, 95% confidence intervals, and p-values from sensitivity analyses using initial unadjudicated values are shown in supplementary tables.

### 24.2 Secondary analysis results

For Good-threshold achievement for Technical Global and Relational Global, the following are reported.

- Proportion achieving Technical Global >= 4.0
- Proportion achieving Relational Global >= 4.0
- Odds ratio for the Layer condition
- 95% confidence interval
- p-value
- Holm-adjusted p-value
- For each Layer condition, the number of scripts rated Good by 0, 1, 2, 3, or 4 of the four raters

### 24.3 Exploratory analysis results

For main effects of life situation and PERMA profile, the following are reported as exploratory analyses.

- Likelihood ratio test for the main effect
- Holm-adjusted p-value
- Condition-specific estimates
- Pairwise comparison results
- Effect sizes and 95% confidence intervals

For client naturalness, the following are reported.

- Descriptive statistics overall and by rater
- Descriptive statistics by `source_layer`
- Number of matches, number of discrepancies, and distribution of differences between Layer3-context and Layer4-context values within the same `pair_id × rater_id`
- Descriptive statistics for the 15 life situation × PERMA profile cells
- Results of the life situation × PERMA profile interaction model
- Results of the pair-mean sensitivity analysis
- Fallback results when the model is unstable

For behavior codes, the following are reported.

- Mean frequency and standard deviation for each behavior code
- Descriptive statistics for `%CR`, `R:Q`, Total reflections, Total MI-Adherent, and Total MI Non-Adherent
- Descriptive statistics for `Q`, `total_reflection`, and `Total MI-Adherent` per counselor utterance
- Achievement proportions for `%CR >= 50%` and `R:Q >= 2.0`
- Counts of `Q = 0`, `SR + CR = 0`, and small-denominator observations
- Descriptive statistics for the 15 life situation × PERMA profile cells
- Exploratory model results as needed

### 24.4 Inter-rater reliability

For inter-rater reliability, the following are reported for each primary outcome.

- ICC(2,1)
- ICC(2,k)
- Ordinal Krippendorff's alpha

For Technical Global and Relational Global, ICC(2,1), ICC(2,k), and interval Krippendorff's alpha are reported as supplementary reliability indicators.

For client naturalness, ICC(2,1), ICC(2,k), and interval Krippendorff's alpha are reported supplementarily.

Even if ICC or Krippendorff's alpha is low, no rater exclusion, rater-specific weighting, or outcome exclusion is performed. If the median-based re-evaluation/adjudication rule is applied because outcome-specific ICC(2,k) is below 0.50, the number of adjudicated cells, adjudication rate, mean change before and after adjudication, initial ICC, and post-adjudication ICC are reported. The post-adjudication ICC is interpreted not as inter-rater reliability for the initial independent ratings, but as agreement in the post-adjudication data. If adjudicated values are used as the primary analysis values, consistency with sensitivity analyses using initial unadjudicated values is also reported.

For behavior codes, inter-rater reliability is not calculated; instead, the extraction and aggregation rules for behavior codes are described.

### 24.5 Interpretive cautions

This study is a dialogue simulation study and does not directly test behavior change or improvement in flourishing among real clients.

MITI is originally an evaluation method for a defined segment of an interview. Because the present study applies it to Japanese text scripts, results are interpreted cautiously as global ratings informed by MITI 4.2.1, that is, MITI-informed ratings.

In this study, the change goal is not fixed in advance for each life situation × PERMA profile. Therefore, CCT and SST are approximate ratings based on the change direction raters can infer from the script text, and may differ from MITI ratings based on an explicitly specified change goal.

Technical Global and Relational Global are derived indicators calculated from CCT, SST, PAR, and EMP. Because they overlap in information with the primary outcomes, they do not replace conclusions from the primary analysis and are interpreted as supplementary evaluations from the perspective of Good-threshold achievement. The multiple-comparison families for the primary analysis (Hypothesis 2) and derived indicators are handled separately because they correspond to qualitatively different outcome types, namely ordinal rating probabilities and binary threshold achievement. Results for derived indicators are not independent new evidence separate from the primary analysis; when results are in the same direction, they are positioned as a robustness check for the primary analysis results.

#### 24.5.1 Interpretation of odds ratios for Technical/Relational Global

Analyses of Good-threshold achievement for Technical Global and Relational Global are conducted at the rater × script unit (240 observations). The odds ratios obtained from these models refer to the probability that a given rater rates a given script in a given condition as Good, and differ from script-level consensus-based achievement rates, such as how many of the four raters rated a script as Good. In reporting, model-estimated odds ratios and script-level achievement proportions are both presented, and their relationship is stated explicitly.

#### 24.5.2 Limitations regarding rater blinding

Raters who do not know the design details of the Layer conditions are not shown Layer-condition labels. Even when a researcher who knows the design details of the Layer conditions is involved in re-evaluation or confirmation, they will not use information beyond the general expected direction of individual responses, and they will not refer to Layer-specific summaries or primary analysis results.

However, systematic differences in response structure, depth, length, and related characteristics may arise between the Layer3 and Layer4 conditions. These differences are part of the Layer-condition effect itself; therefore, the possibility that raters infer the Layer condition from response content cannot be eliminated in principle.

In this study, raters are not asked to make post hoc guesses about Layer condition. Guess accuracy is not judged to function as an indicator of blinding quality because the cues for guessing, such as response texture, and the outcome, namely ratings of response quality, lie on the same dimension and are not independent. For example, even if “guess accuracy above chance level” were observed, it would be impossible to distinguish whether this reflected expectation bias or a true quality difference in Layer4.

Therefore, the estimated effect of Layer condition is reported with an interpretive range that may include both true quality differences due to structural improvement and expectation effects inferred from response characteristics. This is not an absence of blinding verification, but an interpretive limitation inherent to this design.

#### 24.5.3 Limitations of behavior-code-derived summary scores

`%CR`, `R:Q`, and their Good-threshold achievement are calculated from system-output behavior-label counts in which action policies or behavior labels determined in Layer2 are mapped to MITI behavior categories. In this study, no standard validity verification involving independent coding by human coders is performed. Therefore, these indicators differ in nature from MITI 4.2.1 behavior counts that have undergone standard inter-human-coder reliability verification.

In addition, because behavior codes are determined in Layer2 and common to the Layer3 and Layer4 conditions, no Layer effect is estimated for behavior codes. Differences by life situation × PERMA profile are reported exploratorily, but because the number of repetitions per cell is small, strong confirmatory conclusions are avoided.

#### 24.5.4 Limitations regarding client naturalness

Client naturalness is an exploratory indicator of how natural raters perceived the client response to be. It is not counselor quality itself, but an indicator of the realism of the simulated client side.

The client response itself is common to the Layer3 and Layer4 conditions. However, because ratings in this study are made within dialogue context rather than for isolated utterances, the naturalness rating for the same client response may differ depending on the immediately preceding or surrounding counselor-response context. Therefore, this SAP does not treat the Layer3-context and Layer4-context values as simple duplicate values to be removed, and adjusts for `source_layer` and presentation order in the primary exploratory analysis.

The difference associated with `source_layer` describes the context dependence of how the same client response is perceived under different counselor-response contexts. Therefore, it is not interpreted as a confirmatory result for a Layer effect on counselor quality.

Differences by life situation × PERMA profile are treated as exploratory findings to understand in which condition settings the client AI response is more likely to appear unnatural.

---

## Appendix A. Draft wording for the Methods section

The following text can be reused in the Data Analysis section of the manuscript.

```text
In this study, four raters evaluated 60 Japanese counseling scripts. Each rating
indicator was based on the 1–5 global ratings of the Motivational Interviewing
Treatment Integrity (MITI) 4.2.1, but because the rating form allowed 0.5-point
increments, ratings were analyzed as a 9-category ordinal scale from 1.0 to 5.0.
A 0.5-point score was used when the response was judged to fall between two
adjacent integer anchors. The primary evaluation indicators were Cultivating
Change Talk (CCT), Softening Sustain Talk (SST), Partnership (PAR), Empathy
(EMP), and Overall counselor rating, an independent rating based on a five-point
rubric defined for this study.

In the primary analysis, each rater’s rating for each script was used as the
observation unit, and a cumulative link mixed model (CLMM) was fitted for each
outcome. Fixed effects were Layer condition (Layer3 vs. Layer4) and rater ID.
Including rater ID as a fixed effect adjusted for systematic differences in rater
severity. Layer3–Layer4 pairs sharing a common client response were defined as
`pair_id`, and a random intercept for `pair_id` was included in the model. A
random intercept for `script_id` was also included to account for correlations
among the four rater ratings of the same script. The primary model was
`rating_ord ~ layer + rater_id + (1 | pair_id) + (1 | script_id)`. Because life
situation and PERMA profile were fixed within `pair_id`, they were not included
as fixed effects in the confirmatory primary analysis and were handled in
exploratory analyses.

The effect of Layer condition was reported as a cumulative odds ratio and 95%
confidence interval, with Layer3 as the reference category. The significance of
the Layer effect was evaluated by a likelihood ratio test against a reduced model
without Layer. The primary confirmatory analysis was the Layer effect, and
p-values for the five outcomes CCT, SST, PAR, EMP, and Overall rating were
adjusted using the Holm method. For outcomes in which the first-choice CLMM was
invalid for prespecified reasons, the Layer-effect p-value from the prespecified
fallback analysis was included in the same confirmatory family. No single
success/failure decision was made for Hypothesis 2 as a whole; interpretation was
based on the effect sizes, confidence intervals, adjusted p-values, and
consistency of direction across outcomes.

As secondary outcomes, Technical Global was calculated as (CCT + SST) / 2 and
Relational Global as (PAR + EMP) / 2. Each was treated as a binary outcome
indicating whether the value was 4.0 or higher. Because these outcomes were
modeled at the rater × script unit (240 observations), the odds ratio was
interpreted as applying to the probability that a rater would rate a script in a
given condition as Good.

Client-side naturalness was treated as an exploratory outcome on a 1–10 scale
based on the client naturalness column of the rating form. When string-format
inputs were present, the leading numerical value was extracted. The client
response itself was common to the Layer3 and Layer4 conditions, but raters
evaluated client responses within dialogue context. Therefore, the same client
response could receive different Layer3-context and Layer4-context values. The
primary exploratory analysis retained context-embedded ratings at the
`source_script_id × rater` unit. The model was
`client_naturalness_analysis ~ situation * perma_profile + source_layer +
presentation_order_z + rater_id + (1 | pair_id) + (1 | source_script_id)`.
`source_layer` was included to adjust for contextual effects and was not
interpreted as a Layer effect on counselor quality. As a sensitivity analysis,
pair-mean data averaging the Layer3-context and Layer4-context values within the
same `pair_id × rater` were also analyzed.

Referring to the behavior counts in MITI 4.2.1, the percentage of Complex
Reflections (%CR) was defined as CR / (SR + CR), and the Reflection-to-Question
ratio (R:Q) was defined as (SR + CR) / Q. Behavior codes were not assigned by
raters; instead, they were treated as system-output behavior-label counts in
which action policies or behavior labels determined in Layer2 were mapped to
MITI behavior categories. Because behavior codes were common to the Layer3 and
Layer4 conditions, no Layer effect was estimated for behavior-code-derived
indicators. Instead, differences in behavior codes and behavior summary scores
across life situation × PERMA profile combinations were reported exploratorily
and descriptively at the `pair_id` unit. Because no independent human coding was
conducted, behavior-code-derived summary scores were interpreted exploratorily.
Supplementarily, Q, total_reflection, and Total MI-Adherent per counselor
utterance were described.

For Hypothesis 1, human-rated means and standard deviations from prior work were
used as reference information. GPT-SMDP and Opus-SMDP human-rated means were
listed as independent reference values and compared descriptively with the
Layer3-condition script-level score mean in the present study. The corresponding
prior-study standard deviations were reported only as descriptive variability
and were not used for a success/failure decision, superiority or
non-inferiority test, non-inferiority margin, or standardized effect size. For
outcomes with ICC(2,k) below 0.50 based on initial
independent ratings, all cells were re-evaluated/adjudicated using the initial
median for each `script_id × outcome` as the reference. For the five counselor
rating indicators, individual ratings 1.5 points or more away from the median
were brought within median ± 1.0, and ratings 1.0 point or more but less than
1.5 points away from the median were brought within median ± 0.5. For client
naturalness, using the initial median at the `source_script_id` unit as the
reference and accounting for scale width, individual ratings 3.5 points or more
away from the median were brought within median ± 2, and ratings 2.5 points or
more but less than 3.5 points away from the median were brought within median ±
1. Mechanical agreement with the median was not required; the most appropriate
value within the allowable range was selected in light of the rating criteria.
Adjudicated values were used in the primary analysis, and the same analyses using
initial unadjudicated values were conducted as sensitivity analyses. All
rater-rating models included rater ID to adjust for systematic differences in
rater severity. Because the prior study and the present study differ in design
and target scripts, no confirmatory tests were conducted for this comparison;
only descriptive comparisons were reported.
```

---

## Appendix B. Recording SAP deviations

If any of the following changes occur after this SAP is finalized, they will be recorded as SAP deviations in the analysis report or manuscript.

- It is found that the actual timing of finalization differs from the timing stated in this SAP.
- Change in the number of raters.
- Change in primary outcomes.
- Change from 9-category ratings to 5-category ratings.
- Addition of `change_goal` post hoc and use of it in the primary analysis.
- Change in the reference values for Hypothesis 1.
- Change in the definition of `pair_id`.
- Change in the primary analysis model.
- Change in the median-based re-evaluation/adjudication rule when the ICC criterion is not met.
- Change in the policy that re-evaluation is conducted in principle by the original rater.
- Change in the policy of using adjudicated values as the primary analysis values and initial unadjudicated values as sensitivity-analysis values.
- Change from rater fixed effects to rater random effects in the primary analysis.
- Change in the source or extraction rules for behavior codes.
- Use of behavior codes in inferential statistics for Layer comparisons.
- Use of client naturalness in inferential statistics for Layer comparisons concerning counselor quality.
- Post hoc removal of `source_layer` or `presentation_order_z` from the primary exploratory analysis of client naturalness.
- Change in the Good threshold for Technical Global or Relational Global.
- Addition of interaction terms to the confirmatory primary analysis.
- Adjustment for script length in the primary analysis.
- Change in thresholds for behavior summary scores.
- Change in the handling of missing values or division by zero.
- Change in the multiple-comparison correction method.
- Change from fixing the confirmatory primary analysis family at five outcomes.

Applying a prespecified fallback for non-convergence, category collapsing, or supplementary analysis before reviewing Layer-effect estimates, p-values, or condition-specific results is not itself treated as an SAP deviation. However, if the application decision, model selection, category-collapsing method, or Holm-adjustment target is changed after reviewing results, this is recorded as an SAP deviation.

When a deviation is recorded, the following information is retained.

```text
Date of deviation:
Description of deviation:
Reason for deviation:
Before or after reviewing primary results:
Impact on primary analysis:
Reporting location:
```

---

## Appendix C. Life-situation and PERMA-profile levels

The five life-situation levels are fixed directly in Appendix C of this SAP as follows.

```text
Level | Description
S1 | 50-year-old “overburdened middle-manager type”
S2 | 47-year-old “living with parents, low-income, continuing non-regular employment type”
S3 | 54-year-old “living alone, locally isolated, help-seeking-inhibited type”
S4 | 46-year-old “stably employed but socially thin professional type”
S5 | 49-year-old “repeated job changes and lowered self-evaluation type”
```

The three PERMA-profile levels are fixed directly in Appendix C of this SAP as follows.

```text
Level | Name | Description
P1 | Languishers | Condition in which all PERMA domains are low
P2 | Social hedonics | Condition in which Positive Emotion and Relationships are relatively high, while Engagement, Meaning, and Accomplishment are low
P3 | Unsocial eudemonics | Condition in which Engagement, Meaning, and Accomplishment are relatively high, while Positive Emotion and Relationships are low
```

These three PERMA profiles are not established latent profile classes from prior research. They are operational and heuristic classifications used to express differences across PERMA domains. Auxiliary settings such as interpersonal style are background settings intended to create natural differences in responses across life situation × PERMA conditions, and they are not treated as independent experimental factors.

---

## References

- Moyers, T. B., Manuel, J. K., & Ernst, D. (2014/2015 revision). *Motivational Interviewing Treatment Integrity Coding Manual 4.2.1*.
- Masked prior reference study. *Evaluating AI Counseling in Japanese: Counselor, Client, and Evaluator Roles Assessed by Motivational Interviewing Criteria*.
