#!/usr/bin/env python3
"""Run the SAP v3.7 analysis pipeline.

This script creates analysis datasets from the nonpublic source workbook,
computes reliability and descriptive summaries, calls the R model script, and
renders a concise analysis report under ``results/sap_v3_7``.
"""

from __future__ import annotations

import json
import math
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_XLSX = PROJECT_ROOT / "private_inputs" / "source_workbook.xlsx"
RESULTS_DIR = PROJECT_ROOT / "results" / "sap_v3_7"
R_SCRIPT = PROJECT_ROOT / "analysis_steps" / "sap_v3_7_models.R"

SOURCE_RATER_PREFIX = "\u8a55\u4fa1\u8005"
SOURCE_INITIAL = "\u521d\u56de"
SOURCE_CLIENT_EVAL = "\u30af\u30e9\u30a4\u30a2\u30f3\u30c8\u8a55\u4fa1"
SOURCE_RATERS = [f"{SOURCE_RATER_PREFIX}{i}" for i in range(1, 5)]
PUBLIC_RATER_IDS = {source: f"rater_{i}" for i, source in enumerate(SOURCE_RATERS, start=1)}
RATERS = list(PUBLIC_RATER_IDS.values())
RATING_LEVELS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
CLIENT_LEVELS = list(range(1, 11))

OUTCOMES = {
    "CCT": "\u30c1\u30a7\u30f3\u30b8\u30c8\u30fc\u30af\u4fc3\u9032",
    "SST": "\u7dad\u6301\u30c8\u30fc\u30af\u6e1b\u5f31",
    "PAR": "\u30d1\u30fc\u30c8\u30ca\u30fc\u30b7\u30c3\u30d7",
    "EMP": "\u5171\u611f",
    "overall_counselor_rating": "\u7dcf\u5408\u8a55\u4fa1",
}

PRIOR_REFERENCES = {
    "CCT": {"GPT-SMDP": (3.41, 0.74), "Opus-SMDP": (3.44, 0.87)},
    "SST": {"GPT-SMDP": (3.22, 0.85), "Opus-SMDP": (3.38, 0.85)},
    "PAR": {"GPT-SMDP": (3.20, 0.79), "Opus-SMDP": (2.99, 0.96)},
    "EMP": {"GPT-SMDP": (3.12, 0.91), "Opus-SMDP": (3.22, 0.96)},
    "overall_counselor_rating": {"GPT-SMDP": (3.22, 0.65), "Opus-SMDP": (3.28, 0.83)},
}

PERMA_MAP = {
    "LANG": ("P1", "Languishers"),
    "SOCIAL": ("P2", "Social hedonics"),
    "UNSOCIAL": ("P3", "Unsocial eudemonics"),
}

SITUATION_MAP = {
    "MGR": ("S1", "Overburdened middle manager"),
    "LOWINC": ("S2", "Living with parents, low income, and continued non-regular employment"),
    "ISO": ("S3", "Living alone, socially isolated, and reluctant to seek help"),
    "STABLE": ("S4", "Stably employed professional with limited interpersonal ties"),
    "MOB": ("S5", "Repeated job changes and declining self-evaluation"),
}

ACTION_TO_CODE = {
    "QUESTION": "Q",
    "SCALING_QUESTION": "Q",
    "CLARIFY_PREFERENCE": "Q",
    "REFLECT_SIMPLE": "SR",
    "SUMMARY": "SR",
    "REFLECT": "CR",
    "REFLECT_COMPLEX": "CR",
    "REFLECT_DOUBLE": "CR",
    "PROVIDE_INFO": "GI",
    "ASK_PERMISSION_TO_SHARE_INFO": "Seek",
}

CLIENT_NATURALNESS_RAW_TRANSLATIONS = {
    "1\uff1a\u5168\u304f\u81ea\u7136\u3058\u3083\u306a\u3044": "1: not natural at all",
    "5\uff1a\u3069\u3061\u3089\u304b\u3068\u3044\u3046\u3068\u81ea\u7136\u3058\u3083\u306a\u3044": "5: somewhat unnatural",
    "6\uff1a\u3069\u3061\u3089\u304b\u3068\u3044\u3046\u3068\u81ea\u7136": "6: somewhat natural",
}


@dataclass(frozen=True)
class OutputDirs:
    logs: Path
    datasets: Path
    validation: Path
    reliability: Path
    adjudication: Path
    descriptives: Path
    hypothesis1: Path
    primary: Path
    secondary: Path
    exploratory: Path
    sensitivity: Path
    report: Path


def make_output_dirs() -> OutputDirs:
    dirs = OutputDirs(
        logs=RESULTS_DIR / "00_logs",
        datasets=RESULTS_DIR / "01_analysis_datasets",
        validation=RESULTS_DIR / "02_validation",
        reliability=RESULTS_DIR / "03_reliability",
        adjudication=RESULTS_DIR / "04_adjudication",
        descriptives=RESULTS_DIR / "05_descriptives",
        hypothesis1=RESULTS_DIR / "06_hypothesis1",
        primary=RESULTS_DIR / "07_primary_models",
        secondary=RESULTS_DIR / "08_secondary_models",
        exploratory=RESULTS_DIR / "09_exploratory",
        sensitivity=RESULTS_DIR / "10_sensitivity",
        report=RESULTS_DIR / "11_report",
    )
    for directory in dirs.__dict__.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def format_float(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def simple_markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_No applicable rows_"
    data = df.copy()
    for col in data.columns:
        data[col] = data[col].map(lambda x: format_float(x) if isinstance(x, (float, np.floating)) else ("" if pd.isna(x) else str(x)))
    headers = list(data.columns)
    rows = data.values.tolist()
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(lines)


def numeric_rating(value: Any) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return np.nan
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", text)
    if match:
        return float(match.group(1))
    return np.nan


def normalize_layer(raw: Any) -> str:
    text = str(raw).strip()
    if text == "draft_response_text":
        return "Layer3"
    if text == "text":
        return "Layer4"
    raise ValueError(f"Unexpected layer value: {raw!r}")


def split_client_type(client_type: str) -> tuple[str, str, str, str]:
    parts = str(client_type).split("_", 1)
    if len(parts) != 2:
        raise ValueError(f"Unexpected client_type: {client_type}")
    perma_key, situation_key = parts
    perma_code, perma_label = PERMA_MAP[perma_key]
    situation_code, situation_label = SITUATION_MAP[situation_key]
    return perma_code, perma_label, situation_code, situation_label


def make_pair_id(generation_id: int, client_type: str) -> str:
    return f"G{int(generation_id):02d}_{client_type}"


def icc_two_way_absolute(matrix: pd.DataFrame) -> dict[str, float]:
    values = matrix.astype(float).to_numpy()
    n, k = values.shape
    grand = np.nanmean(values)
    row_means = np.nanmean(values, axis=1)
    col_means = np.nanmean(values, axis=0)
    ss_rows = k * np.sum((row_means - grand) ** 2)
    ss_cols = n * np.sum((col_means - grand) ** 2)
    residual = values - row_means[:, None] - col_means[None, :] + grand
    ss_error = np.nansum(residual**2)
    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))
    denom_a1 = ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n
    denom_ak = ms_rows + (ms_cols - ms_error) / n
    icc_a1 = (ms_rows - ms_error) / denom_a1 if denom_a1 != 0 else np.nan
    icc_ak = (ms_rows - ms_error) / denom_ak if denom_ak != 0 else np.nan
    denom_c1 = ms_rows + (k - 1) * ms_error
    icc_c1 = (ms_rows - ms_error) / denom_c1 if denom_c1 != 0 else np.nan
    icc_ck = (ms_rows - ms_error) / ms_rows if ms_rows != 0 else np.nan
    return {
        "ICC_A_1_absolute_single": icc_a1,
        "ICC_A_k_absolute_average": icc_ak,
        "ICC_C_1_consistency_single": icc_c1,
        "ICC_C_k_consistency_average": icc_ck,
    }


def bootstrap_icc_ci(matrix: pd.DataFrame, seed: int = 20260507, iterations: int = 5000) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(matrix)
    vals_a1: list[float] = []
    vals_ak: list[float] = []
    for _ in range(iterations):
        idx = rng.integers(0, n, size=n)
        sample = matrix.iloc[idx].reset_index(drop=True)
        icc = icc_two_way_absolute(sample)
        vals_a1.append(icc["ICC_A_1_absolute_single"])
        vals_ak.append(icc["ICC_A_k_absolute_average"])
    arr_a1 = np.array(vals_a1, dtype=float)
    arr_ak = np.array(vals_ak, dtype=float)
    return {
        "ICC_A_1_95CI_low_boot": np.nanpercentile(arr_a1, 2.5),
        "ICC_A_1_95CI_high_boot": np.nanpercentile(arr_a1, 97.5),
        "ICC_A_k_95CI_low_boot": np.nanpercentile(arr_ak, 2.5),
        "ICC_A_k_95CI_high_boot": np.nanpercentile(arr_ak, 97.5),
    }


def krippendorff_alpha(matrix: pd.DataFrame, metric: str) -> float:
    values = matrix.astype(float).to_numpy()
    categories = sorted(pd.unique(pd.Series(values.ravel()).dropna()))
    if len(categories) < 2:
        return np.nan

    def distance(a: float, b: float) -> float:
        if metric == "interval":
            return float((a - b) ** 2)
        ranks = {cat: idx for idx, cat in enumerate(categories)}
        return float((ranks[a] - ranks[b]) ** 2)

    observed_num = 0.0
    observed_den = 0
    for row in values:
        vals = [float(v) for v in row if not np.isnan(v)]
        m = len(vals)
        if m < 2:
            continue
        for i in range(m):
            for j in range(m):
                if i == j:
                    continue
                observed_num += distance(vals[i], vals[j])
                observed_den += 1
    if observed_den == 0:
        return np.nan
    do = observed_num / observed_den

    flat = [float(v) for v in values.ravel() if not np.isnan(v)]
    n = len(flat)
    expected_num = 0.0
    expected_den = n * (n - 1)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            expected_num += distance(flat[i], flat[j])
    if expected_den == 0:
        return np.nan
    de = expected_num / expected_den
    return 1.0 - do / de if de != 0 else np.nan


def reliability_for_matrix(
    matrix: pd.DataFrame,
    metric_name: str,
    timing: str,
    alpha_metric: str,
    seed_offset: int = 0,
) -> dict[str, Any]:
    complete = matrix.dropna()
    icc = icc_two_way_absolute(complete)
    ci = bootstrap_icc_ci(complete, seed=20260507 + seed_offset, iterations=5000)
    return {
        "timing": timing,
        "metric": metric_name,
        "n_cases": int(complete.shape[0]),
        "n_raters": int(complete.shape[1]),
        **icc,
        **ci,
        "krippendorff_alpha": krippendorff_alpha(complete, alpha_metric),
        "krippendorff_metric": alpha_metric,
        "mean_within_case_sd": float(complete.std(axis=1, ddof=1).mean()),
        "mean_rating": float(complete.to_numpy().mean()),
    }


def build_case_base(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base["generation_id"] = base["gneration"].astype(int)
    base["layer"] = base["layer"].map(normalize_layer)
    base["source_layer"] = base["layer"]
    base["script_id"] = base["id"].astype(str)
    base["pair_id"] = [make_pair_id(g, ct) for g, ct in zip(base["generation_id"], base["client_type"])]
    parsed = base["client_type"].map(split_client_type)
    base["perma_code"] = parsed.map(lambda x: x[0])
    base["perma_profile"] = parsed.map(lambda x: x[1])
    base["situation_code"] = parsed.map(lambda x: x[2])
    base["situation"] = parsed.map(lambda x: x[3])
    return base


def build_global_long(base: pd.DataFrame, reliability_initial: pd.DataFrame | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in base.iterrows():
        for source_rater, public_rater in PUBLIC_RATER_IDS.items():
            presentation_order = numeric_rating(row.get(source_rater))
            for outcome, jp_name in OUTCOMES.items():
                initial = numeric_rating(row.get(f"{source_rater}_{SOURCE_INITIAL}_{jp_name}"))
                final = numeric_rating(row.get(f"{source_rater}_{jp_name}"))
                rows.append(
                    {
                        "script_id": row["script_id"],
                        "pair_id": row["pair_id"],
                        "layer": row["layer"],
                        "situation": row["situation"],
                        "situation_code": row["situation_code"],
                        "perma_profile": row["perma_profile"],
                        "perma_code": row["perma_code"],
                        "generation_id": row["generation_id"],
                        "client_type": row["client_type"],
                        "rater_id": public_rater,
                        "outcome": outcome,
                        "rating_initial": initial,
                        "rating_final": final,
                        "presentation_order": presentation_order,
                    }
                )
    long = pd.DataFrame(rows)
    med = long.groupby(["script_id", "outcome"], as_index=False)["rating_initial"].median().rename(columns={"rating_initial": "initial_median"})
    long = long.merge(med, on=["script_id", "outcome"], how="left")
    long["absolute_median_diff"] = (long["rating_initial"] - long["initial_median"]).abs()
    low_reliability = set()
    if reliability_initial is not None:
        low_reliability = set(reliability_initial.loc[reliability_initial["ICC_A_k_absolute_average"] < 0.50, "metric"])
    long["uses_adjudicated_final"] = long["outcome"].isin(low_reliability)
    long["rating_analysis"] = np.where(long["uses_adjudicated_final"], long["rating_final"], long["rating_initial"])

    def flag(row: pd.Series) -> str:
        if pd.isna(row["rating_initial"]) or pd.isna(row["rating_final"]):
            return "missing_or_unresolvable"
        if not row["uses_adjudicated_final"]:
            return "not_applicable"
        changed = not np.isclose(row["rating_initial"], row["rating_final"])
        threshold_hit = row["absolute_median_diff"] >= 1.0
        if changed:
            return "adjudicated_changed"
        if threshold_hit:
            return "adjudicated_confirmed"
        return "checked_no_change"

    long["adjudication_flag"] = long.apply(flag, axis=1)
    return long


def build_client_context(base: pd.DataFrame, reliability_initial: pd.DataFrame | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in base.iterrows():
        for source_rater, public_rater in PUBLIC_RATER_IDS.items():
            raw_naturalness = row.get(f"{source_rater}_{SOURCE_INITIAL}_{SOURCE_CLIENT_EVAL}")
            public_raw_naturalness = CLIENT_NATURALNESS_RAW_TRANSLATIONS.get(
                str(raw_naturalness),
                raw_naturalness,
            )
            initial = numeric_rating(raw_naturalness)
            final = numeric_rating(row.get(f"{source_rater}_{SOURCE_CLIENT_EVAL}"))
            rows.append(
                {
                    "source_script_id": row["script_id"],
                    "pair_id": row["pair_id"],
                    "source_layer": row["source_layer"],
                    "situation": row["situation"],
                    "situation_code": row["situation_code"],
                    "perma_profile": row["perma_profile"],
                    "perma_code": row["perma_code"],
                    "generation_id": row["generation_id"],
                    "client_type": row["client_type"],
                    "rater_id": public_rater,
                    "presentation_order": numeric_rating(row.get(source_rater)),
                    "client_naturalness_raw": public_raw_naturalness,
                    "client_naturalness_initial": initial,
                    "client_naturalness_final": final,
                }
            )
    client = pd.DataFrame(rows)
    med = client.groupby("source_script_id", as_index=False)["client_naturalness_initial"].median().rename(columns={"client_naturalness_initial": "client_naturalness_initial_median"})
    client = client.merge(med, on="source_script_id", how="left")
    client["client_naturalness_absolute_median_diff"] = (
        client["client_naturalness_initial"] - client["client_naturalness_initial_median"]
    ).abs()
    low = False
    if reliability_initial is not None and not reliability_initial.empty:
        row = reliability_initial[reliability_initial["metric"] == "client_naturalness"]
        low = bool((row["ICC_A_k_absolute_average"] < 0.50).any())
    client["uses_adjudicated_final"] = low
    client["client_naturalness_analysis"] = np.where(
        client["uses_adjudicated_final"],
        client["client_naturalness_final"],
        client["client_naturalness_initial"],
    )

    def flag(row: pd.Series) -> str:
        if pd.isna(row["client_naturalness_initial"]) or pd.isna(row["client_naturalness_final"]):
            return "missing_or_unresolvable"
        if not row["uses_adjudicated_final"]:
            return "not_applicable"
        changed = not np.isclose(row["client_naturalness_initial"], row["client_naturalness_final"])
        threshold_hit = row["client_naturalness_absolute_median_diff"] >= 2.5
        if changed:
            return "adjudicated_changed"
        if threshold_hit:
            return "adjudicated_confirmed"
        return "checked_no_change"

    client["client_naturalness_adjudication_flag"] = client.apply(flag, axis=1)
    client["presentation_order_z"] = client.groupby("rater_id")["presentation_order"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) and not np.isclose(s.std(ddof=0), 0) else 0
    )
    return client


def client_pair_mean(client: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["pair_id", "situation", "situation_code", "perma_profile", "perma_code", "generation_id", "client_type", "rater_id"]
    agg = (
        client.groupby(group_cols, dropna=False)
        .agg(
            client_naturalness_pair_mean_initial=("client_naturalness_initial", "mean"),
            client_naturalness_pair_mean_final=("client_naturalness_final", "mean"),
            client_naturalness_pair_mean_analysis=("client_naturalness_analysis", "mean"),
            client_naturalness_pair_available_source_count=("client_naturalness_analysis", "count"),
            presentation_order_pair_mean=("presentation_order", "mean"),
        )
        .reset_index()
    )
    agg["presentation_order_pair_mean_z"] = agg.groupby("rater_id")["presentation_order_pair_mean"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) and not np.isclose(s.std(ddof=0), 0) else 0
    )
    return agg


def add_client_context_diff(client: pd.DataFrame) -> pd.DataFrame:
    wide = client.pivot_table(
        index=["pair_id", "rater_id"],
        columns="source_layer",
        values="client_naturalness_analysis",
        aggfunc="first",
    ).reset_index()
    if "Layer3" not in wide:
        wide["Layer3"] = np.nan
    if "Layer4" not in wide:
        wide["Layer4"] = np.nan
    wide["client_naturalness_layer_diff"] = wide["Layer4"] - wide["Layer3"]
    wide["client_naturalness_abs_layer_diff"] = wide["client_naturalness_layer_diff"].abs()
    return wide


def build_global_reliability(base: pd.DataFrame, value_prefix: str, timing: str) -> pd.DataFrame:
    rows = []
    for i, (outcome, jp_name) in enumerate(OUTCOMES.items()):
        values = []
        for _, row in base.iterrows():
            item = {"script_id": row["script_id"]}
            for source_rater, public_rater in PUBLIC_RATER_IDS.items():
                col = f"{source_rater}_{value_prefix}_{jp_name}" if value_prefix else f"{source_rater}_{jp_name}"
                item[public_rater] = numeric_rating(row.get(col))
            values.append(item)
        mat = pd.DataFrame(values).set_index("script_id")[RATERS]
        rows.append(reliability_for_matrix(mat, outcome, timing, "ordinal", seed_offset=i))
    return pd.DataFrame(rows)


def build_client_reliability(base: pd.DataFrame, initial: bool, timing: str) -> pd.DataFrame:
    values = []
    for _, row in base.iterrows():
        item = {"source_script_id": row["script_id"]}
        for source_rater, public_rater in PUBLIC_RATER_IDS.items():
            col = f"{source_rater}_{SOURCE_INITIAL}_{SOURCE_CLIENT_EVAL}" if initial else f"{source_rater}_{SOURCE_CLIENT_EVAL}"
            item[public_rater] = numeric_rating(row.get(col))
        values.append(item)
    mat = pd.DataFrame(values).set_index("source_script_id")[RATERS]
    return pd.DataFrame([reliability_for_matrix(mat, "client_naturalness", timing, "interval", seed_offset=50)])


def technical_relational(global_long: pd.DataFrame) -> pd.DataFrame:
    analysis_wide = global_long.pivot_table(
        index=[
            "script_id",
            "pair_id",
            "layer",
            "situation",
            "situation_code",
            "perma_profile",
            "perma_code",
            "generation_id",
            "client_type",
            "rater_id",
            "presentation_order",
        ],
        columns="outcome",
        values="rating_analysis",
        aggfunc="first",
    ).reset_index()
    initial_wide = global_long.pivot_table(
        index=["script_id", "rater_id"],
        columns="outcome",
        values="rating_initial",
        aggfunc="first",
    ).reset_index()
    merged = analysis_wide.merge(initial_wide, on=["script_id", "rater_id"], suffixes=("", "_initial"))
    merged["technical_global"] = merged[["CCT", "SST"]].mean(axis=1)
    merged.loc[merged[["CCT", "SST"]].isna().any(axis=1), "technical_global"] = np.nan
    merged["relational_global"] = merged[["PAR", "EMP"]].mean(axis=1)
    merged.loc[merged[["PAR", "EMP"]].isna().any(axis=1), "relational_global"] = np.nan
    merged["good_technical_global"] = (merged["technical_global"] >= 4.0).astype(float)
    merged.loc[merged["technical_global"].isna(), "good_technical_global"] = np.nan
    merged["good_relational_global"] = (merged["relational_global"] >= 4.0).astype(float)
    merged.loc[merged["relational_global"].isna(), "good_relational_global"] = np.nan

    merged["technical_global_initial"] = merged[["CCT_initial", "SST_initial"]].mean(axis=1)
    merged.loc[merged[["CCT_initial", "SST_initial"]].isna().any(axis=1), "technical_global_initial"] = np.nan
    merged["relational_global_initial"] = merged[["PAR_initial", "EMP_initial"]].mean(axis=1)
    merged.loc[merged[["PAR_initial", "EMP_initial"]].isna().any(axis=1), "relational_global_initial"] = np.nan
    merged["good_technical_global_initial"] = (merged["technical_global_initial"] >= 4.0).astype(float)
    merged.loc[merged["technical_global_initial"].isna(), "good_technical_global_initial"] = np.nan
    merged["good_relational_global_initial"] = (merged["relational_global_initial"] >= 4.0).astype(float)
    merged.loc[merged["relational_global_initial"].isna(), "good_relational_global_initial"] = np.nan
    return merged


def build_technical_reliability(tech: pd.DataFrame, value_col: str, metric_name: str) -> dict[str, Any]:
    mat = tech.pivot_table(index="script_id", columns="rater_id", values=value_col, aggfunc="first")
    return reliability_for_matrix(mat[RATERS], metric_name, "analysis", "interval", seed_offset=100 + len(metric_name))


def research_sample_files() -> list[Path]:
    sample_dir = PROJECT_ROOT / "app" / "logs" / "self_play_batch" / "research_samples"
    return sorted(sample_dir.glob("*.csv"))


def parse_research_sample_name(path: Path) -> tuple[int, str]:
    match = re.match(r"^(\d{2})_session_simulation_\d{2}_(.+)_result\.csv$", path.name)
    if not match:
        raise ValueError(f"Unexpected research sample filename: {path.name}")
    return int(match.group(1)), match.group(2)


def build_behavior_and_lengths(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    behavior_rows: list[dict[str, Any]] = []
    length_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    base_lookup = base.set_index(["generation_id", "client_type", "layer"])["script_id"].to_dict()
    meta_lookup = base.drop_duplicates(["generation_id", "client_type"]).set_index(["generation_id", "client_type"])

    for path in research_sample_files():
        generation_id, client_type = parse_research_sample_name(path)
        pair_id = make_pair_id(generation_id, client_type)
        meta = meta_lookup.loc[(generation_id, client_type)]
        df = pd.read_csv(path)
        counselor = df[df["speaker"].astype(str).eq("counselor")].copy()
        counts = {code: 0 for code in ["GI", "Persuade", "Persuade_with_Permission", "Q", "SR", "CR", "AF", "Seek", "Emphasize", "Confront"]}
        for action, count in counselor["main_action"].fillna("").astype(str).value_counts().items():
            code = ACTION_TO_CODE.get(action)
            if code:
                counts[code] += int(count)
            else:
                action_rows.append({"pair_id": pair_id, "unmapped_main_action": action, "count": int(count)})
        counts["AF"] += int((counselor["add_affirm"].fillna("NONE").astype(str) != "NONE").sum())
        total_reflection = counts["SR"] + counts["CR"]
        counselor_utterance_count = int(len(counselor))
        row = {
            "pair_id": pair_id,
            "situation": meta["situation"],
            "situation_code": meta["situation_code"],
            "perma_profile": meta["perma_profile"],
            "perma_code": meta["perma_code"],
            "generation_id": generation_id,
            "client_type": client_type,
            "behavior_source": str(path.relative_to(PROJECT_ROOT)),
            "behavior_coding_rule_version": "sap_v3.7_system_action_mapping_v1",
            "counselor_utterance_count": counselor_utterance_count,
            **counts,
        }
        row["total_reflection"] = total_reflection
        row["pct_complex_reflection"] = counts["CR"] / total_reflection if total_reflection > 0 else np.nan
        row["good_pct_complex_reflection"] = 1 if total_reflection > 0 and row["pct_complex_reflection"] >= 0.50 else 0
        if counts["Q"] == 0 and total_reflection > 0:
            row["reflection_question_ratio"] = np.inf
            row["reflection_question_ratio_finite"] = np.nan
            row["reflection_question_ratio_finite_log1p"] = np.nan
            row["good_reflection_question_ratio"] = 1
        elif counts["Q"] == 0 and total_reflection == 0:
            row["reflection_question_ratio"] = np.nan
            row["reflection_question_ratio_finite"] = np.nan
            row["reflection_question_ratio_finite_log1p"] = np.nan
            row["good_reflection_question_ratio"] = 0
        else:
            ratio = total_reflection / counts["Q"]
            row["reflection_question_ratio"] = ratio
            row["reflection_question_ratio_finite"] = ratio
            row["reflection_question_ratio_finite_log1p"] = np.log1p(ratio)
            row["good_reflection_question_ratio"] = 1 if ratio >= 2.0 else 0
        row["Total_MI_Adherent"] = counts["Seek"] + counts["AF"] + counts["Emphasize"]
        row["Total_MI_Non_Adherent"] = counts["Confront"] + counts["Persuade"]
        row["Q_per_counselor_utterance"] = counts["Q"] / counselor_utterance_count if counselor_utterance_count else np.nan
        row["total_reflection_per_counselor_utterance"] = total_reflection / counselor_utterance_count if counselor_utterance_count else np.nan
        row["Total_MI_Adherent_per_counselor_utterance"] = row["Total_MI_Adherent"] / counselor_utterance_count if counselor_utterance_count else np.nan
        row["Q_zero"] = int(counts["Q"] == 0)
        row["total_reflection_zero"] = int(total_reflection == 0)
        row["total_reflection_1_to_2"] = int(1 <= total_reflection <= 2)
        behavior_rows.append(row)

        client_text_total = df.loc[df["speaker"].astype(str).eq("client"), "text"].fillna("").astype(str).map(len).sum()
        for layer, text_col in [("Layer3", "draft_response_text"), ("Layer4", "text")]:
            script_id = base_lookup[(generation_id, client_type, layer)]
            counselor_chars = counselor[text_col].fillna("").astype(str).map(len).sum()
            length_rows.append(
                {
                    "script_id": script_id,
                    "pair_id": pair_id,
                    "layer": layer,
                    "generation_id": generation_id,
                    "client_type": client_type,
                    "counselor_utterance_count": counselor_utterance_count,
                    "counselor_char_count": int(counselor_chars),
                    "script_total_char_count": int(client_text_total + counselor_chars),
                    "source_csv": str(path.relative_to(PROJECT_ROOT)),
                }
            )

    return pd.DataFrame(behavior_rows), pd.DataFrame(length_rows), pd.DataFrame(action_rows)


def validation_summary(base: pd.DataFrame, global_long: pd.DataFrame, client: pd.DataFrame, behavior: pd.DataFrame) -> pd.DataFrame:
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    add("script_id_count", base["script_id"].nunique() == 60, str(base["script_id"].nunique()))
    add("pair_id_count", base["pair_id"].nunique() == 30, str(base["pair_id"].nunique()))
    pair_counts = base.groupby("pair_id")["layer"].agg(lambda s: ",".join(sorted(s)))
    add("each_pair_has_layer3_layer4", bool((pair_counts == "Layer3,Layer4").all()), f"violations={(pair_counts != 'Layer3,Layer4').sum()}")
    add("global_rating_rows", len(global_long) == 1200, str(len(global_long)))
    add("global_rating_range", global_long["rating_analysis"].dropna().between(1, 5).all(), "1.0-5.0")
    add("global_rating_half_steps", global_long["rating_analysis"].dropna().map(lambda x: np.isclose((x * 2) % 1, 0)).all(), "0.5-step values")
    add("client_naturalness_rows", len(client) == 240, str(len(client)))
    add("client_naturalness_range", client["client_naturalness_analysis"].dropna().between(1, 10).all(), "1-10")
    add("behavior_pair_rows", len(behavior) == 30, str(len(behavior)))
    code_cols = ["GI", "Persuade", "Persuade_with_Permission", "Q", "SR", "CR", "AF", "Seek", "Emphasize", "Confront"]
    behavior_values = behavior[code_cols].fillna(0)
    integer_ok = behavior_values.map(lambda x: float(x).is_integer()).all().all()
    add("behavior_nonnegative_integer", bool(behavior_values.ge(0).all().all() and integer_ok), "nonnegative integers")
    order_bias = (
        global_long.drop_duplicates(["script_id", "rater_id"])
        .groupby(["rater_id", "layer"])["presentation_order"]
        .mean()
        .unstack()
    )
    within_diffs = (order_bias["Layer4"] - order_bias["Layer3"]).abs()
    overall_diff = (
        global_long.drop_duplicates(["script_id", "rater_id"])
        .groupby("layer")["presentation_order"]
        .mean()
    )
    add(
        "presentation_order_large_imbalance",
        not ((within_diffs >= 10).any() or abs(overall_diff["Layer4"] - overall_diff["Layer3"]) >= 5),
        f"max_within={within_diffs.max():.3f}; overall_diff={abs(overall_diff['Layer4'] - overall_diff['Layer3']):.3f}",
    )
    return pd.DataFrame(checks)


def descriptive_tables(global_long: pd.DataFrame, tech: pd.DataFrame, client: pd.DataFrame, behavior: pd.DataFrame) -> dict[str, pd.DataFrame]:
    rating_desc = (
        global_long.groupby(["outcome", "layer"])["rating_analysis"]
        .agg(n="count", mean="mean", sd="std", median="median", min="min", max="max")
        .reset_index()
    )
    rating_dist = (
        global_long.groupby(["outcome", "layer", "rating_analysis"])
        .size()
        .reset_index(name="n")
    )
    good_desc = (
        tech.groupby("layer")
        .agg(
            n=("script_id", "count"),
            technical_global_mean=("technical_global", "mean"),
            technical_global_sd=("technical_global", "std"),
            relational_global_mean=("relational_global", "mean"),
            relational_global_sd=("relational_global", "std"),
            good_technical_rate=("good_technical_global", "mean"),
            good_relational_rate=("good_relational_global", "mean"),
        )
        .reset_index()
    )
    client_desc = (
        client.groupby(["situation", "perma_profile"])["client_naturalness_analysis"]
        .agg(n="count", mean="mean", sd="std", median="median", min="min", max="max")
        .reset_index()
    )
    behavior_desc = (
        behavior.groupby(["situation", "perma_profile"])
        .agg(
            n=("pair_id", "count"),
            Q_mean=("Q", "mean"),
            total_reflection_mean=("total_reflection", "mean"),
            pct_complex_reflection_mean=("pct_complex_reflection", "mean"),
            reflection_question_ratio_finite_mean=("reflection_question_ratio_finite", "mean"),
            Total_MI_Adherent_mean=("Total_MI_Adherent", "mean"),
            good_pct_complex_reflection_rate=("good_pct_complex_reflection", "mean"),
            good_reflection_question_ratio_rate=("good_reflection_question_ratio", "mean"),
        )
        .reset_index()
    )
    return {
        "rating_descriptives_by_layer": rating_desc,
        "rating_distribution_by_layer": rating_dist,
        "technical_relational_descriptives": good_desc,
        "client_naturalness_15cell_descriptives": client_desc,
        "behavior_code_15cell_descriptives": behavior_desc,
    }


def hypothesis1(global_long: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(20260507)
    for outcome, refs in PRIOR_REFERENCES.items():
        sub = global_long[(global_long["layer"] == "Layer3") & (global_long["outcome"] == outcome)].copy()
        script_values = (
            sub.groupby("script_id")
            .agg(
                script_mean=("rating_analysis", "mean"),
                script_mean_initial=("rating_initial", "mean"),
                n_raters=("rating_analysis", "count"),
            )
            .reset_index()
        )
        script_values = script_values[script_values["n_raters"] >= 3]
        values = script_values["script_mean"].to_numpy(dtype=float)
        boot_means = []
        for _ in range(10000):
            sample = rng.choice(values, size=len(values), replace=True)
            boot_means.append(np.mean(sample))
        mean_val = float(np.mean(values))
        sd_val = float(np.std(values, ddof=1))
        ci_low, ci_high = np.percentile(boot_means, [2.5, 97.5])
        initial_mean = float(script_values["script_mean_initial"].mean())
        for ref_name, (ref_mean, ref_sd) in refs.items():
            rows.append(
                {
                    "outcome": outcome,
                    "reference": ref_name,
                    "n_scripts": len(values),
                    "layer3_mean": mean_val,
                    "layer3_sd": sd_val,
                    "layer3_median": float(np.median(values)),
                    "layer3_iqr": float(np.percentile(values, 75) - np.percentile(values, 25)),
                    "bootstrap_ci_low": float(ci_low),
                    "bootstrap_ci_high": float(ci_high),
                    "reference_mean": ref_mean,
                    "reference_sd_descriptive": ref_sd,
                    "difference_layer3_minus_reference": mean_val - ref_mean,
                    "point_estimate_exceeds_reference": bool(mean_val > ref_mean),
                    "initial_unadjudicated_layer3_mean": initial_mean,
                    "initial_minus_analysis_mean": initial_mean - mean_val,
                }
            )
    return pd.DataFrame(rows)


def script_aggregate_sensitivity(global_long: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for outcome in OUTCOMES:
        script_means = (
            global_long[global_long["outcome"] == outcome]
            .groupby(["pair_id", "layer", "script_id"], as_index=False)
            .agg(script_mean=("rating_analysis", "mean"), n_raters=("rating_analysis", "count"))
        )
        script_means = script_means[script_means["n_raters"] >= 3]
        wide = script_means.pivot_table(index="pair_id", columns="layer", values="script_mean", aggfunc="first")
        wide["pair_diff_layer4_minus_layer3"] = wide["Layer4"] - wide["Layer3"]
        diffs = wide["pair_diff_layer4_minus_layer3"].dropna()
        rows.append(
            {
                "outcome": outcome,
                "n_pairs": len(diffs),
                "mean_pair_diff_layer4_minus_layer3": diffs.mean(),
                "sd_pair_diff": diffs.std(ddof=1),
                "median_pair_diff": diffs.median(),
                "min_pair_diff": diffs.min(),
                "max_pair_diff": diffs.max(),
                "n_pair_diff_positive": int((diffs > 0).sum()),
                "n_pair_diff_zero": int((diffs == 0).sum()),
                "n_pair_diff_negative": int((diffs < 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def package_versions() -> pd.DataFrame:
    packages = ["numpy", "pandas", "openpyxl"]
    rows = [
        {"name": "python", "version": sys.version.split()[0]},
        {"name": "platform", "version": platform.platform()},
        {"name": "executable", "version": sys.executable},
    ]
    for package in packages:
        try:
            module = __import__(package)
            version = getattr(module, "__version__", "unknown")
        except Exception as exc:  # pragma: no cover - diagnostic only
            version = f"unavailable: {exc}"
        rows.append({"name": package, "version": version})
    return pd.DataFrame(rows)


def run_r_models(dirs: OutputDirs) -> None:
    command = ["Rscript", str(R_SCRIPT), str(RESULTS_DIR)]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    (dirs.logs / "r_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (dirs.logs / "r_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"R model script failed with exit code {completed.returncode}. See {dirs.logs / 'r_stderr.txt'}")


def read_optional_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def render_report(dirs: OutputDirs, validation: pd.DataFrame, reliability: pd.DataFrame, h1: pd.DataFrame) -> None:
    primary = read_optional_csv(dirs.primary / "primary_layer_effects.csv")
    secondary = read_optional_csv(dirs.secondary / "good_threshold_layer_effects.csv")
    client_lmm = read_optional_csv(dirs.exploratory / "client_naturalness_context_lmm.csv")
    behavior_models = read_optional_csv(dirs.exploratory / "behavior_code_exploratory_models.csv")
    aggregate = read_optional_csv(dirs.sensitivity / "script_aggregate_pair_diff.csv")

    lines = [
        "# SAP v3.7 Analysis Report",
        "",
        f"Created at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Inputs and Fixed Decisions",
        "",
        f"- Input data: `{INPUT_XLSX.relative_to(PROJECT_ROOT)}`",
        "- Layer mapping: `draft_response_text` was treated as Layer3, and `text` was treated as Layer4.",
        "- Analysis values: for outcomes with initial ICC(2,k) below 0.50, the post-re-rating/adjudicated values in the nonpublic source workbook were used; that is, current rating columns rather than `rater_*_initial_*` columns.",
        "- Existing Layer-specific result files were not used for model selection or adjudication decisions.",
        "",
        "## Data Validation",
        "",
        simple_markdown_table(validation),
        "",
        "## Initial and Analysis-Value Reliability",
        "",
        simple_markdown_table(
            reliability[
                [
                    "timing",
                    "metric",
                    "n_cases",
                    "n_raters",
                    "ICC_A_1_absolute_single",
                    "ICC_A_k_absolute_average",
                    "krippendorff_alpha",
                    "mean_within_case_sd",
                    "mean_rating",
                ]
            ]
        ),
        "",
        "## Hypothesis 1: Descriptive Comparison With Prior Reference Values",
        "",
        simple_markdown_table(
            h1[
                [
                    "outcome",
                    "reference",
                    "n_scripts",
                    "layer3_mean",
                    "layer3_sd",
                    "bootstrap_ci_low",
                    "bootstrap_ci_high",
                    "reference_mean",
                    "difference_layer3_minus_reference",
                    "point_estimate_exceeds_reference",
                ]
            ]
        ),
        "",
        "## Hypothesis 2: Layer Effects for Primary Outcomes",
        "",
        simple_markdown_table(
            primary[
                [
                    "outcome",
                    "n",
                    "engine",
                    "fallback_step",
                    "OR",
                    "CI_low",
                    "CI_high",
                    "CI_method",
                    "p_value",
                    "holm_p",
                    "model_status",
                ]
            ]
            if not primary.empty
            else primary
        ),
        "",
        "## Secondary Analysis: Good-Threshold Achievement",
        "",
        simple_markdown_table(
            secondary[
                [
                    "outcome",
                    "n",
                    "engine",
                    "OR",
                    "CI_low",
                    "CI_high",
                    "p_value",
                    "holm_p",
                    "model_status",
                ]
            ]
            if not secondary.empty
            else secondary
        ),
        "",
        "## Exploratory Analyses",
        "",
        "### Client Naturalness",
        "",
        simple_markdown_table(client_lmm),
        "",
        "### Behavior-Code Models",
        "",
        simple_markdown_table(behavior_models),
        "",
        "## Script-Level Aggregate Sensitivity Analysis",
        "",
        simple_markdown_table(aggregate),
        "",
        "## Notes",
        "",
        "- No binary success/failure or supported/unsupported judgment is made for Hypothesis 2 as a whole.",
        "- Behavior codes are summaries of system action labels derived from Layer2, not MITI behavior counts assigned by human coders.",
        "- The `source_layer` term for client naturalness is a contextual adjustment/descriptive variable and should not be interpreted as a confirmatory Layer effect on counselor quality.",
    ]
    (dirs.report / "sap_v3_7_analysis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    os.chdir(PROJECT_ROOT)
    dirs = make_output_dirs()
    started = datetime.now()
    (dirs.logs / "run_started.txt").write_text(started.isoformat(timespec="seconds") + "\n", encoding="utf-8")
    write_csv(package_versions(), dirs.logs / "python_package_versions.csv")

    raw = pd.read_excel(INPUT_XLSX)
    base = build_case_base(raw)

    reliability_initial_global = build_global_reliability(base, SOURCE_INITIAL, "initial")
    reliability_initial_client = build_client_reliability(base, initial=True, timing="initial")
    reliability_initial = pd.concat([reliability_initial_global, reliability_initial_client], ignore_index=True)

    global_long = build_global_long(base, reliability_initial_global)
    client = build_client_context(base, reliability_initial_client)
    client_diff = add_client_context_diff(client)
    client_pair = client_pair_mean(client)
    tech = technical_relational(global_long)
    tech_reliability = pd.DataFrame(
        [
            build_technical_reliability(tech, "technical_global", "technical_global"),
            build_technical_reliability(tech, "relational_global", "relational_global"),
        ]
    )

    behavior, lengths, unmapped_actions = build_behavior_and_lengths(base)
    global_long = global_long.merge(lengths[["script_id", "counselor_utterance_count", "counselor_char_count", "script_total_char_count"]], on="script_id", how="left")
    tech = tech.merge(lengths[["script_id", "counselor_utterance_count", "counselor_char_count", "script_total_char_count"]], on="script_id", how="left")

    reliability_analysis_global = []
    for i, outcome in enumerate(OUTCOMES):
        mat = global_long[global_long["outcome"] == outcome].pivot_table(index="script_id", columns="rater_id", values="rating_analysis", aggfunc="first")
        reliability_analysis_global.append(reliability_for_matrix(mat[RATERS], outcome, "analysis", "ordinal", seed_offset=200 + i))
    mat_client_analysis = client.pivot_table(index="source_script_id", columns="rater_id", values="client_naturalness_analysis", aggfunc="first")
    reliability_analysis_client = reliability_for_matrix(mat_client_analysis[RATERS], "client_naturalness", "analysis", "interval", seed_offset=250)
    reliability_all = pd.concat(
        [
            reliability_initial,
            pd.DataFrame(reliability_analysis_global),
            pd.DataFrame([reliability_analysis_client]),
            tech_reliability,
        ],
        ignore_index=True,
    )

    validation = validation_summary(base, global_long, client, behavior)
    desc = descriptive_tables(global_long, tech, client, behavior)
    h1 = hypothesis1(global_long)
    aggregate = script_aggregate_sensitivity(global_long)

    write_csv(base, dirs.datasets / "internal_base_export_with_ids.csv")
    write_csv(global_long, dirs.datasets / "global_ratings_long.csv")
    write_csv(tech, dirs.datasets / "technical_relational_global.csv")
    write_csv(client, dirs.datasets / "client_naturalness_context.csv")
    write_csv(client_diff, dirs.datasets / "client_naturalness_context_differences.csv")
    write_csv(client_pair, dirs.datasets / "client_naturalness_pair_mean.csv")
    write_csv(behavior, dirs.datasets / "behavior_codes_pair.csv")
    write_csv(lengths, dirs.datasets / "script_length_metrics.csv")
    write_csv(unmapped_actions, dirs.validation / "unmapped_behavior_actions.csv")
    write_csv(validation, dirs.validation / "validation_summary.csv")
    write_csv(reliability_all, dirs.reliability / "reliability_summary.csv")
    write_csv(
        global_long[global_long["adjudication_flag"].ne("not_applicable")],
        dirs.adjudication / "global_rating_adjudication_inferred_flags.csv",
    )
    write_csv(
        client[client["client_naturalness_adjudication_flag"].ne("not_applicable")],
        dirs.adjudication / "client_naturalness_adjudication_inferred_flags.csv",
    )
    for name, table in desc.items():
        write_csv(table, dirs.descriptives / f"{name}.csv")
    write_csv(h1, dirs.hypothesis1 / "hypothesis1_layer3_prior_reference_comparison.csv")
    write_csv(aggregate, dirs.sensitivity / "script_aggregate_pair_diff.csv")

    behavior_mapping = pd.DataFrame(
        [
            {"main_action": action, "behavior_code": code}
            for action, code in sorted(ACTION_TO_CODE.items())
        ]
        + [{"main_action": "add_affirm != NONE", "behavior_code": "AF"}]
    )
    write_csv(behavior_mapping, dirs.datasets / "behavior_action_mapping.csv")

    run_r_models(dirs)
    render_report(dirs, validation, reliability_all, h1)
    completed = datetime.now()
    summary = {
        "started": started.isoformat(timespec="seconds"),
        "completed": completed.isoformat(timespec="seconds"),
        "duration_seconds": (completed - started).total_seconds(),
        "input": str(INPUT_XLSX.relative_to(PROJECT_ROOT)),
        "results_dir": str(RESULTS_DIR.relative_to(PROJECT_ROOT)),
        "n_scripts": int(base["script_id"].nunique()),
        "n_pairs": int(base["pair_id"].nunique()),
        "n_global_rows": int(len(global_long)),
        "n_client_rows": int(len(client)),
        "n_behavior_pairs": int(len(behavior)),
    }
    (dirs.logs / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
