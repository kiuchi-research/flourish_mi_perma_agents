from __future__ import annotations

"""
DSPy 最適化用のメトリクス（評価関数）

- A: reply_quality_metric
- B: phase_accuracy_metric / ctr_regression_metric
- C: session_score_metric（セッション全体の指標）
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import dspy

from mi_counselor_agent import MainAction, coerce_main_action, validate_output


# ----------------------------
# A: 発話生成のスコア
# ----------------------------
_EMPATHY_MARKERS = [
    "なるほど",
    "そうなのですね",
    "お気持ち",
    "大変",
    "つら",
    "しんど",
    "難し",
    "戸惑",
    "悩",
    "心配",
]
_LECTURE_MARKERS = [
    "すべき",
    "しなければ",
    "必ず",
    "当然",
    "間違って",
]


def _contains_any(text: str, markers: List[str]) -> bool:
    return any(m in text for m in markers)


def _sentence_count_rough(text: str) -> int:
    # 日本語の厳密な文分割は難しいので、句点・改行でざっくり
    parts = re.split(r"[。！？\n]+", text.strip())
    parts = [p for p in parts if p.strip()]
    return len(parts)


def reply_quality_metric(example: dspy.Example, pred: dspy.Prediction, trace=None) -> float:
    """
    0.0〜1.0 を返す（trace があるときは bool を返してもよい）
    """
    action = coerce_main_action(getattr(example, "main_action", "")) or MainAction.REFLECT

    text = str(getattr(pred, "reply", "")).strip()
    ok, reason = validate_output(action, text)
    if not ok:
        return False if trace is not None else 0.0

    score = 0.55  # 形式OKの最低点

    # 共感の雰囲気
    if _contains_any(text, _EMPATHY_MARKERS):
        score += 0.15

    # 説教調を避ける
    if not _contains_any(text, _LECTURE_MARKERS):
        score += 0.10

    # 長さ（短すぎ/長すぎを抑える）
    n_sent = _sentence_count_rough(text)
    if 1 <= n_sent <= 4:
        score += 0.10
    elif n_sent >= 7:
        score -= 0.10

    # add_affirm=True のとき、強み/努力の認めがあると加点（簡易）
    if bool(getattr(example, "add_affirm", False)):
        if any(w in text for w in ["工夫", "努力", "大事に", "強み", "前進", "できて"]):
            score += 0.10
        else:
            score -= 0.05

    # クリップ
    score = max(0.0, min(1.0, score))

    if trace is not None:
        return score >= 0.75
    return score


# ----------------------------
# B: フェーズ分類 accuracy
# ----------------------------
def phase_accuracy_metric(example: dspy.Example, pred: dspy.Prediction, trace=None) -> float:
    gold = str(getattr(example, "phase", "")).strip()
    out = str(getattr(pred, "phase", "")).strip()
    ok = (gold == out) and bool(gold)
    if trace is not None:
        return ok
    return 1.0 if ok else 0.0


# ----------------------------
# B: change_talk / resistance 回帰っぽい評価
#   - 1 - MAE を 0..1 に丸める
# ----------------------------
def _clip01(x: float) -> float:
    if x != x:
        return 0.0
    return max(0.0, min(1.0, float(x)))


def ctr_regression_metric(example: dspy.Example, pred: dspy.Prediction, trace=None) -> float:
    try:
        gold_ct = _clip01(float(getattr(example, "change_talk")))
        gold_rs = _clip01(float(getattr(example, "resistance")))
    except Exception:
        # ラベルなしなら評価しない（=0.5扱い）
        return 0.5

    try:
        out_ct = _clip01(float(getattr(pred, "change_talk")))
        out_rs = _clip01(float(getattr(pred, "resistance")))
    except Exception:
        return False if trace is not None else 0.0

    mae = (abs(gold_ct - out_ct) + abs(gold_rs - out_rs)) / 2.0
    score = 1.0 - mae
    score = max(0.0, min(1.0, score))
    if trace is not None:
        return score >= 0.8
    return score


# ----------------------------
# C: セッション全体スコア
#   - MISessionDriverProgram の pred.session_log を使う
# ----------------------------
def score_session_log(session_log: List[Dict[str, Any]]) -> float:
    """
    0.0〜1.0 くらいのスコアを返す（完全に研究用の簡易指標です）
    """
    if not session_log:
        return 0.0

    actions: List[str] = []
    reflect_streak = 0
    max_reflect_streak = 0

    # 条件付き評価
    ct_reward = 0.0
    rs_reward = 0.0
    n_ct = 0
    n_rs = 0

    # 形式違反チェック
    format_penalty = 0.0

    ask_permission_count = 0
    provide_info_count = 0

    for t in session_log:
        act = str(t.get("main_action", "")).strip()
        text = str(t.get("counselor", "")).strip()
        actions.append(act)

        if act == "REFLECT":
            reflect_streak += 1
            max_reflect_streak = max(max_reflect_streak, reflect_streak)
        else:
            reflect_streak = 0

        # 形式チェック（validate_output）
        parsed_action = coerce_main_action(act)
        if parsed_action is None:
            ok = True
        else:
            ok, _ = validate_output(parsed_action, text)
        if not ok:
            format_penalty += 0.15

        feats = t.get("features") or {}
        ct = float(feats.get("change_talk", 0.0) or 0.0)
        rs = float(feats.get("resistance", 0.0) or 0.0)

        if ct >= 0.6:
            n_ct += 1
            if act == "REFLECT":
                ct_reward += 1.0
            elif act == "SUMMARY":
                ct_reward += 0.6
            else:
                ct_reward += 0.2

        if rs >= 0.6:
            n_rs += 1
            if act in ("REFLECT", "SUMMARY", "ASK_PERMISSION_TO_SHARE_INFO"):
                rs_reward += 1.0
            elif act == "QUESTION":
                rs_reward += 0.0
            else:
                rs_reward += 0.5

        if act == "ASK_PERMISSION_TO_SHARE_INFO":
            ask_permission_count += 1
        if act == "PROVIDE_INFO":
            provide_info_count += 1

    # 全体の REFLECT / QUESTION バランス
    reflect = sum(1 for a in actions if a == "REFLECT")
    question = sum(1 for a in actions if a == "QUESTION")
    denom = max(1, (reflect + question))
    reflect_ratio = reflect / denom

    # スコア組み立て
    score = 0.4

    # 形式が崩れないこと
    score += max(0.0, 0.3 - format_penalty)

    # 反射ストリークが長すぎない（ただしCTが強いときは許容されるので緩め）
    if max_reflect_streak <= 4:
        score += 0.10
    elif max_reflect_streak >= 7:
        score -= 0.10

    # REFLECT比（0.45〜0.85くらいを軽く推奨）
    if 0.45 <= reflect_ratio <= 0.85:
        score += 0.10
    else:
        score -= 0.05

    # 条件付き（CT/抵抗）応答
    if n_ct > 0:
        score += 0.10 * (ct_reward / n_ct)
    if n_rs > 0:
        score += 0.10 * (rs_reward / n_rs)

    # 情報提供があるなら、ASK_PERMISSION_TO_SHARE_INFO が一度もないのはペナルティ
    if provide_info_count > 0 and ask_permission_count == 0:
        score -= 0.10

    score = max(0.0, min(1.0, score))
    return score


def session_score_metric(example: dspy.Example, pred: dspy.Prediction, trace=None) -> float:
    session_log = getattr(pred, "session_log", None)
    if not isinstance(session_log, list):
        return False if trace is not None else 0.0
    s = score_session_log(session_log)
    if trace is not None:
        return s >= 0.75
    return s
