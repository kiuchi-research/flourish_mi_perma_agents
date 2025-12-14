from __future__ import annotations

from typing import Any, Dict, Optional

from env_utils import build_llm_from_config, get_model_config
from mi_counselor_agent import (
    LLMMIEvaluator,
    LLMActionRanker,
    LLMPhaseClassifier,
    LLMRiskDetector,
    MIRhythmBot,
)


def _build_optional_phase_classifier(api_key: str, cfg: Dict[str, Any]) -> Optional[LLMPhaseClassifier]:
    """enabled が真のときだけ LLMPhaseClassifier を生成する。"""
    if not cfg:
        return None
    if cfg.get("enabled") is False:
        return None
    llm = build_llm_from_config(cfg, api_key)
    # フェーズ判定は直前のやり取りに寄せるため、参照履歴を短めにする
    return LLMPhaseClassifier(llm=llm, temperature=0.0, max_history_turns=2)


def _build_optional_action_ranker(api_key: str, cfg: Dict[str, Any]) -> Optional[LLMActionRanker]:
    """enabled が真のときだけ LLMActionRanker を生成する。"""
    if not cfg:
        return None
    if cfg.get("enabled") is False:
        return None
    llm = build_llm_from_config(cfg, api_key)
    return LLMActionRanker(llm=llm)


def _build_optional_risk_detector(api_key: str, cfg: Dict[str, Any]) -> Optional[LLMRiskDetector]:
    """enabled が真のときだけ LLMRiskDetector を生成する。"""
    if not cfg:
        return None
    if cfg.get("enabled") is False:
        return None
    llm = build_llm_from_config(cfg, api_key)
    temperature = float(cfg.get("temperature", 0.0) or 0.0)
    max_history_turns = int(cfg.get("max_history_turns", 8) or 8)
    return LLMRiskDetector(llm=llm, temperature=temperature, max_history_turns=max_history_turns)


def _build_optional_mi_evaluator(api_key: str, cfg: Dict[str, Any]) -> Optional[LLMMIEvaluator]:
    """enabled が真のときだけ LLMMIEvaluator を生成する。"""
    if not cfg:
        return None
    if cfg.get("enabled") is False:
        return None
    llm = build_llm_from_config(cfg, api_key)
    temperature = float(cfg.get("temperature", 0.0) or 0.0)
    max_history_turns = int(cfg.get("max_history_turns", 6) or 6)
    return LLMMIEvaluator(llm=llm, temperature=temperature, max_history_turns=max_history_turns)


def _extract_rewrite_threshold(cfg: Dict[str, Any]) -> Optional[float]:
    """rewrite_threshold を float で取り出す（無効なら None）。"""
    threshold = cfg.get("rewrite_threshold")
    if threshold is None:
        return None
    try:
        return float(threshold)
    except Exception:
        return None


def build_counselor_stack(
    *,
    api_key: str,
) -> Dict[str, Any]:
    """
    カウンセラーボットと周辺の分類器/評価器をまとめて構築する共通ビルダー。
    """
    counselor_cfg = get_model_config("counselor_llm", role="counselor")
    counselor_phase_cfg = get_model_config("counselor_phase", role="counselor")
    counselor_action_cfg = get_model_config("counselor_action", role="counselor")
    risk_detector_cfg = get_model_config("counselor_risk_detector", role="counselor")
    mi_evaluator_cfg = get_model_config("counselor_mi_evaluator", role="counselor")

    llm = build_llm_from_config(counselor_cfg, api_key)
    phase_classifier = _build_optional_phase_classifier(api_key, counselor_phase_cfg)
    action_ranker = _build_optional_action_ranker(api_key, counselor_action_cfg)
    risk_detector = _build_optional_risk_detector(api_key, risk_detector_cfg)
    mi_evaluator = _build_optional_mi_evaluator(api_key, mi_evaluator_cfg)
    rewrite_threshold = _extract_rewrite_threshold(mi_evaluator_cfg)

    counselor = MIRhythmBot(
        llm=llm,
        phase_classifier=phase_classifier,
        action_ranker=action_ranker,
        risk_detector=risk_detector,
        output_evaluator=mi_evaluator,
        evaluation_rewrite_threshold=rewrite_threshold,
    )

    return {
        "counselor": counselor,
        "llm": llm,
        "counselor_cfg": counselor_cfg,
        "phase_cfg": counselor_phase_cfg,
        "action_cfg": counselor_action_cfg,
        "risk_cfg": risk_detector_cfg,
        "mi_eval_cfg": mi_evaluator_cfg,
    }
