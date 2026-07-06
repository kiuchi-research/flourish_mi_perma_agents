#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
results_dir <- if (length(args) >= 1) args[[1]] else "results/sap_v3_7"

dir.create(file.path(results_dir, "00_logs"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(results_dir, "07_primary_models"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(results_dir, "08_secondary_models"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(results_dir, "09_exploratory"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(results_dir, "10_sensitivity"), recursive = TRUE, showWarnings = FALSE)

log_lines <- character()
log_msg <- function(...) {
  line <- paste0(format(Sys.time(), "%Y-%m-%d %H:%M:%S"), " | ", paste(..., collapse = " "))
  log_lines <<- c(log_lines, line)
  message(line)
}

pkg_status <- data.frame(
  package = c("ordinal", "lme4", "emmeans", "MASS", "glmmTMB", "brglm2"),
  available = c(
    requireNamespace("ordinal", quietly = TRUE),
    requireNamespace("lme4", quietly = TRUE),
    requireNamespace("emmeans", quietly = TRUE),
    requireNamespace("MASS", quietly = TRUE),
    requireNamespace("glmmTMB", quietly = TRUE),
    requireNamespace("brglm2", quietly = TRUE)
  ),
  version = NA_character_
)
for (i in seq_len(nrow(pkg_status))) {
  if (pkg_status$available[i]) {
    pkg_status$version[i] <- as.character(utils::packageVersion(pkg_status$package[i]))
  }
}
write.csv(pkg_status, file.path(results_dir, "00_logs", "r_package_status.csv"), row.names = FALSE, fileEncoding = "UTF-8")

if (!pkg_status$available[pkg_status$package == "ordinal"]) {
  stop("R package 'ordinal' is required.")
}
if (!pkg_status$available[pkg_status$package == "lme4"]) {
  stop("R package 'lme4' is required.")
}

library(ordinal)
library(lme4)

read_utf8 <- function(path) {
  read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, fileEncoding = "UTF-8-BOM")
}

write_utf8 <- function(dat, path) {
  write.csv(dat, path, row.names = FALSE, fileEncoding = "UTF-8")
}

rating_levels <- sprintf("%.1f", seq(1, 5, by = 0.5))

safe_model <- function(expr) {
  warnings <- character()
  fit <- tryCatch(
    withCallingHandlers(
      expr,
      warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) {
      structure(list(error = conditionMessage(e)), class = "safe_model_error")
    }
  )
  list(fit = fit, warnings = unique(warnings))
}

is_error <- function(x) inherits(x, "safe_model_error")

fixed_coefs <- function(fit) {
  if (inherits(fit, "merMod")) {
    return(lme4::fixef(fit))
  }
  coef(fit)
}

has_layer_coef <- function(fit) {
  coefs <- fixed_coefs(fit)
  !is.null(coefs) && "layerLayer4" %in% names(coefs) && is.finite(coefs[["layerLayer4"]])
}

wald_ci <- function(fit, coef_name = "layerLayer4") {
  sm <- tryCatch(summary(fit), error = function(e) NULL)
  if (is.null(sm)) return(c(NA_real_, NA_real_))
  coefs <- tryCatch(coef(sm), error = function(e) NULL)
  if (is.null(coefs) || !(coef_name %in% rownames(coefs))) return(c(NA_real_, NA_real_))
  se_col <- intersect(colnames(coefs), c("Std. Error", "Std.Error"))
  if (!length(se_col)) return(c(NA_real_, NA_real_))
  est <- coefs[coef_name, "Estimate"]
  se <- coefs[coef_name, se_col[[1]]]
  c(est - 1.96 * se, est + 1.96 * se)
}

profile_or_wald_ci <- function(fit, coef_name = "layerLayer4") {
  prof <- tryCatch(
    suppressMessages(suppressWarnings(confint(fit, parm = coef_name))),
    error = function(e) NULL
  )
  if (!is.null(prof)) {
    vals <- as.numeric(prof[1, ])
    if (length(vals) == 2 && all(is.finite(vals))) {
      return(list(ci = vals, method = "profile_likelihood"))
    }
  }
  list(ci = wald_ci(fit, coef_name), method = "Wald")
}

extract_or <- function(fit, coef_name = "layerLayer4", ci_fun = profile_or_wald_ci) {
  coefs <- fixed_coefs(fit)
  beta <- if (has_layer_coef(fit)) coefs[[coef_name]] else NA_real_
  ci_obj <- ci_fun(fit, coef_name)
  data.frame(
    beta = beta,
    OR = exp(beta),
    CI_low = exp(ci_obj$ci[[1]]),
    CI_high = exp(ci_obj$ci[[2]]),
    CI_method = ci_obj$method
  )
}

lrt_p <- function(reduced, full) {
  tab <- tryCatch(anova(reduced, full), error = function(e) NULL)
  if (!is.null(tab)) {
    p_col <- grep("Pr\\(>Chisq\\)", colnames(tab), value = TRUE)
    if (length(p_col) && nrow(tab) >= 2) {
      p_val <- suppressWarnings(as.numeric(tab[2, p_col[[1]]]))
      if (length(p_val) == 1 && is.finite(p_val)) return(p_val)
    }
  }
  ll_red <- tryCatch(logLik(reduced), error = function(e) NULL)
  ll_full <- tryCatch(logLik(full), error = function(e) NULL)
  if (is.null(ll_red) || is.null(ll_full)) return(NA_real_)
  df <- attr(ll_full, "df") - attr(ll_red, "df")
  stat <- 2 * (as.numeric(ll_full) - as.numeric(ll_red))
  if (!is.finite(stat) || !is.finite(df) || df <= 0) return(NA_real_)
  pchisq(stat, df = df, lower.tail = FALSE)
}

random_variance_summary <- function(fit) {
  vc <- tryCatch(VarCorr(fit), error = function(e) NULL)
  if (is.null(vc)) return("unavailable")
  paste(capture.output(print(vc)), collapse = " | ")
}

clmm_fit_sequence <- function(dat, full_formulas, reduced_formulas, model_label) {
  attempts <- list()
  for (i in seq_along(full_formulas)) {
    full_formula <- as.formula(full_formulas[[i]])
    reduced_formula <- as.formula(reduced_formulas[[i]])
    full_obj <- safe_model(ordinal::clmm(full_formula, data = dat, link = "logit", Hess = TRUE))
    red_obj <- safe_model(ordinal::clmm(reduced_formula, data = dat, link = "logit", Hess = TRUE))
    full_ok <- !is_error(full_obj$fit) && length(full_obj$warnings) == 0 && has_layer_coef(full_obj$fit)
    red_ok <- !is_error(red_obj$fit) && length(red_obj$warnings) == 0
    attempts[[i]] <- list(
      engine = "clmm",
      step = i,
      full_formula = full_formulas[[i]],
      reduced_formula = reduced_formulas[[i]],
      full = full_obj,
      reduced = red_obj,
      valid = full_ok && red_ok
    )
    if (full_ok && red_ok) return(attempts[[i]])
    log_msg(model_label, "CLMM attempt", i, "invalid; trying fallback.")
  }

  full_obj <- safe_model(ordinal::clm(as.formula("rating_ord ~ layer + rater_id"), data = dat, link = "logit", Hess = TRUE))
  red_obj <- safe_model(ordinal::clm(as.formula("rating_ord ~ rater_id"), data = dat, link = "logit", Hess = TRUE))
  full_ok <- !is_error(full_obj$fit) && length(full_obj$warnings) == 0 && has_layer_coef(full_obj$fit)
  red_ok <- !is_error(red_obj$fit) && length(red_obj$warnings) == 0
  list(
    engine = "clm_fixed",
    step = length(full_formulas) + 1,
    full_formula = "rating_ord ~ layer + rater_id",
    reduced_formula = "rating_ord ~ rater_id",
    full = full_obj,
    reduced = red_obj,
    valid = full_ok && red_ok
  )
}

fit_primary_outcome <- function(dat, outcome_name, value_col = "rating_analysis", label = "primary") {
  sub <- dat[dat$outcome == outcome_name & !is.na(dat[[value_col]]), ]
  sub$rating_ord <- ordered(sprintf("%.1f", sub[[value_col]]), levels = rating_levels)
  sub$layer <- factor(sub$layer, levels = c("Layer3", "Layer4"))
  sub$rater_id <- factor(sub$rater_id)
  sub$pair_id <- factor(sub$pair_id)
  sub$script_id <- factor(sub$script_id)

  fit_obj <- clmm_fit_sequence(
    sub,
    c(
      "rating_ord ~ layer + rater_id + (1 | pair_id) + (1 | script_id)",
      "rating_ord ~ layer + rater_id + (1 | pair_id)"
    ),
    c(
      "rating_ord ~ rater_id + (1 | pair_id) + (1 | script_id)",
      "rating_ord ~ rater_id + (1 | pair_id)"
    ),
    paste(label, outcome_name)
  )

  if (!fit_obj$valid) {
    return(data.frame(
      analysis = label,
      outcome = outcome_name,
      n = nrow(sub),
      engine = fit_obj$engine,
      fallback_step = fit_obj$step,
      formula = fit_obj$full_formula,
      beta = NA_real_,
      OR = NA_real_,
      CI_low = NA_real_,
      CI_high = NA_real_,
      CI_method = NA_character_,
      p_value = NA_real_,
      model_status = "failed",
      warnings = paste(c(fit_obj$full$warnings, fit_obj$reduced$warnings), collapse = " || "),
      variance_summary = NA_character_
    ))
  }

  eff <- extract_or(fit_obj$full$fit)
  data.frame(
    analysis = label,
    outcome = outcome_name,
    n = nrow(sub),
    engine = fit_obj$engine,
    fallback_step = fit_obj$step,
    formula = fit_obj$full_formula,
    beta = eff$beta,
    OR = eff$OR,
    CI_low = eff$CI_low,
    CI_high = eff$CI_high,
    CI_method = eff$CI_method,
    p_value = lrt_p(fit_obj$reduced$fit, fit_obj$full$fit),
    model_status = "ok",
    warnings = paste(c(fit_obj$full$warnings, fit_obj$reduced$warnings), collapse = " || "),
    variance_summary = random_variance_summary(fit_obj$full$fit)
  )
}

fit_clmm_custom <- function(dat, outcome_name, value_col, full_formula, reduced_formula, label) {
  sub <- dat[dat$outcome == outcome_name & !is.na(dat[[value_col]]), ]
  sub$rating_ord <- ordered(sprintf("%.1f", sub[[value_col]]), levels = rating_levels)
  sub$layer <- factor(sub$layer, levels = c("Layer3", "Layer4"))
  sub$rater_id <- factor(sub$rater_id)
  sub$pair_id <- factor(sub$pair_id)
  sub$script_id <- factor(sub$script_id)
  full_obj <- safe_model(ordinal::clmm(as.formula(full_formula), data = sub, link = "logit", Hess = TRUE))
  red_obj <- safe_model(ordinal::clmm(as.formula(reduced_formula), data = sub, link = "logit", Hess = TRUE))
  ok <- !is_error(full_obj$fit) && !is_error(red_obj$fit) && has_layer_coef(full_obj$fit)
  if (!ok) {
    return(data.frame(
      analysis = label, outcome = outcome_name, n = nrow(sub), beta = NA_real_, OR = NA_real_,
      CI_low = NA_real_, CI_high = NA_real_, CI_method = NA_character_, p_value = NA_real_,
      model_status = "failed", warnings = paste(c(full_obj$warnings, red_obj$warnings), collapse = " || ")
    ))
  }
  eff <- extract_or(full_obj$fit)
  data.frame(
    analysis = label, outcome = outcome_name, n = nrow(sub), beta = eff$beta, OR = eff$OR,
    CI_low = eff$CI_low, CI_high = eff$CI_high, CI_method = eff$CI_method,
    p_value = lrt_p(red_obj$fit, full_obj$fit),
    model_status = ifelse(length(c(full_obj$warnings, red_obj$warnings)) == 0, "ok", "warning"),
    warnings = paste(c(full_obj$warnings, red_obj$warnings), collapse = " || ")
  )
}

fit_lmer_numeric <- function(dat, outcome_name, value_col, full_formula, reduced_formula, label) {
  sub <- dat[dat$outcome == outcome_name & !is.na(dat[[value_col]]), ]
  sub$rating_num <- as.numeric(sub[[value_col]])
  sub$layer <- factor(sub$layer, levels = c("Layer3", "Layer4"))
  sub$rater_id <- factor(sub$rater_id)
  sub$pair_id <- factor(sub$pair_id)
  sub$script_id <- factor(sub$script_id)
  full_obj <- safe_model(lme4::lmer(as.formula(full_formula), data = sub, REML = FALSE))
  red_obj <- safe_model(lme4::lmer(as.formula(reduced_formula), data = sub, REML = FALSE))
  ok <- !is_error(full_obj$fit) && !is_error(red_obj$fit) && has_layer_coef(full_obj$fit)
  if (!ok) {
    return(data.frame(analysis = label, outcome = outcome_name, n = nrow(sub), beta = NA_real_, CI_low = NA_real_, CI_high = NA_real_, p_value = NA_real_, model_status = "failed", warnings = paste(c(full_obj$warnings, red_obj$warnings), collapse = " || ")))
  }
  beta <- fixed_coefs(full_obj$fit)[["layerLayer4"]]
  ci <- wald_ci(full_obj$fit)
  data.frame(analysis = label, outcome = outcome_name, n = nrow(sub), beta = beta, CI_low = ci[[1]], CI_high = ci[[2]], p_value = lrt_p(red_obj$fit, full_obj$fit), model_status = ifelse(length(c(full_obj$warnings, red_obj$warnings)) == 0, "ok", "warning"), warnings = paste(c(full_obj$warnings, red_obj$warnings), collapse = " || "))
}

fit_good_outcome <- function(dat, outcome_col, value_label = "analysis", label = "secondary_good") {
  sub <- dat[!is.na(dat[[outcome_col]]), ]
  sub$layer <- factor(sub$layer, levels = c("Layer3", "Layer4"))
  sub$rater_id <- factor(sub$rater_id)
  sub$pair_id <- factor(sub$pair_id)
  sub$script_id <- factor(sub$script_id)
  sub$good <- as.integer(sub[[outcome_col]])

  attempts <- list(
    list(engine = "glmer", formula = "good ~ layer + rater_id + (1 | pair_id) + (1 | script_id)", reduced = "good ~ rater_id + (1 | pair_id) + (1 | script_id)"),
    list(engine = "glmer_no_script", formula = "good ~ layer + rater_id + (1 | pair_id)", reduced = "good ~ rater_id + (1 | pair_id)"),
    list(engine = "glm_fixed", formula = "good ~ layer + rater_id", reduced = "good ~ rater_id")
  )

  for (i in seq_along(attempts)) {
    a <- attempts[[i]]
    if (a$engine == "glm_fixed") {
      full_obj <- safe_model(glm(as.formula(a$formula), data = sub, family = binomial(link = "logit")))
      red_obj <- safe_model(glm(as.formula(a$reduced), data = sub, family = binomial(link = "logit")))
    } else {
      full_obj <- safe_model(lme4::glmer(as.formula(a$formula), data = sub, family = binomial(link = "logit"), control = glmerControl(optimizer = "bobyqa")))
      red_obj <- safe_model(lme4::glmer(as.formula(a$reduced), data = sub, family = binomial(link = "logit"), control = glmerControl(optimizer = "bobyqa")))
    }
    ok <- !is_error(full_obj$fit) && !is_error(red_obj$fit) && has_layer_coef(full_obj$fit)
    if (ok) {
      eff <- extract_or(full_obj$fit, ci_fun = function(fit, coef_name) list(ci = wald_ci(fit, coef_name), method = "Wald"))
      return(data.frame(
        analysis = label,
        value_set = value_label,
        outcome = outcome_col,
        n = nrow(sub),
        engine = a$engine,
        fallback_step = i,
        formula = a$formula,
        beta = eff$beta,
        OR = eff$OR,
        CI_low = eff$CI_low,
        CI_high = eff$CI_high,
        CI_method = eff$CI_method,
        p_value = lrt_p(red_obj$fit, full_obj$fit),
        model_status = ifelse(length(c(full_obj$warnings, red_obj$warnings)) == 0, "ok", "warning"),
        warnings = paste(c(full_obj$warnings, red_obj$warnings), collapse = " || "),
        variance_summary = ifelse(a$engine == "glm_fixed", NA_character_, random_variance_summary(full_obj$fit))
      ))
    }
  }

  data.frame(
    analysis = label,
    value_set = value_label,
    outcome = outcome_col,
    n = nrow(sub),
    engine = "none",
    fallback_step = NA_integer_,
    formula = NA_character_,
    beta = NA_real_,
    OR = NA_real_,
    CI_low = NA_real_,
    CI_high = NA_real_,
    CI_method = NA_character_,
    p_value = NA_real_,
    model_status = "failed",
    warnings = "all attempts failed",
    variance_summary = NA_character_
  )
}

global_path <- file.path(results_dir, "01_analysis_datasets", "global_ratings_long.csv")
good_path <- file.path(results_dir, "01_analysis_datasets", "technical_relational_global.csv")
client_path <- file.path(results_dir, "01_analysis_datasets", "client_naturalness_context.csv")
client_pair_path <- file.path(results_dir, "01_analysis_datasets", "client_naturalness_pair_mean.csv")
behavior_path <- file.path(results_dir, "01_analysis_datasets", "behavior_codes_pair.csv")

global <- read_utf8(global_path)
good <- read_utf8(good_path)
client <- read_utf8(client_path)
client_pair <- read_utf8(client_pair_path)
behavior <- read_utf8(behavior_path)

outcomes <- c("CCT", "SST", "PAR", "EMP", "overall_counselor_rating")

log_msg("Fitting primary CLMM models.")
primary <- do.call(rbind, lapply(outcomes, function(o) fit_primary_outcome(global, o, "rating_analysis", "primary_adjudicated_or_initial")))
primary$holm_p <- p.adjust(primary$p_value, method = "holm")
write_utf8(primary, file.path(results_dir, "07_primary_models", "primary_layer_effects.csv"))

log_msg("Fitting initial-value sensitivity CLMM models.")
initial_sens <- do.call(rbind, lapply(outcomes, function(o) fit_primary_outcome(global, o, "rating_initial", "initial_unadjudicated_sensitivity")))
initial_sens$holm_p <- p.adjust(initial_sens$p_value, method = "holm")
write_utf8(initial_sens, file.path(results_dir, "10_sensitivity", "primary_initial_unadjudicated_layer_effects.csv"))

log_msg("Fitting rater random-effect sensitivity models.")
rater_random <- do.call(rbind, lapply(outcomes, function(o) {
  fit_clmm_custom(
    global, o, "rating_analysis",
    "rating_ord ~ layer + (1 | rater_id) + (1 | pair_id) + (1 | script_id)",
    "rating_ord ~ (1 | rater_id) + (1 | pair_id) + (1 | script_id)",
    "rater_random_sensitivity"
  )
}))
rater_random$holm_p <- p.adjust(rater_random$p_value, method = "holm")
write_utf8(rater_random, file.path(results_dir, "10_sensitivity", "rater_random_layer_effects.csv"))

log_msg("Fitting numeric LMM sensitivity models.")
numeric_lmm <- do.call(rbind, lapply(outcomes, function(o) {
  fit_lmer_numeric(
    global, o, "rating_analysis",
    "rating_num ~ layer + rater_id + (1 | pair_id) + (1 | script_id)",
    "rating_num ~ rater_id + (1 | pair_id) + (1 | script_id)",
    "numeric_lmm_sensitivity"
  )
}))
numeric_lmm$holm_p <- p.adjust(numeric_lmm$p_value, method = "holm")
write_utf8(numeric_lmm, file.path(results_dir, "10_sensitivity", "numeric_lmm_layer_effects.csv"))

log_msg("Fitting length-adjusted sensitivity models.")
length_sens <- do.call(rbind, lapply(outcomes, function(o) {
  fit_clmm_custom(
    global, o, "rating_analysis",
    "rating_ord ~ layer + rater_id + counselor_utterance_count + (1 | pair_id) + (1 | script_id)",
    "rating_ord ~ rater_id + counselor_utterance_count + (1 | pair_id) + (1 | script_id)",
    "length_adjusted_sensitivity"
  )
}))
length_sens$holm_p <- p.adjust(length_sens$p_value, method = "holm")
write_utf8(length_sens, file.path(results_dir, "10_sensitivity", "length_adjusted_layer_effects.csv"))

log_msg("Fitting leave-one-rater-out primary models.")
loo_rows <- list()
for (r in unique(global$rater_id)) {
  dat_loo <- global[global$rater_id != r, ]
  rows <- do.call(rbind, lapply(outcomes, function(o) fit_primary_outcome(dat_loo, o, "rating_analysis", paste0("leave_one_rater_out_", r))))
  rows$excluded_rater_id <- r
  rows$holm_p <- p.adjust(rows$p_value, method = "holm")
  loo_rows[[r]] <- rows
}
write_utf8(do.call(rbind, loo_rows), file.path(results_dir, "10_sensitivity", "leave_one_rater_out_layer_effects.csv"))

log_msg("Fitting secondary Good-threshold models.")
good_results <- rbind(
  fit_good_outcome(good, "good_technical_global", "analysis", "secondary_good"),
  fit_good_outcome(good, "good_relational_global", "analysis", "secondary_good")
)
good_results$holm_p <- p.adjust(good_results$p_value, method = "holm")
write_utf8(good_results, file.path(results_dir, "08_secondary_models", "good_threshold_layer_effects.csv"))

good_initial <- rbind(
  fit_good_outcome(good, "good_technical_global_initial", "initial", "secondary_good_initial_sensitivity"),
  fit_good_outcome(good, "good_relational_global_initial", "initial", "secondary_good_initial_sensitivity")
)
good_initial$holm_p <- p.adjust(good_initial$p_value, method = "holm")
write_utf8(good_initial, file.path(results_dir, "10_sensitivity", "good_threshold_initial_unadjudicated_layer_effects.csv"))

log_msg("Fitting exploratory global situation/PERMA models.")
explore_rows <- list()
for (o in outcomes) {
  sub <- global[global$outcome == o & !is.na(global$rating_analysis), ]
  sub$rating_ord <- ordered(sprintf("%.1f", sub$rating_analysis), levels = rating_levels)
  sub$layer <- factor(sub$layer, levels = c("Layer3", "Layer4"))
  sub$situation <- factor(sub$situation)
  sub$perma_profile <- factor(sub$perma_profile)
  sub$rater_id <- factor(sub$rater_id)
  sub$script_id <- factor(sub$script_id)
  full <- safe_model(ordinal::clmm(rating_ord ~ layer + situation + perma_profile + rater_id + (1 | script_id), data = sub, link = "logit", Hess = TRUE))
  no_situation <- safe_model(ordinal::clmm(rating_ord ~ layer + perma_profile + rater_id + (1 | script_id), data = sub, link = "logit", Hess = TRUE))
  no_perma <- safe_model(ordinal::clmm(rating_ord ~ layer + situation + rater_id + (1 | script_id), data = sub, link = "logit", Hess = TRUE))
  explore_rows[[paste0(o, "_situation")]] <- data.frame(outcome = o, effect = "situation", n = nrow(sub), p_value = if (!is_error(full$fit) && !is_error(no_situation$fit)) lrt_p(no_situation$fit, full$fit) else NA_real_, model_status = ifelse(!is_error(full$fit) && !is_error(no_situation$fit), "ok_or_warning", "failed"), warnings = paste(c(full$warnings, no_situation$warnings), collapse = " || "))
  explore_rows[[paste0(o, "_perma")]] <- data.frame(outcome = o, effect = "perma_profile", n = nrow(sub), p_value = if (!is_error(full$fit) && !is_error(no_perma$fit)) lrt_p(no_perma$fit, full$fit) else NA_real_, model_status = ifelse(!is_error(full$fit) && !is_error(no_perma$fit), "ok_or_warning", "failed"), warnings = paste(c(full$warnings, no_perma$warnings), collapse = " || "))
}
explore <- do.call(rbind, explore_rows)
explore$holm_p_within_effect <- ave(explore$p_value, explore$effect, FUN = function(x) p.adjust(x, method = "holm"))
write_utf8(explore, file.path(results_dir, "09_exploratory", "global_situation_perma_effects.csv"))

log_msg("Fitting client naturalness exploratory models.")
client$source_layer <- factor(client$source_layer, levels = c("Layer3", "Layer4"))
client$situation <- factor(client$situation)
client$perma_profile <- factor(client$perma_profile)
client$rater_id <- factor(client$rater_id)
client$pair_id <- factor(client$pair_id)
client$source_script_id <- factor(client$source_script_id)

fit_client_full_ml <- safe_model(lme4::lmer(client_naturalness_analysis ~ situation * perma_profile + source_layer + presentation_order_z + rater_id + (1 | pair_id) + (1 | source_script_id), data = client, REML = FALSE))
fit_client_red_ml <- safe_model(lme4::lmer(client_naturalness_analysis ~ situation + perma_profile + source_layer + presentation_order_z + rater_id + (1 | pair_id) + (1 | source_script_id), data = client, REML = FALSE))
fit_client_reml <- safe_model(lme4::lmer(client_naturalness_analysis ~ situation * perma_profile + source_layer + presentation_order_z + rater_id + (1 | pair_id) + (1 | source_script_id), data = client, REML = TRUE))
client_result <- data.frame(
  analysis = "client_naturalness_context_lmm",
  n = nrow(client),
  interaction_p_value_ml_lrt = if (!is_error(fit_client_full_ml$fit) && !is_error(fit_client_red_ml$fit)) lrt_p(fit_client_red_ml$fit, fit_client_full_ml$fit) else NA_real_,
  source_layer_beta = if (!is_error(fit_client_reml$fit) && "source_layerLayer4" %in% names(fixed_coefs(fit_client_reml$fit))) fixed_coefs(fit_client_reml$fit)[["source_layerLayer4"]] else NA_real_,
  model_status = ifelse(!is_error(fit_client_full_ml$fit) && !is_error(fit_client_red_ml$fit), "ok_or_warning", "failed"),
  warnings = paste(c(fit_client_full_ml$warnings, fit_client_red_ml$warnings, fit_client_reml$warnings), collapse = " || "),
  variance_summary = if (!is_error(fit_client_reml$fit)) random_variance_summary(fit_client_reml$fit) else NA_character_
)
write_utf8(client_result, file.path(results_dir, "09_exploratory", "client_naturalness_context_lmm.csv"))

client_pair$situation <- factor(client_pair$situation)
client_pair$perma_profile <- factor(client_pair$perma_profile)
client_pair$rater_id <- factor(client_pair$rater_id)
client_pair$pair_id <- factor(client_pair$pair_id)
fit_pair_full_ml <- safe_model(lme4::lmer(client_naturalness_pair_mean_analysis ~ situation * perma_profile + rater_id + (1 | pair_id), data = client_pair, REML = FALSE))
fit_pair_red_ml <- safe_model(lme4::lmer(client_naturalness_pair_mean_analysis ~ situation + perma_profile + rater_id + (1 | pair_id), data = client_pair, REML = FALSE))
client_pair_result <- data.frame(
  analysis = "client_naturalness_pair_mean_lmm",
  n = nrow(client_pair),
  interaction_p_value_ml_lrt = if (!is_error(fit_pair_full_ml$fit) && !is_error(fit_pair_red_ml$fit)) lrt_p(fit_pair_red_ml$fit, fit_pair_full_ml$fit) else NA_real_,
  model_status = ifelse(!is_error(fit_pair_full_ml$fit) && !is_error(fit_pair_red_ml$fit), "ok_or_warning", "failed"),
  warnings = paste(c(fit_pair_full_ml$warnings, fit_pair_red_ml$warnings), collapse = " || "),
  variance_summary = if (!is_error(fit_pair_full_ml$fit)) random_variance_summary(fit_pair_full_ml$fit) else NA_character_
)
write_utf8(client_pair_result, file.path(results_dir, "09_exploratory", "client_naturalness_pair_mean_lmm.csv"))

log_msg("Fitting behavior-code exploratory models.")
behavior$situation <- factor(behavior$situation)
behavior$perma_profile <- factor(behavior$perma_profile)
behavior_results <- list()
behavior_specs <- list(
  Q = list(col = "Q", family = "poisson"),
  total_reflection = list(col = "total_reflection", family = "poisson"),
  pct_complex_reflection = list(col = "pct_complex_reflection", family = "lm"),
  reflection_question_ratio = list(col = "reflection_question_ratio_finite_log1p", family = "lm"),
  Total_MI_Adherent = list(col = "Total_MI_Adherent", family = "poisson"),
  Total_MI_Non_Adherent = list(col = "Total_MI_Non_Adherent", family = "poisson")
)
for (nm in names(behavior_specs)) {
  spec <- behavior_specs[[nm]]
  sub <- behavior[!is.na(behavior[[spec$col]]), ]
  if (nrow(sub) == 0) {
    behavior_results[[nm]] <- data.frame(summary = nm, n = 0, engine = "none", interaction_p_value = NA_real_, model_status = "no_data", poisson_aic = NA_real_, negbin_aic = NA_real_)
    next
  }
  if (spec$family == "poisson") {
    pois <- safe_model(glm(as.formula(paste0(spec$col, " ~ situation * perma_profile")), data = sub, family = poisson(link = "log")))
    red <- safe_model(glm(as.formula(paste0(spec$col, " ~ situation + perma_profile")), data = sub, family = poisson(link = "log")))
    nb <- if (pkg_status$available[pkg_status$package == "MASS"]) safe_model(MASS::glm.nb(as.formula(paste0(spec$col, " ~ situation * perma_profile")), data = sub)) else list(fit = structure(list(error = "MASS unavailable"), class = "safe_model_error"), warnings = character())
    pois_aic <- if (!is_error(pois$fit)) AIC(pois$fit) else NA_real_
    nb_aic <- if (!is_error(nb$fit)) AIC(nb$fit) else NA_real_
    behavior_results[[nm]] <- data.frame(summary = nm, n = nrow(sub), engine = ifelse(is.finite(nb_aic) && is.finite(pois_aic) && nb_aic <= pois_aic - 4, "negative_binomial_supplement", "poisson_primary"), interaction_p_value = if (!is_error(pois$fit) && !is_error(red$fit)) lrt_p(red$fit, pois$fit) else NA_real_, model_status = ifelse(!is_error(pois$fit), "ok_or_warning", "failed"), poisson_aic = pois_aic, negbin_aic = nb_aic)
  } else {
    full <- safe_model(lm(as.formula(paste0(spec$col, " ~ situation * perma_profile")), data = sub))
    red <- safe_model(lm(as.formula(paste0(spec$col, " ~ situation + perma_profile")), data = sub))
    behavior_results[[nm]] <- data.frame(summary = nm, n = nrow(sub), engine = "lm_supplement", interaction_p_value = if (!is_error(full$fit) && !is_error(red$fit)) lrt_p(red$fit, full$fit) else NA_real_, model_status = ifelse(!is_error(full$fit), "ok_or_warning", "failed"), poisson_aic = NA_real_, negbin_aic = NA_real_)
  }
}
write_utf8(do.call(rbind, behavior_results), file.path(results_dir, "09_exploratory", "behavior_code_exploratory_models.csv"))

writeLines(log_lines, file.path(results_dir, "00_logs", "r_model_log.txt"))
log_msg("R analysis completed.")
