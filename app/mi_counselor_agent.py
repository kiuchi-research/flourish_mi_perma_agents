from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from enum import Enum
import math
import random
import re
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from openai_llm import OpenAIResponsesLLM


# ============================
# 8フェーズ（最終目標の定義）
# ============================
class Phase(str, Enum):
    GREETING = "あいさつ"
    PURPOSE_CONFIRMATION = "目的確認"
    CURRENT_STATUS_CHECK = "現状確認"
    FOCUSING_TARGET_BEHAVIOR = "標的行動焦点化"
    IMPORTANCE_PROMOTION = "重要度促進"
    CONFIDENCE_PROMOTION = "自信度促進"
    NEXT_STEP_DECISION = "次の一歩決定"
    CLOSING = "クロージング"


class MainAction(str, Enum):
    REFLECT = "REFLECT"                # 聞き返し（言い換え）
    QUESTION = "QUESTION"              # 質問
    SUMMARY = "SUMMARY"                # 要約
    ASK_PERMISSION = "ASK_PERMISSION"  # 許可を得る（情報共有の前段）
    PROVIDE_INFO = "PROVIDE_INFO"      # 情報共有（＋反応を聞く）


class InfoMode(str, Enum):
    NONE = "NONE"
    WAITING_PERMISSION = "WAITING_PERMISSION"
    READY_TO_PROVIDE = "READY_TO_PROVIDE"


class ReflectionStyle(str, Enum):
    SIMPLE = "simple"        # 事実の言い換え中心
    COMPLEX = "complex"      # 感情や価値を織り込む
    DOUBLE_SIDED = "double"  # 両価性（やりたい/やりたくない両方）をまとめる


class RiskLevel(str, Enum):
    NONE = "none"
    MILD = "mild"
    HIGH = "high"


@dataclass
class RiskAssessment:
    level: RiskLevel = RiskLevel.NONE
    reason: Optional[str] = None
    raw_output: Optional[str] = None


@dataclass
class OutputEvaluation:
    score: float
    feedback: Optional[str] = None
    raw_output: Optional[str] = None
    rewrite: Optional[str] = None


class LLMClient(Protocol):
    """LLM呼び出しは環境に合わせて差し替えてください。"""

    def generate(self, messages: List[Dict[str, str]], *, temperature: float = 0.2) -> str:
        ...


@dataclass
class PlannerConfig:
    """
    ルールベースの調整ノブ（DsPy最適化前のベースライン）。
    - stochastic=False なら決定論で再現性重視（ログ収集・評価向き）
    - reflect_* は反射の連打を抑えるノブ
    - summary_* は要約の頻度・トリガー
    - allow_override_* は「チェンジトーク/抵抗/新情報」時に反射上限を緩める条件
    """
    # softmax温度（stochastic=False でも重み計算には効く）
    temperature: float = 0.7
    # スコアから確率を作ったあと、サンプリングするか（False=常にargmaxで再現性優先）
    stochastic: bool = False
    # 乱数シード（stochastic=True 時の揺らぎ再現用）
    seed: int = 42

    # 連続聞き返しペナルティ：3回目以降に掛ける減衰率（0〜1、小さいほど強い抑制）
    reflect_decay_base: float = 0.65
    # 連続聞き返しが多いときの上限（例：0.15=15%まで）
    reflect_prob_cap_after_streak: float = 0.15
    reflect_streak_cap_threshold: int = 5

    # 要約を促す閾値（最後の要約からのターン数）
    summary_interval_turns: int = 6
    # 連続反射がこの回数以上なら要約/質問を押す
    summary_reflect_streak_trigger: int = 3

    # 「例外で反射上限を解除」判定の閾値（0〜1）
    allow_override_change_talk: float = 0.6
    allow_override_resistance: float = 0.6
    allow_override_novelty: float = 0.7


@dataclass
class DialogueState:
    # 8フェーズの初期値：最初は「あいさつ」から開始
    phase: Phase = Phase.GREETING

    # リズム制御のための状態
    r_since_q: int = 0              # 最後の質問から何回「非質問」が続いたか
    reflect_streak: int = 0         # 連続でREFLECTした回数（単調さ抑制用）
    turns_since_summary: int = 0    # 最後の要約から何ターンか
    turns_since_affirm: int = 0     # 最後に是認を入れてから何ターンか

    # 情報共有（EPE: Elicit-Provide-Elicit）管理
    info_mode: InfoMode = InfoMode.NONE

    # 参照用
    last_user_text: str = ""
    turn_index: int = 0
    last_actions: List[MainAction] = field(default_factory=list)

    # フェーズを跨いで参照するスロット
    goal_description: Optional[str] = None
    target_behavior: Optional[str] = None
    client_values: List[str] = field(default_factory=list)
    next_step: Optional[str] = None

    # 安全関連のメモ
    risk_level: RiskLevel = RiskLevel.NONE
    last_risk_reason: Optional[str] = None


@dataclass
class PlannerFeatures:
    user_is_question: bool
    user_requests_info: bool
    has_permission: Optional[bool]  # None=不明, True/False=明確
    resistance: float               # 0〜1（高いほど抵抗っぽい）
    change_talk: float              # 0〜1（高いほどチェンジトークっぽい）
    novelty: float                  # 0〜1（高いほど新情報）
    is_short_reply: bool            # 非常に短い返答かどうか
    topic_shift: bool
    need_summary: bool
    allow_reflect_override: bool


@dataclass
class Decision:
    phase: Phase
    main_action: MainAction
    add_affirm: bool
    # 次状態（このDecisionを採用した後の想定状態）
    next_state: DialogueState
    debug: Dict[str, Any] = field(default_factory=dict)


# ============================
# 差し替え可能な分類・提案器
# ============================
class PhaseClassifier(Protocol):
    """
    フェーズ判定器（LLM/DSPy/ルールなど差し替え可能）。
    - 戻り値: (phase, debug)
    - debug には confidence / raw_output など任意で入れてOK。
    """

    def classify(
        self,
        *,
        history: List[Tuple[str, str]],
        state: DialogueState,
        user_text: str,
    ) -> Tuple[Phase, Dict[str, Any]]:
        ...


class ActionRanker(Protocol):
    """
    主動作（OARS + 例外）の優先順位提案器（DSPyで最適化しやすい差し込み口）。
    - 例: [REFLECT, SUMMARY, QUESTION] のような“順位リスト”を返す。
    """

    def rank(
        self,
        *,
        history: List[Tuple[str, str]],
        state: DialogueState,
        features: PlannerFeatures,
    ) -> Tuple[List[MainAction], Dict[str, Any]]:
        ...


class FeatureExtractor(Protocol):
    """
    特徴量抽出器（ルール/LLMで差し替え可）。
    - 戻り値: (PlannerFeatures, debug)
    """

    def extract(
        self,
        *,
        user_text: str,
        state: DialogueState,
        cfg: PlannerConfig,
        history: List[Tuple[str, str]],
    ) -> Tuple[PlannerFeatures, Dict[str, Any]]:
        ...


class RiskDetector(Protocol):
    """
    安全性リスク検知（自傷他害など）。
    - 戻り値: RiskAssessment
    """

    def detect(
        self,
        *,
        user_text: str,
        history: List[Tuple[str, str]],
        state: DialogueState,
    ) -> RiskAssessment:
        ...


class OutputEvaluator(Protocol):
    """
    生成応答のMI準拠評価器（LLM採点など）。
    """

    def evaluate(
        self,
        *,
        action: MainAction,
        assistant_text: str,
        history: List[Tuple[str, str]],
        state: DialogueState,
    ) -> OutputEvaluation:
        ...


# ----------------------------
# Feature extraction (軽量版)
# ----------------------------
_RE_QUESTION = re.compile(r"[？?]|(でしょうか)|(ですか)|(ますか)")
_RE_INFO_REQ = re.compile(r"(教えて|知りたい|情報|アドバイス|提案|方法|コツ|おすすめ|どうすれば|どうしたら)")
_RE_YES = re.compile(r"^(はい|ええ|うん|お願いします|お願い|いいです|大丈夫|ok|OK|了解|ぜひ|是非)", re.IGNORECASE)
_RE_NO = re.compile(r"^(いいえ|いや|やめて|いりません|不要|結構です|ノー|no|NO)", re.IGNORECASE)

# 抵抗（抵抗・反発）のシグナル（雑でOK：最初はルールが主）
_RESIST_MARKERS = [
    # 典型的な拒否・反発
    "でも", "けど", "しかし", "無理", "できない", "難しい", "やりたくない", "嫌", "意味ない",
    "必要ない", "無駄", "どうせ", "無理だ", "しんどい", "めんどくさい", "やる気が出ない",
    # 両価性の後ろ向き側
    "前にも失敗", "うまくいかない", "続かない", "気が進まない",
]

# チェンジトーク（変化への志向）のシグナル
_CHANGE_TALK_MARKERS = [
    # 前向き・志向性
    "したい", "やってみる", "やってみたい", "変えたい", "変わりたい", "頑張る", "できそう",
    "必要", "大事", "大切", "目標", "挑戦", "改善", "やったほうがいい", "続けたい",
    "もう少し", "試したい", "取り組みたい", "できるように",
]


def _char_bigrams(text: str) -> set:
    t = re.sub(r"\s+", "", text)
    if len(t) < 2:
        return {t} if t else set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _estimate_novelty(user_text: str, last_user_text: str) -> float:
    # 1) 文字bi-gramの差
    sim = _jaccard(_char_bigrams(user_text), _char_bigrams(last_user_text))
    novelty = 1.0 - sim

    # 2) 数字・日時っぽいものが増えたらブースト
    nums_now = set(re.findall(r"\d+", user_text))
    nums_prev = set(re.findall(r"\d+", last_user_text))
    if nums_now - nums_prev:
        novelty = min(1.0, novelty + 0.15)

    # 3) 固有っぽい語（簡易：カタカナ連続）が増えたら少しブースト
    kata_now = set(re.findall(r"[ァ-ヴー]{3,}", user_text))
    kata_prev = set(re.findall(r"[ァ-ヴー]{3,}", last_user_text))
    if kata_now - kata_prev:
        novelty = min(1.0, novelty + 0.10)

    # 4) 極端に短い入力でも、完全に0にはしない（過去を踏まえ反射できるため）
    if len(re.sub(r"\s+", "", user_text)) <= 8:
        novelty = max(novelty, 0.15)

    return max(0.0, min(1.0, novelty))


def _score_from_markers(text: str, markers: Sequence[str], *, cap: int = 4) -> float:
    hits = sum(1 for m in markers if m in text)
    return min(1.0, hits / cap)


def _detect_permission(text: str) -> Optional[bool]:
    t = text.strip()
    if _RE_YES.search(t):
        return True
    if _RE_NO.search(t):
        return False
    if "いいですよ" in t or "大丈夫です" in t:
        return True
    if "やめて" in t or "やめてください" in t:
        return False
    return None


def _parse_json_from_text(text: str) -> Optional[Any]:
    """
    LLM出力から最初のJSONオブジェクト/配列を抜き出してパースするゆるいヘルパ。
    - ```json ... ``` のコードブロックや前後の説明を取り除く。
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


def extract_features_rule(user_text: str, state: DialogueState, cfg: PlannerConfig) -> PlannerFeatures:
    """
    入力発話からルールベースの特徴量を抽出。
    - resistance / change_talk はマーカーリストに基づくスコア（実ログで拡張予定）
    - novelty は bi-gram 類似度＋数字/固有語の出現で新情報らしさを拾う
    - allow_reflect_override が True なら、連続反射キャップを緩める
    """
    user_is_question = bool(_RE_QUESTION.search(user_text))
    user_requests_info = bool(_RE_INFO_REQ.search(user_text))
    has_permission = _detect_permission(user_text) if state.info_mode == InfoMode.WAITING_PERMISSION else None

    resistance = _score_from_markers(user_text, _RESIST_MARKERS)
    change_talk = _score_from_markers(user_text, _CHANGE_TALK_MARKERS)

    novelty = _estimate_novelty(user_text, state.last_user_text)
    topic_shift = novelty >= 0.85 and len(re.sub(r"\s+", "", user_text)) >= 15
    clean_len = len(re.sub(r"\s+", "", user_text))
    is_short_reply = clean_len <= 12

    need_summary = (
        state.turns_since_summary >= cfg.summary_interval_turns
        or state.reflect_streak >= cfg.summary_reflect_streak_trigger
        or topic_shift
    )

    allow_reflect_override = (
        change_talk >= cfg.allow_override_change_talk
        or resistance >= cfg.allow_override_resistance
        or novelty >= cfg.allow_override_novelty
    )

    return PlannerFeatures(
        user_is_question=user_is_question,
        user_requests_info=user_requests_info,
        has_permission=has_permission,
        resistance=resistance,
        change_talk=change_talk,
        novelty=novelty,
        is_short_reply=is_short_reply,
        topic_shift=topic_shift,
        need_summary=need_summary,
        allow_reflect_override=allow_reflect_override,
    )


def extract_features(user_text: str, state: DialogueState, cfg: PlannerConfig) -> PlannerFeatures:
    """
    後方互換のためのエイリアス。ルール版の特徴量抽出を呼び出します。
    """
    return extract_features_rule(user_text, state, cfg)


@dataclass
class RuleBasedFeatureExtractor:
    """
    既存のルールベース特徴量抽出のラッパー。
    """

    def extract(
        self,
        *,
        user_text: str,
        state: DialogueState,
        cfg: PlannerConfig,
        history: List[Tuple[str, str]],
    ) -> Tuple[PlannerFeatures, Dict[str, Any]]:
        features = extract_features_rule(user_text, state, cfg)
        return features, {"method": "rule"}


@dataclass
class LLMFeatureExtractor:
    """
    LLMを用いて抵抗/チェンジトーク/新情報度などをスコア化する抽出器。
    ルール版をフォールバック兼ベースラインとして併用する。
    """

    llm: LLMClient
    temperature: float = 0.2
    max_history_turns: int = 6
    rule_fallback: RuleBasedFeatureExtractor = field(default_factory=RuleBasedFeatureExtractor)

    def extract(
        self,
        *,
        user_text: str,
        state: DialogueState,
        cfg: PlannerConfig,
        history: List[Tuple[str, str]],
    ) -> Tuple[PlannerFeatures, Dict[str, Any]]:
        base_features, base_debug = self.rule_fallback.extract(
            user_text=user_text, state=state, cfg=cfg, history=history
        )

        dialogue = _history_to_dialogue(history, max_turns=self.max_history_turns)
        system = (
            "あなたは動機づけ面接（MI）の対話から特徴量を数値で推定するアナリストです。\n"
            "抵抗（0〜1）、変化への前向きさ（チェンジトーク:0〜1）、新情報度（0〜1）などを推定してください。\n"
            "出力は JSON オブジェクトのみ。例：\n"
            '{"resistance":0.2,"change_talk":0.6,"novelty":0.4,"user_is_question":false,"user_requests_info":false,"has_permission":null,"note":"短い返答"}\n'
            "- 抵抗: 反発・拒否・諦めを示すほど1に近い。\n"
            "- 変化への前向きさ: 変えたい・やってみたい・価値に沿いたいほど1に近い。\n"
            "- 新情報度: 直前までと比べて内容が新しいほど1に近い。\n"
            "- user_is_question: クライアント発話が質問なら true。\n"
            "- user_requests_info: 情報提供の要望なら true。\n"
            "- has_permission: 許可が明確なら true/false、不明なら null。\n"
        )
        user = (
            f"【現在フェーズ】{state.phase.value}\n"
            f"【直近の対話（新しい順ではなく発話順）】\n{dialogue}\n"
            f"【今回のクライアント発話】{user_text}\n"
            "上記を踏まえて JSON だけを返してください。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = self.llm.generate(messages, temperature=self.temperature)
        parsed = _parse_json_from_text(raw)
        overlay: Dict[str, Any] = parsed if isinstance(parsed, dict) else {}

        def _clamp(v: Any) -> float:
            try:
                return float(max(0.0, min(1.0, float(v))))
            except Exception:
                return 0.0

        resistance = _clamp(overlay.get("resistance", base_features.resistance))
        change_talk = _clamp(overlay.get("change_talk", base_features.change_talk))
        novelty = _clamp(overlay.get("novelty", base_features.novelty))
        user_is_question = bool(overlay.get("user_is_question", base_features.user_is_question))
        user_requests_info = bool(overlay.get("user_requests_info", base_features.user_requests_info))
        has_permission_val = overlay.get("has_permission", base_features.has_permission)
        has_permission: Optional[bool]
        if has_permission_val is None or has_permission_val == "":
            has_permission = None
        elif isinstance(has_permission_val, bool):
            has_permission = has_permission_val
        elif str(has_permission_val).lower() in {"true", "yes", "y"}:
            has_permission = True
        elif str(has_permission_val).lower() in {"false", "no", "n"}:
            has_permission = False
        else:
            has_permission = base_features.has_permission

        clean_len = len(re.sub(r"\s+", "", user_text))
        topic_shift = novelty >= 0.85 and clean_len >= 15
        need_summary = (
            state.turns_since_summary >= cfg.summary_interval_turns
            or state.reflect_streak >= cfg.summary_reflect_streak_trigger
            or topic_shift
        )
        allow_reflect_override = (
            change_talk >= cfg.allow_override_change_talk
            or resistance >= cfg.allow_override_resistance
            or novelty >= cfg.allow_override_novelty
        )

        merged = dataclasses.replace(
            base_features,
            resistance=resistance,
            change_talk=change_talk,
            novelty=novelty,
            user_is_question=user_is_question,
            user_requests_info=user_requests_info,
            has_permission=has_permission,
            topic_shift=topic_shift,
            need_summary=need_summary,
            allow_reflect_override=allow_reflect_override,
        )

        debug: Dict[str, Any] = {
            "method": "llm",
            "raw_output": raw,
            "parsed": overlay,
            "fallback": base_debug,
        }
        return merged, debug


# ----------------------------
# Planning (方策：ルール＋確率)
# ----------------------------
def _softmax(scores: Dict[MainAction, float], temperature: float) -> Dict[MainAction, float]:
    t = max(1e-6, temperature)
    m = max(scores.values()) if scores else 0.0
    exp_scores = {k: math.exp((v - m) / t) for k, v in scores.items()}
    z = sum(exp_scores.values()) or 1.0
    return {k: v / z for k, v in exp_scores.items()}


def _sample_action(probs: Dict[MainAction, float], rng: random.Random) -> MainAction:
    r = rng.random()
    cum = 0.0
    last = None
    for k, p in probs.items():
        last = k
        cum += p
        if r <= cum:
            return k
    return last or MainAction.REFLECT


# フェーズごとの「軽い」事前バイアス（強すぎるとリズムが壊れるので控えめに）
_PHASE_ACTION_MULTIPLIERS: Dict[Phase, Tuple[float, float, float]] = {
    # (reflect_mul, question_mul, summary_mul)
    Phase.GREETING: (0.95, 1.25, 0.80),
    Phase.PURPOSE_CONFIRMATION: (0.95, 1.25, 0.85),
    Phase.CURRENT_STATUS_CHECK: (1.20, 0.95, 0.95),
    Phase.FOCUSING_TARGET_BEHAVIOR: (0.95, 1.10, 1.15),
    Phase.IMPORTANCE_PROMOTION: (1.10, 1.15, 0.90),
    Phase.CONFIDENCE_PROMOTION: (1.10, 1.10, 0.90),
    Phase.NEXT_STEP_DECISION: (0.95, 1.05, 1.25),
    Phase.CLOSING: (0.95, 0.85, 1.35),
}


def plan_next_action(
    *,
    state: DialogueState,
    features: PlannerFeatures,
    cfg: PlannerConfig,
    llm_rank_bias: Optional[List[MainAction]] = None,
) -> Tuple[MainAction, Dict[str, Any]]:
    """
    llm_rank_bias: LLM/DSPyが提案する優先順位（例：[REFLECT, SUMMARY, QUESTION]）。
    ルール側で最終決定するが、スコアに軽くバイアスを乗せる。
    """
    debug: Dict[str, Any] = {}

    # 1) 情報共有モード（EPE）の優先制御
    if state.info_mode == InfoMode.WAITING_PERMISSION:
        if features.has_permission is True:
            debug["info_mode_transition"] = "WAITING_PERMISSION -> READY_TO_PROVIDE"
            return MainAction.PROVIDE_INFO, debug
        if features.has_permission is False:
            debug["info_mode_transition"] = "WAITING_PERMISSION -> NONE (permission denied)"
        else:
            debug["info_mode_transition"] = "WAITING_PERMISSION (unclear), ask again"
            return MainAction.ASK_PERMISSION, debug

    if state.info_mode == InfoMode.READY_TO_PROVIDE:
        debug["info_mode_transition"] = "READY_TO_PROVIDE -> PROVIDE_INFO"
        return MainAction.PROVIDE_INFO, debug

    # 2) ユーザが情報を求めたら、まず許可を取る
    if features.user_requests_info:
        debug["trigger"] = "user_requests_info -> ASK_PERMISSION"
        return MainAction.ASK_PERMISSION, debug

    # 3) 通常のスコアリング
    # ベース：RRQの癖（r_since_q）
    if state.r_since_q == 0:
        reflect_score = 3.0
        question_score = 1.6
    elif state.r_since_q == 1:
        reflect_score = 2.3
        question_score = 2.2
    else:
        reflect_score = 1.2
        question_score = 3.2

    summary_score = 0.9
    if features.need_summary:
        summary_score += 2.4

    # フェーズごとの軽い事前バイアス
    rm, qm, sm = _PHASE_ACTION_MULTIPLIERS.get(state.phase, (1.0, 1.0, 1.0))
    reflect_score *= rm
    question_score *= qm
    summary_score *= sm

    # 連続反射ペナルティ（3回目以降）
    decay_steps = max(0, state.reflect_streak - 2)
    reflect_decay = cfg.reflect_decay_base ** decay_steps
    reflect_score *= reflect_decay

    # 新情報/チェンジトークが出たら反射を少し上げる（短文でも可能）
    reflect_score *= (1.0 + 0.55 * features.novelty + 0.45 * features.change_talk)

    # 抵抗が強い時：質問を少し控え、反射を上げる
    if features.resistance >= 0.6:
        reflect_score *= 1.25
        question_score *= 0.75

    # ユーザが質問してきたら、こちらも質問寄り
    if features.user_is_question:
        question_score += 1.1

    # 反射が続いてきたら、質問と要約を押す
    if state.reflect_streak >= 3:
        question_score *= (1.0 + 0.18 * (state.reflect_streak - 2))
        summary_score *= (1.0 + 0.22 * (state.reflect_streak - 2))

    # 反射が5回以上続いているなら、原則反射確率に上限（ただしoverride条件で解除）
    cap_applied = False
    if state.reflect_streak >= cfg.reflect_streak_cap_threshold and not features.allow_reflect_override:
        reflect_score = min(reflect_score, 0.15)
        cap_applied = True

    # LLM/DSPy提案の順位に軽いバイアス（任意）
    if llm_rank_bias:
        bonus = [0.45, 0.25, 0.10]
        for i, act in enumerate(llm_rank_bias[:3]):
            if act == MainAction.REFLECT:
                reflect_score += bonus[i]
            elif act == MainAction.QUESTION:
                question_score += bonus[i]
            elif act == MainAction.SUMMARY:
                summary_score += bonus[i]

    scores = {
        MainAction.REFLECT: max(0.01, reflect_score),
        MainAction.QUESTION: max(0.01, question_score),
        MainAction.SUMMARY: max(0.01, summary_score),
    }

    probs = _softmax(scores, temperature=cfg.temperature)

    # 反射確率のcap（必要なら）
    if cap_applied or (state.reflect_streak >= cfg.reflect_streak_cap_threshold and not features.allow_reflect_override):
        rp = probs.get(MainAction.REFLECT, 0.0)
        cap = cfg.reflect_prob_cap_after_streak
        if rp > cap:
            excess = rp - cap
            probs[MainAction.REFLECT] = cap
            q = probs.get(MainAction.QUESTION, 0.0)
            s = probs.get(MainAction.SUMMARY, 0.0)
            denom = (q + s) or 1.0
            probs[MainAction.QUESTION] = q + excess * (q / denom)
            probs[MainAction.SUMMARY] = s + excess * (s / denom)

    z = sum(probs.values()) or 1.0
    probs = {k: v / z for k, v in probs.items()}

    debug.update(
        {
            "scores": {k.value: float(v) for k, v in scores.items()},
            "probs": {k.value: float(v) for k, v in probs.items()},
            "reflect_streak": state.reflect_streak,
            "r_since_q": state.r_since_q,
            "turns_since_summary": state.turns_since_summary,
            "turns_since_affirm": state.turns_since_affirm,
            "phase": state.phase.value,
            "phase_action_multipliers": {"REFLECT": rm, "QUESTION": qm, "SUMMARY": sm},
            "cap_applied": cap_applied,
            "allow_reflect_override": features.allow_reflect_override,
            "llm_rank_bias": [a.value for a in llm_rank_bias] if llm_rank_bias else None,
        }
    )

    if not cfg.stochastic:
        action = max(probs.items(), key=lambda kv: kv[1])[0]
        debug["sampling"] = "argmax"
        return action, debug

    rng = random.Random(cfg.seed + state.turn_index)
    action = _sample_action(probs, rng)
    debug["sampling"] = "stochastic"
    return action, debug


def decide_affirm(features: PlannerFeatures, state: DialogueState) -> bool:
    """
    是認（affirmation）は主動作に“付加”します。
    連発しすぎると軽くなるので、近いターンでは抑えます。
    """
    if state.turns_since_affirm <= 1:
        return False

    if features.change_talk >= 0.35:
        return True
    if features.resistance >= 0.55 and features.novelty >= 0.25:
        return True
    if features.novelty >= 0.75:
        return True
    return False


def apply_action_to_state(
    *,
    state: DialogueState,
    features: PlannerFeatures,
    action: MainAction,
    add_affirm: bool,
) -> DialogueState:
    ns = dataclasses.replace(state)
    ns.turn_index += 1

    # info_mode遷移
    if action == MainAction.ASK_PERMISSION:
        ns.info_mode = InfoMode.WAITING_PERMISSION
    elif action == MainAction.PROVIDE_INFO:
        ns.info_mode = InfoMode.NONE
    elif state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is False:
        ns.info_mode = InfoMode.NONE
    elif state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is True:
        ns.info_mode = InfoMode.READY_TO_PROVIDE

    # リズムカウンタ
    if action in (MainAction.QUESTION, MainAction.ASK_PERMISSION, MainAction.PROVIDE_INFO):
        ns.r_since_q = 0
        ns.reflect_streak = 0
    elif action == MainAction.REFLECT:
        ns.r_since_q += 1
        ns.reflect_streak += 1
    elif action == MainAction.SUMMARY:
        ns.r_since_q += 1
        ns.reflect_streak = 0

    # 要約カウンタ
    if action == MainAction.SUMMARY:
        ns.turns_since_summary = 0
    else:
        ns.turns_since_summary += 1

    # 是認カウンタ
    if add_affirm:
        ns.turns_since_affirm = 0
    else:
        ns.turns_since_affirm += 1

    ns.last_actions = (ns.last_actions + [action])[-10:]
    return ns


# ----------------------------
# Phase classification（ヒューリスティック：LLM不使用のフォールバック）
# ----------------------------
_PHASE_HINTS: List[Tuple[Phase, List[str]]] = [
    (Phase.GREETING, ["こんにちは", "こんばんは", "はじめまして", "よろしく", "お世話"]),
    (Phase.PURPOSE_CONFIRMATION, ["今日は", "目的", "ゴール", "相談", "話したい", "何を", "どうなりたい"]),
    (Phase.CURRENT_STATUS_CHECK, ["最近", "現状", "状況", "困って", "悩んで", "つらい", "しんどい", "今"]),
    (Phase.FOCUSING_TARGET_BEHAVIOR, ["目標", "行動", "習慣", "やめたい", "始めたい", "頻度", "いつ", "標的", "焦点"]),
    (Phase.IMPORTANCE_PROMOTION, ["重要", "大事", "優先", "どのくらい", "0", "10", "点", "スケール"]),
    (Phase.CONFIDENCE_PROMOTION, ["自信", "できそう", "できる", "難しい", "不安", "可能", "無理"]),
    (Phase.NEXT_STEP_DECISION, ["次に", "一歩", "やってみる", "具体的に", "計画", "いつから", "まず"]),
    (Phase.CLOSING, ["ありがとうございました", "今日はここまで", "終わり", "次回", "また", "お大事に"]),
]


def classify_phase_heuristic(user_text: str, current_phase: Phase) -> Phase:
    scores: Dict[Phase, int] = {p: 0 for p, _ in _PHASE_HINTS}
    for phase, hints in _PHASE_HINTS:
        for h in hints:
            if h in user_text:
                scores[phase] += 1
    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] == 0:
        return current_phase
    return best[0]


def _history_to_dialogue(history: List[Tuple[str, str]], *, max_turns: int = 8) -> str:
    lines: List[str] = []
    for role, text in history[-max_turns:]:
        prefix = "クライアント" if role == "user" else "カウンセラー"
        lines.append(f"{prefix}: {text}")
    return "\n".join(lines)


def _parse_phase_from_text(text: str) -> Tuple[Optional[Phase], float]:
    t = (text or "").strip().strip("「」\"'`")
    if not t:
        return None, 0.0

    # 完全一致（最も高信頼）
    for p in Phase:
        if t == p.value:
            return p, 1.0

    # 文章のどこかにラベルが含まれる（中信頼）
    for p in Phase:
        if p.value in t:
            return p, 0.7

    # 省略・表記揺れの救済（低信頼）
    if "挨拶" in t:
        return Phase.GREETING, 0.4
    if "目的" in t:
        return Phase.PURPOSE_CONFIRMATION, 0.4
    if "現状" in t:
        return Phase.CURRENT_STATUS_CHECK, 0.4
    if "標的" in t or "行動" in t or "焦点" in t:
        return Phase.FOCUSING_TARGET_BEHAVIOR, 0.35
    if "重要" in t:
        return Phase.IMPORTANCE_PROMOTION, 0.35
    if "自信" in t:
        return Phase.CONFIDENCE_PROMOTION, 0.35
    if "次" in t or "一歩" in t:
        return Phase.NEXT_STEP_DECISION, 0.35
    if "クロージ" in t or "終" in t:
        return Phase.CLOSING, 0.35

    return None, 0.0


@dataclass
class LLMPhaseClassifier:
    """
    LLMで8フェーズ分類を行う簡易実装（DSPy化する前のベースライン）。
    - 出力は Phase の value（日本語ラベル）1つだけ、を強く要求します。
    """

    llm: LLMClient
    temperature: float = 0.0
    max_history_turns: int = 8

    def classify(
        self,
        *,
        history: List[Tuple[str, str]],
        state: DialogueState,
        user_text: str,
    ) -> Tuple[Phase, Dict[str, Any]]:
        dialogue = _history_to_dialogue(history, max_turns=self.max_history_turns)

        labels = " / ".join([p.value for p in Phase])
        system = (
            "あなたは動機づけ面接（MI）の対話を、次の8フェーズのいずれか1つに分類する分類器です。\n"
            "【出力制約】出力はラベル文字列“だけ”にしてください（説明・箇条書き・理由は書かない）。\n"
            f"【ラベル】{labels}\n"
            "\n"
            "【フェーズ定義（短縮）】\n"
            "- あいさつ: 開始の挨拶、関係づくり\n"
            "- 目的確認: 今日は何を扱うか、ゴールの合意\n"
            "- 現状確認: 現状・困りごと・感情・状況の理解\n"
            "- 標的行動焦点化: 変えたい行動を絞り込み、焦点を合わせる\n"
            "- 重要度促進: 重要さ（価値・理由）を言語化する\n"
            "- 自信度促進: できそう感、障壁・資源を扱う\n"
            "- 次の一歩決定: 具体的な小さな次の行動の合意\n"
            "- クロージング: 要点まとめ、次回への接続、終結\n"
            "\n"
            "【補助ルール】\n"
            "- 直近のやり取り全体から“今どの作業をしているか”で判断してください。\n"
            "- 不明確なら、現在フェーズを維持してください。\n"
            "- 重要度や自信が低そうなら、目的確認や現状確認など前段階へ戻ってもよい（柔軟に遷移）。\n"
        )

        user = (
            f"【現在フェーズ】{state.phase.value}\n"
            f"【ターン番号】{state.turn_index}\n"
            "【直近の対話】\n"
            f"{dialogue}\n"
            "\n"
            "出力："
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        raw = self.llm.generate(messages, temperature=self.temperature)
        pred, conf = _parse_phase_from_text(raw)

        debug: Dict[str, Any] = {
            "method": "llm",
            "raw_output": raw,
            "parsed_phase": pred.value if pred else None,
            "confidence": conf,
        }

        if pred is None:
            # ここでは current を返す（最終判断は外側で fallback してもよい）
            debug["fallback"] = "none_parsed -> keep_current"
            return state.phase, debug

        return pred, debug


@dataclass
class LLMActionRanker:
    """
    LLMで主動作（REFLECT/QUESTION/SUMMARY）の優先順位を提案する。
    ルールベースの plan_next_action に軽くバイアスを与える用途。
    """

    llm: LLMClient
    temperature: float = 0.2
    max_history_turns: int = 6

    def rank(
        self,
        *,
        history: List[Tuple[str, str]],
        state: DialogueState,
        features: PlannerFeatures,
    ) -> Tuple[List[MainAction], Dict[str, Any]]:
        dialogue = _history_to_dialogue(history, max_turns=self.max_history_turns)
        feature_json = json.dumps(dataclasses.asdict(features), ensure_ascii=False)
        system = (
            "あなたは動機づけ面接（MI）を行うカウンセラーの次の主動作を順位付けするアシスタントです。\n"
            "OARS（Open questions / Affirmations / Reflections / Summaries）のうち、今回重視したい順に3つを返してください。\n"
            "出力は JSON の配列か、{ \"rank\": [ ... ] } 形式で。各要素は REFLECT / SUMMARY / QUESTION のいずれか。"
        )
        user = (
            f"【現在フェーズ】{state.phase.value}\n"
            f"【特徴量（参考）】{feature_json}\n"
            f"【直近のやり取り】\n{dialogue}\n"
            "MIの原則（共感・抵抗への順応・自律尊重）を踏まえ、優先度の高い順に3つ並べてください。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = self.llm.generate(messages, temperature=self.temperature)
        parsed = _parse_json_from_text(raw)
        rank_list: List[Any]
        if isinstance(parsed, dict) and "rank" in parsed:
            rank_list = parsed.get("rank", [])
        elif isinstance(parsed, list):
            rank_list = parsed
        else:
            rank_list = []

        def _to_action(val: Any) -> Optional[MainAction]:
            if isinstance(val, MainAction):
                return val
            s = str(val).strip().upper()
            if "REFLECT" in s:
                return MainAction.REFLECT
            if "SUMMARY" in s:
                return MainAction.SUMMARY
            if "QUESTION" in s or "ASK" in s:
                return MainAction.QUESTION
            return None

        ordered: List[MainAction] = []
        seen = set()
        for v in rank_list:
            a = _to_action(v)
            if a and a not in seen:
                ordered.append(a)
                seen.add(a)

        used_default = False
        if not ordered:
            ordered = [MainAction.REFLECT, MainAction.SUMMARY, MainAction.QUESTION]
            used_default = True

        debug = {
            "raw_output": raw,
            "parsed": parsed,
            "used_default": used_default,
        }
        return ordered, debug


# ----------------------------
# Risk detection（安全レイヤ）
# ----------------------------
_RISK_SELF_HARM = [
    "死にたい", "消えたい", "自殺", "首を", "命を絶", "生きていたくない", "希死念慮", "リストカット", "オーバードーズ",
]
_RISK_HARM_OTHERS = ["殺す", "傷つけてやる", "復讐", "危害を加える"]
_RISK_SEVERE = ["幻聴", "幻覚", "妄想", "制御できない", "パニックで", "手がつけられない"]


@dataclass
class RuleBasedRiskDetector:
    """
    自傷他害リスクの単純なルール検出器（軽量フォールバック）。
    """

    def detect(
        self,
        *,
        user_text: str,
        history: List[Tuple[str, str]],
        state: DialogueState,
    ) -> RiskAssessment:
        text = user_text
        hits = sum(1 for kw in _RISK_SELF_HARM if kw in text)
        hits += sum(1 for kw in _RISK_HARM_OTHERS if kw in text)
        severe_hits = [kw for kw in _RISK_SEVERE if kw in text]
        level = RiskLevel.NONE
        if hits >= 2 or any(kw in text for kw in _RISK_HARM_OTHERS):
            level = RiskLevel.HIGH
        elif hits == 1 or severe_hits:
            level = RiskLevel.MILD
        reason = None
        if level != RiskLevel.NONE:
            terms = {kw for kw in _RISK_SELF_HARM + _RISK_HARM_OTHERS + _RISK_SEVERE if kw in text}
            reason = "ルール検出: " + ", ".join(sorted(terms)) if terms else "ルール検出"
        return RiskAssessment(level=level, reason=reason)


@dataclass
class LLMRiskDetector:
    """
    LLMで危機度を判定する検出器。none/mild/high の3段階で返す。
    """

    llm: LLMClient
    temperature: float = 0.0
    max_history_turns: int = 8
    rule_fallback: RuleBasedRiskDetector = field(default_factory=RuleBasedRiskDetector)

    def detect(
        self,
        *,
        user_text: str,
        history: List[Tuple[str, str]],
        state: DialogueState,
    ) -> RiskAssessment:
        dialogue = _history_to_dialogue(history, max_turns=self.max_history_turns)
        system = (
            "あなたは対話の安全リスクを判定する分類器です。\n"
            "レベル: none / mild / high のいずれかを JSON で返してください。\n"
            "- high: 自殺企図・具体的計画・他害の意思など差し迫った危険\n"
            "- mild: 希死念慮の示唆、体調の著しい悪化が疑われる\n"
            "- none: 上記に該当しない\n"
            '出力例: {"level":"high","reason":"死にたいと繰り返し発言"}'
        )
        user = (
            f"【現在フェーズ】{state.phase.value}\n"
            f"【直近の対話】\n{dialogue}\n"
            f"【今回のクライアント発話】{user_text}\n"
            "安全リスクを判定し、短い理由を付けてください。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = self.llm.generate(messages, temperature=self.temperature)
        parsed = _parse_json_from_text(raw)
        level_text: Optional[str] = None
        reason: Optional[str] = None
        if isinstance(parsed, dict):
            level_text = str(parsed.get("level") or parsed.get("risk") or "").lower()
            reason = parsed.get("reason") or parsed.get("note")

        mapping = {"none": RiskLevel.NONE, "low": RiskLevel.MILD, "mild": RiskLevel.MILD, "moderate": RiskLevel.MILD, "high": RiskLevel.HIGH}
        if level_text in mapping:
            level = mapping[level_text]
        else:
            fallback = self.rule_fallback.detect(user_text=user_text, history=history, state=state)
            return RiskAssessment(level=fallback.level, reason=fallback.reason, raw_output=raw)

        return RiskAssessment(level=level, reason=reason, raw_output=raw)


@dataclass
class LLMMIEvaluator:
    """
    応答がMIの原則に沿っているかを簡易採点する LLM 評価器。
    """

    llm: LLMClient
    temperature: float = 0.0
    max_history_turns: int = 6

    def evaluate(
        self,
        *,
        action: MainAction,
        assistant_text: str,
        history: List[Tuple[str, str]],
        state: DialogueState,
    ) -> OutputEvaluation:
        dialogue = _history_to_dialogue(history, max_turns=self.max_history_turns)
        system = (
            "あなたは動機づけ面接（MI）の対話応答を採点するレビュアーです。\n"
            "共感的・非指示的・自律尊重・抵抗への順応が守られているかを 0〜10 で評価してください。\n"
            'JSONのみを出力してください。例: {"score":8.5,"feedback":"丁寧な反射だが質問が誘導的"}\n'
            "- スコアが低い場合は短く改善ポイントを feedback に入れてください。\n"
        )
        user = (
            f"【現在フェーズ】{state.phase.value}\n"
            f"【主動作】{action.value}\n"
            f"【直近の対話】\n{dialogue}\n"
            f"【今回のアシスタント発話】{assistant_text}\n"
            "MI準拠性を採点し、必要なら改善のヒントを短く書いてください。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = self.llm.generate(messages, temperature=self.temperature)
        parsed = _parse_json_from_text(raw)
        score = 10.0
        feedback = None
        rewrite = None
        if isinstance(parsed, dict):
            try:
                score = float(parsed.get("score", score))
            except Exception:
                pass
            feedback_val = parsed.get("feedback") or parsed.get("comment")
            rewrite_val = parsed.get("rewrite")
            feedback = str(feedback_val) if feedback_val is not None else None
            rewrite = str(rewrite_val) if rewrite_val is not None else None

        score = max(0.0, min(10.0, score))
        return OutputEvaluation(score=score, feedback=feedback, raw_output=raw, rewrite=rewrite)


# ----------------------------
# Prompt building（ガイダンス付き生成）
# ----------------------------
def select_reflection_style(features: PlannerFeatures) -> ReflectionStyle:
    """
    簡易ヒューリスティックで反射スタイルを選択。
    - 抵抗が強い: 両面反射でバランスを取る
    - チェンジトークが強い: 複雑反射で価値や強みを織り込む
    - 短い/新情報が少ない: 簡単反射で軽く確認
    """
    if features.resistance >= 0.6:
        return ReflectionStyle.DOUBLE_SIDED
    if features.change_talk >= 0.55:
        return ReflectionStyle.COMPLEX
    if features.is_short_reply or features.novelty < 0.25:
        return ReflectionStyle.SIMPLE
    return ReflectionStyle.COMPLEX


def build_prompt(
    *,
    history: List[Tuple[str, str]],
    state: DialogueState,
    action: MainAction,
    add_affirm: bool,
    reflection_style: Optional[ReflectionStyle] = None,
    risk_assessment: Optional[RiskAssessment] = None,
) -> List[Dict[str, str]]:
    """
    history: [("user"|"assistant", text), ...]
    返り値は chat-completions 互換の messages 形式。
    """

    slot_hint_lines = [
        f"- 目標/目的: {state.goal_description or '未設定'}",
        f"- 標的行動: {state.target_behavior or '未設定'}",
        f"- 価値観/大事なこと: {', '.join(state.client_values) if state.client_values else '未設定'}",
        f"- 次の一歩案: {state.next_step or '未設定'}",
    ]
    slot_hint = "スロット（参照用）:\n" + "\n".join(slot_hint_lines)

    risk_note = ""
    if risk_assessment:
        if risk_assessment.level == RiskLevel.HIGH:
            risk_note = "【安全モード】高リスクが検知されています。通常の進行を中断し、安全確保と専門窓口案内を最優先してください。\n"
        elif risk_assessment.level == RiskLevel.MILD:
            risk_note = "【注意】安全面での懸念が少しあります。慎重に、安心を優先してください。\n"

    reflection_style_line = (
        f"今回の反射スタイル: {reflection_style.value}" if reflection_style else "今回の反射スタイル: 指定なし"
    )

    # OARS = Open questions（オープン質問）, Affirmations（是認）, Reflections（聞き返し）, Summaries（要約）
    system = (
        "あなたは動機づけ面接（Motivational Interviewing: MI）のスタイルで支援する対話エージェントです。\n"
        "口調は丁寧で、相手を尊重し、決めつけず、対立せず、自己決定を支えます。\n"
        "安全配慮：自傷他害や差し迫った危険が疑われる場合は、通常の進行を中断し、安全確保と専門窓口の利用を勧めてください。\n"
        "\n"
        f"現在のフェーズ: {state.phase.value}\n"
        f"今回の主動作: {action.value}\n"
        f"是認を入れる: {'はい' if add_affirm else 'いいえ'}\n"
        f"{reflection_style_line}\n"
        f"{slot_hint}\n"
        f"{risk_note}"
        "\n"
        "共通ルール:\n"
        "- 直近だけでなく、これまでのやり取りも踏まえてよい。\n"
        "- 説教・押しつけ・断定を避ける。\n"
        "- 専門用語は避けるか、必要なら短く説明する。\n"
    )

    phase_guidance = {
        Phase.GREETING: "目的：安心できる雰囲気で挨拶し、話しやすい土台を作る。",
        Phase.PURPOSE_CONFIRMATION: "目的：今日は何を扱うか（目的・ゴール）を一緒に確認する。",
        Phase.CURRENT_STATUS_CHECK: "目的：現状・困りごと・気持ち・状況を丁寧に理解する。",
        Phase.FOCUSING_TARGET_BEHAVIOR: "目的：標的となる行動を具体化し、焦点を合わせる。",
        Phase.IMPORTANCE_PROMOTION: "目的：変える重要性（理由・価値）を言語化し、強める。",
        Phase.CONFIDENCE_PROMOTION: "目的：できそう感（自信）を高め、障壁と資源を整理する。",
        Phase.NEXT_STEP_DECISION: "目的：次の一歩を小さく具体化し、合意する。",
        Phase.CLOSING: "目的：要点をまとめ、次回への接続や労いを添えて終える。",
    }[state.phase]

    if risk_assessment and risk_assessment.level == RiskLevel.HIGH:
        action_rule = (
            "出力要件（安全確保モード）：\n"
            "- まず安全確保と専門窓口（緊急ダイヤル、医療機関、産業保健スタッフ等）への連絡を丁寧に案内する。\n"
            "- 危機対応に専念し、通常のMI進行は一旦止める。\n"
            "- 責めずに安心感を伝えつつ、話せるかどうかを1つだけ短く尋ねる。\n"
        )
    elif action == MainAction.REFLECT:
        action_rule = (
            "出力要件（聞き返し/言い換え）：\n"
            "- 相手の発言内容・感情・価値を、丁寧に言い換えて返す。\n"
            "- 新情報を足しすぎない（推測するなら「〜かもしれません」など控えめに）。\n"
            "- 質問しない（文末に「？」を付けない）。\n"
            "- 長さは2〜4文程度。\n"
        )
        style_hint = {
            ReflectionStyle.SIMPLE: "- スタイル: 簡単反射（事実中心で短く、確認を兼ねて）。\n",
            ReflectionStyle.COMPLEX: "- スタイル: 複雑反射（感情や価値観を織り込み、意味づけを深める）。\n",
            ReflectionStyle.DOUBLE_SIDED: "- スタイル: 両面反射（やりたい/やりたくない双方を並べてバランスを取る）。\n",
        }.get(reflection_style)
        if style_hint:
            action_rule += style_hint
    elif action == MainAction.QUESTION:
        action_rule = (
            "出力要件（質問）：\n"
            "- 原則1つの質問。\n"
            "- はい/いいえで終わりにくい聞き方（オープン質問）を優先。\n"
            "- 説教や誘導質問を避ける。\n"
            "- 必要なら、短い一文の受け止め（反射）を前置きしてよい。\n"
        )
    elif action == MainAction.SUMMARY:
        action_rule = (
            "出力要件（要約）：\n"
            "- これまでの要点を2〜5文で整理。\n"
            "- (1) 事実、(2) 感情、(3) 価値/大事にしていること、(4) 迷い/両価性 の順に必要なものを拾う。\n"
            "- 最後に、短い確認の問いを1つ付けてもよい（例：『ここまでの理解で合っていますか。』）。\n"
        )
    elif action == MainAction.ASK_PERMISSION:
        action_rule = (
            "出力要件（許可取り）：\n"
            "- 情報共有や提案をする前に、許可を取る。\n"
            "- 1〜2文で簡潔に。最後は質問で終える。\n"
        )
    elif action == MainAction.PROVIDE_INFO:
        action_rule = (
            "出力要件（情報共有）：\n"
            "- 中立的に、選択肢として短く情報を共有する（箇条書きは可）。\n"
            "- 最後に『どう感じますか』『どれならできそうですか』など反応を聞く質問を1つ。\n"
            "- 押しつけない。\n"
        )
    else:
        action_rule = "出力要件：不明"

    affirm_rule = (
        "\n是認（affirmation）の入れ方:\n"
        "- 努力・工夫・価値観・強み・小さな前進を具体的に認める。\n"
        "- お世辞や過度な称賛にしない。\n"
        if add_affirm
        else ""
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system + "\n" + phase_guidance + "\n\n" + action_rule + affirm_rule}
    ]
    for role, text in history[-20:]:
        messages.append({"role": role, "content": text})
    return messages


# ----------------------------
# Output validation（最低限）
# ----------------------------
def validate_output(action: MainAction, text: str) -> Tuple[bool, str]:
    t = text.strip()
    if not t:
        return False, "empty"

    if action == MainAction.REFLECT:
        if "？" in t or "?" in t:
            return False, "reflect_contains_question_mark"
    if action == MainAction.ASK_PERMISSION:
        if ("？" not in t) and ("?" not in t) and ("でしょうか" not in t) and ("ですか" not in t):
            return False, "ask_permission_not_question"
    if action == MainAction.QUESTION:
        if ("？" not in t) and ("?" not in t) and ("でしょうか" not in t) and ("ですか" not in t):
            return False, "question_missing"
        qcount = t.count("？") + t.count("?")
        if qcount >= 2:
            return False, "too_many_questions"
    return True, "ok"


# ----------------------------
# Orchestrator（最小実装）
# ----------------------------
@dataclass
class MIRhythmBot:
    llm: LLMClient
    cfg: PlannerConfig = field(default_factory=PlannerConfig)
    state: DialogueState = field(default_factory=DialogueState)
    history: List[Tuple[str, str]] = field(default_factory=list)

    # 追加：フェーズ判定とアクション順位の差し込み口
    phase_classifier: Optional[PhaseClassifier] = None
    action_ranker: Optional[ActionRanker] = None
    feature_extractor: FeatureExtractor = field(default_factory=RuleBasedFeatureExtractor)
    risk_detector: Optional[RiskDetector] = field(default_factory=RuleBasedRiskDetector)
    output_evaluator: Optional[OutputEvaluator] = None

    # LLMフェーズ判定の“低信頼”時フォールバック閾値（phase_classifier がconfidenceを返す場合のみ）
    phase_confidence_threshold: float = 0.55
    # MI準拠スコアが低いときに自動で再生成する閾値（Noneならロギングのみ）
    evaluation_rewrite_threshold: Optional[float] = None

    def reset(self) -> None:
        """
        セッションを切り替えるとき用のリセット。
        - DialogueState を初期化
        - 発話履歴をクリア
        """
        self.state = DialogueState()
        self.history.clear()

    def step(self, user_text: str) -> Tuple[str, Decision]:
        # 1) 履歴更新（user）
        self.history.append(("user", user_text))

        # 1.5) 安全確認（高リスクならフェーズを強制遷移）
        risk_assessment: Optional[RiskAssessment] = None
        if self.risk_detector is not None:
            try:
                risk_assessment = self.risk_detector.detect(
                    user_text=user_text,
                    history=self.history,
                    state=self.state,
                )
            except Exception as e:
                risk_assessment = RiskAssessment(level=self.state.risk_level, reason=f"risk_detector_error:{e}")

        if risk_assessment:
            self.state.risk_level = risk_assessment.level
            self.state.last_risk_reason = risk_assessment.reason
            if risk_assessment.level == RiskLevel.HIGH:
                # 緊急時は情報共有モードを解除して安全案内を優先
                self.state.info_mode = InfoMode.NONE

        # 2) フェーズ更新（LLM/DSPyを優先。なければヒューリスティック）
        phase_debug: Dict[str, Any] = {"method": "heuristic"}
        if risk_assessment and risk_assessment.level == RiskLevel.HIGH:
            self.state.phase = Phase.CLOSING
            phase_debug = {
                "method": "risk_override",
                "risk_level": risk_assessment.level.value,
                "risk_reason": risk_assessment.reason,
            }
        elif self.phase_classifier is not None:
            try:
                ph, phase_debug = self.phase_classifier.classify(
                    history=self.history,
                    state=self.state,
                    user_text=user_text,
                )
                conf = float(phase_debug.get("confidence", 1.0))
                if conf < self.phase_confidence_threshold:
                    fallback = classify_phase_heuristic(user_text, self.state.phase)
                    phase_debug["fallback_phase"] = fallback.value
                    phase_debug["fallback_reason"] = f"confidence<{self.phase_confidence_threshold}"
                    ph = fallback
                self.state.phase = ph
            except Exception as e:
                fallback = classify_phase_heuristic(user_text, self.state.phase)
                phase_debug = {
                    "method": "phase_classifier_error_fallback",
                    "error": str(e),
                    "fallback_phase": fallback.value,
                }
                self.state.phase = fallback
        else:
            self.state.phase = classify_phase_heuristic(user_text, self.state.phase)

        # 3) 特徴量
        feature_debug: Dict[str, Any] = {}
        if self.feature_extractor is not None:
            try:
                features, feature_debug = self.feature_extractor.extract(
                    user_text=user_text,
                    state=self.state,
                    cfg=self.cfg,
                    history=self.history,
                )
            except Exception as e:
                features = extract_features_rule(user_text, self.state, self.cfg)
                feature_debug = {"method": "feature_extractor_error_fallback", "error": str(e)}
        else:
            features = extract_features_rule(user_text, self.state, self.cfg)
            feature_debug = {"method": "no_feature_extractor_fallback"}

        # permissionを明確に拒否なら解除
        if self.state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is False:
            self.state.info_mode = InfoMode.NONE

        # 4) 行動選択（LLMランカーを優先し、なければヒューリスティック）
        crisis_override = risk_assessment and risk_assessment.level == RiskLevel.HIGH
        llm_rank_bias: Optional[List[MainAction]] = None
        llm_action_choice: Optional[MainAction] = None
        ranker_debug: Optional[Dict[str, Any]] = None
        if (not crisis_override) and self.action_ranker is not None:
            try:
                llm_rank_bias, ranker_debug = self.action_ranker.rank(
                    history=self.history,
                    state=self.state,
                    features=features,
                )
                # 念のためユニーク化＆不正値除去
                cleaned: List[MainAction] = []
                seen = set()
                for a in llm_rank_bias:
                    if not isinstance(a, MainAction):
                        continue
                    if a in seen:
                        continue
                    seen.add(a)
                    cleaned.append(a)
                llm_rank_bias = cleaned
                if cleaned:
                    llm_action_choice = cleaned[0]
            except Exception as e:
                llm_rank_bias = None
                ranker_debug = {"error": str(e)}

        if crisis_override:
            action = MainAction.PROVIDE_INFO
            debug = {"sampling": "crisis_override", "risk_level": risk_assessment.level.value}
        else:
            if llm_action_choice is not None:
                action = llm_action_choice
                debug = {
                    "sampling": "llm_action_ranker",
                    "ranker_choice": llm_action_choice.value,
                    "llm_rank_bias": [a.value for a in llm_rank_bias] if llm_rank_bias else [],
                }
            else:
                action, debug = plan_next_action(
                    state=self.state,
                    features=features,
                    cfg=self.cfg,
                    llm_rank_bias=llm_rank_bias,
                )

        # permissionが得られたなら情報共有へ
        if self.state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is True:
            self.state.info_mode = InfoMode.READY_TO_PROVIDE
            action = MainAction.PROVIDE_INFO

        # 5) 是認の付加（危機時は抑制）
        add_affirm = False if crisis_override else decide_affirm(features, self.state)

        # 6) 次状態（このターンの想定更新）
        reflection_style = select_reflection_style(features) if action == MainAction.REFLECT else None
        next_state = apply_action_to_state(state=self.state, features=features, action=action, add_affirm=add_affirm)

        decision = Decision(
            phase=self.state.phase,
            main_action=action,
            add_affirm=add_affirm,
            next_state=next_state,
            debug={
                "features": dataclasses.asdict(features),
                "feature_debug": feature_debug,
                "phase_debug": phase_debug,
                "ranker_debug": ranker_debug,
                "risk_assessment": (
                    {
                        "level": risk_assessment.level.value,
                        "reason": risk_assessment.reason,
                        "raw_output": risk_assessment.raw_output,
                    }
                    if risk_assessment
                    else None
                ),
                **debug,
            },
        )

        # 7) 生成
        messages = build_prompt(
            history=self.history,
            state=self.state,
            action=action,
            add_affirm=add_affirm,
            reflection_style=reflection_style,
            risk_assessment=risk_assessment,
        )
        assistant_text = self.llm.generate(messages, temperature=0.2)

        # 8) 検査→必要なら一回だけやり直し
        ok, reason = validate_output(action, assistant_text)
        if not ok:
            repair = (
                f"直前の出力が要件を満たしていません（理由: {reason}）。\n"
                "要件を厳密に守って、同じ主動作で書き直してください。"
            )
            messages.append({"role": "system", "content": repair})
            assistant_text = self.llm.generate(messages, temperature=0.2)

        # 8.5) MI準拠セルフチェック（ログ優先、閾値設定時のみ再生成）
        evaluation: Optional[OutputEvaluation] = None
        if self.output_evaluator is not None:
            try:
                evaluation = self.output_evaluator.evaluate(
                    action=action,
                    assistant_text=assistant_text,
                    history=self.history,
                    state=self.state,
                )
            except Exception as e:
                evaluation = OutputEvaluation(score=0.0, feedback=f"evaluation_error:{e}", raw_output=None)

        if evaluation and self.evaluation_rewrite_threshold is not None:
            if evaluation.score < self.evaluation_rewrite_threshold:
                rewrite_hint = evaluation.rewrite or evaluation.feedback or "MIの原則により丁寧で非指示的な表現に直してください。"
                repair = (
                    f"直前の応答はMI準拠スコアが低めでした（{evaluation.score}）。\n"
                    f"指摘: {rewrite_hint}\n"
                    "同じ主動作とフェーズを保ちつつ、改善版を書き直してください。"
                )
                messages.append({"role": "system", "content": repair})
                assistant_text = self.llm.generate(messages, temperature=0.15)

        # 9) 履歴更新（assistant）＋state更新
        self.history.append(("assistant", assistant_text))
        self.state = next_state
        self.state.last_user_text = user_text

        if evaluation:
            decision.debug["evaluation"] = {
                "score": evaluation.score,
                "feedback": evaluation.feedback,
                "raw_output": evaluation.raw_output,
            }

        return assistant_text, decision


# ----------------------------
# Demo用のダミーLLM（必ず差し替えてください）
# ----------------------------
@dataclass
class DummyLLM:
    def generate(self, messages: List[Dict[str, str]], *, temperature: float = 0.2) -> str:
        sys = messages[0]["content"]
        if "今回の主動作: REFLECT" in sys:
            return "なるほど、いまのお話だと、最近の状況について整理しながら考えておられるのですね。"
        if "今回の主動作: QUESTION" in sys:
            return "今の状況で、いちばん変えてみたいことは何でしょうか？"
        if "今回の主動作: SUMMARY" in sys:
            return "ここまでのお話では、現状の困りごとがありつつも、変えたい気持ちも少し出てきているようです。合っていますか？"
        if "今回の主動作: ASK_PERMISSION" in sys:
            return "いくつか選択肢の情報を共有してもよろしいでしょうか？"
        if "今回の主動作: PROVIDE_INFO" in sys:
            return "例えば、(1) 記録をつける、(2) 目標を小さくする、(3) 周りに協力を頼む、のようなやり方があります。どれが一番やれそうですか？"
        return "承知しました。"


def _run_demo() -> None:
    # 実運用想定：Responses API + gpt-5-mini を使用
    llm = OpenAIResponsesLLM(
        model="gpt-5-mini",
        reasoning_effort="medium",
        store=False,
    )
    bot = MIRhythmBot(
        llm=llm,
        cfg=PlannerConfig(stochastic=False, seed=1),
        phase_classifier=LLMPhaseClassifier(llm=llm),
    )
    inputs = [
        "最近、夜更かしが増えてしまって困っています。",
        "うーん、でも仕事が忙しくて…",
        "そうですね。",
        "できれば早く寝たいです。",
        "どうしたらいいですか？",
        "はい、教えてください。",
        "なるほど。",
    ]
    for u in inputs:
        a, d = bot.step(u)
        print("U:", u)
        print("A:", a)
        print(
            "DBG phase:", d.phase.value,
            "action:", d.main_action.value,
            "reflect_streak:", d.next_state.reflect_streak,
            "r_since_q:", d.next_state.r_since_q,
        )
        print("----")


if __name__ == "__main__":
    _run_demo()
