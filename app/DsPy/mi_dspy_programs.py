from __future__ import annotations

"""
DSPy 用のプログラム群（A/B/Cで使い回し）

- A: 発話生成（MIReplyProgram / MIReplyRepairProgram）
- B: フェーズ判定（MIPhaseProgram）
     チェンジトーク・抵抗推定（MIChangeTalkResistanceProgram）
- C: 行動ランキング（MIActionRankerProgram）
     セッション実行（MISessionDriverProgram）
"""

from dataclasses import asdict
from typing import List, Literal, Optional, Tuple

import dspy

from mi_counselor_agent import (
    Phase,
    MainAction,
    DialogueState,
    PlannerConfig,
    PlannerFeatures,
    Decision,
    InfoMode,
    apply_action_to_state,
    classify_phase_heuristic,
    decide_affirm,
    extract_features,
    compute_allowed_actions,
    validate_output,
    coerce_main_action,
)

# ----------------------------
# 型（DSPyの出力を安定させるため Literal を使う）
# ----------------------------
PhaseLabel = Literal[
    "問題特定",
    "標的行動設定",
    "チェンジトーク促進",
    "タスク特定",
    "ホームワーク設定",
]

ActionLabel = Literal[
    "REFLECT",
    "QUESTION",
    "SUMMARY",
    "ASK_PERMISSION_TO_SHARE_INFO",
    "PROVIDE_INFO",
]


# ----------------------------
# A: 発話生成
# ----------------------------
class MIReplySignature(dspy.Signature):
    """
    あなたは動機づけ面接（MI: Motivational Interviewing）スタイルのカウンセラーです。
    入力として「対話履歴（dialogue）」と「フェーズ（phase）」と「主動作（main_action）」が与えられます。
    主動作に沿った“次の一言”を日本語で生成してください。

    全体方針（MI）:
    - 共感・受容・自律尊重（押しつけない）
    - 反射（聞き返し）を基本に、必要時に質問・要約・許可取り・情報提供へ
    - 専門用語は避け、丁寧語で

    主動作ごとの制約:
    - REFLECT: 質問記号「?」「？」を入れない（断定しすぎず言い換える）
    - QUESTION: 質問は1つまで。文末は疑問形（？/ですか/でしょうか）
    - SUMMARY: 要点を短くまとめる。必要なら最後に確認の問いを1つまで
    - ASK_PERMISSION_TO_SHARE_INFO: 情報共有の前に許可を取る（短く、最後は疑問形）
    - PROVIDE_INFO: 中立に短く情報提示し、最後に反応を尋ねる質問を1つ
    """

    dialogue: str = dspy.InputField(
        desc="直近の対話。例: Client: ... / Counselor: ...。最後の行は Client の最新発話。"
    )
    phase: PhaseLabel = dspy.InputField(desc="現在のフェーズ")
    main_action: ActionLabel = dspy.InputField(desc="今回の主動作")
    add_affirm: bool = dspy.InputField(desc="Trueなら是認（努力/工夫/強みの具体的認め）を一言添える")
    reply: str = dspy.OutputField(desc="次のカウンセラー発話（日本語、丁寧語）")


class MIReplyProgram(dspy.Module):
    def __init__(self, temperature: float = 0.2):
        super().__init__()
        # Predict は最小の“生成”モジュール
        self.predict = dspy.Predict(MIReplySignature, temperature=temperature)

    def forward(self, dialogue: str, phase: PhaseLabel, main_action: ActionLabel, add_affirm: bool):
        return self.predict(dialogue=dialogue, phase=phase, main_action=main_action, add_affirm=add_affirm)


class MIReplyRepairSignature(dspy.Signature):
    """
    直前のカウンセラー発話が制約に違反しました。
    同じ意図を保ったまま、違反を解消するように“書き直し”てください。
    """

    dialogue: str = dspy.InputField(desc="対話履歴（最後はClient発話）")
    phase: PhaseLabel = dspy.InputField(desc="現在フェーズ")
    main_action: ActionLabel = dspy.InputField(desc="主動作")
    add_affirm: bool = dspy.InputField(desc="是認を入れるか")
    bad_reply: str = dspy.InputField(desc="違反した発話")
    violation_reason: str = dspy.InputField(desc="違反理由（短いコード名）")
    reply: str = dspy.OutputField(desc="修正版のカウンセラー発話（制約を満たす）")


class MIReplyRepairProgram(dspy.Module):
    def __init__(self, temperature: float = 0.2):
        super().__init__()
        self.predict = dspy.Predict(MIReplyRepairSignature, temperature=temperature)

    def forward(
        self,
        dialogue: str,
        phase: PhaseLabel,
        main_action: ActionLabel,
        add_affirm: bool,
        bad_reply: str,
        violation_reason: str,
    ):
        return self.predict(
            dialogue=dialogue,
            phase=phase,
            main_action=main_action,
            add_affirm=add_affirm,
            bad_reply=bad_reply,
            violation_reason=violation_reason,
        )


# ----------------------------
# B: フェーズ判定 / チェンジトーク・抵抗推定
# ----------------------------
class MIPhaseSignature(dspy.Signature):
    """
    入力の発話（user_text）と現在フェーズ（current_phase）をもとに、
    次に優先すべきフェーズを1つだけ返してください。
    """

    user_text: str = dspy.InputField(desc="クライアント発話（最新）")
    current_phase: PhaseLabel = dspy.InputField(desc="現在フェーズ")
    phase: PhaseLabel = dspy.OutputField(desc="推定フェーズ（いずれか1つ）")


class MIPhaseProgram(dspy.Module):
    def __init__(self, temperature: float = 0.0):
        super().__init__()
        self.predict = dspy.Predict(MIPhaseSignature, temperature=temperature)

    def forward(self, user_text: str, current_phase: PhaseLabel):
        return self.predict(user_text=user_text, current_phase=current_phase)


class MIChangeTalkResistanceSignature(dspy.Signature):
    """
    クライアント発話から、以下を 0.0〜1.0 で推定してください。

    - change_talk: 変化に向かう言動（理由/必要/意思/能力/コミット等）が強いほど高い
    - resistance: 反発/言い訳/拒否/話題回避/最小化が強いほど高い

    数値は0〜1に収めてください。
    """

    user_text: str = dspy.InputField(desc="クライアント発話（最新）")
    last_user_text: str = dspy.InputField(desc="直前のクライアント発話（なければ空文字）")
    change_talk: float = dspy.OutputField(desc="0.0〜1.0")
    resistance: float = dspy.OutputField(desc="0.0〜1.0")


class MIChangeTalkResistanceProgram(dspy.Module):
    def __init__(self, temperature: float = 0.0):
        super().__init__()
        self.predict = dspy.Predict(MIChangeTalkResistanceSignature, temperature=temperature)

    def forward(self, user_text: str, last_user_text: str):
        return self.predict(user_text=user_text, last_user_text=last_user_text)


# ----------------------------
# C: 行動ランキング
# ----------------------------
class MIActionRankSignature(dspy.Signature):
    """
    状態・特徴量を見て、次に優先したい主動作を上位3つ返してください（順番が重要）。

    返す値は REFLECT/QUESTION/SUMMARY/ASK_PERMISSION_TO_SHARE_INFO/PROVIDE_INFO のいずれか。
    """

    user_text: str = dspy.InputField(desc="クライアント発話（最新）")
    phase: PhaseLabel = dspy.InputField(desc="現在フェーズ")
    info_mode: Literal["NONE", "WAITING_PERMISSION", "READY_TO_PROVIDE"] = dspy.InputField(desc="情報共有状態")

    reflect_streak: int = dspy.InputField(desc="連続REFLECT回数")
    r_since_q: int = dspy.InputField(desc="最後の質問からの非質問ターン数")
    turns_since_summary: int = dspy.InputField(desc="最後の要約からのターン数")

    change_talk: float = dspy.InputField(desc="0〜1")
    resistance: float = dspy.InputField(desc="0〜1")
    novelty: float = dspy.InputField(desc="0〜1")

    user_is_question: bool = dspy.InputField(desc="ユーザ発話が質問っぽいか")
    user_requests_info: bool = dspy.InputField(desc="情報提供を求めているか")

    rank1: ActionLabel = dspy.OutputField(desc="最優先アクション")
    rank2: ActionLabel = dspy.OutputField(desc="次点アクション")
    rank3: ActionLabel = dspy.OutputField(desc="第3候補アクション")


class MIActionRankerProgram(dspy.Module):
    def __init__(self, temperature: float = 0.0):
        super().__init__()
        self.predict = dspy.Predict(MIActionRankSignature, temperature=temperature)

    def forward(
        self,
        user_text: str,
        phase: PhaseLabel,
        info_mode: str,
        reflect_streak: int,
        r_since_q: int,
        turns_since_summary: int,
        change_talk: float,
        resistance: float,
        novelty: float,
        user_is_question: bool,
        user_requests_info: bool,
    ):
        return self.predict(
            user_text=user_text,
            phase=phase,
            info_mode=info_mode,
            reflect_streak=reflect_streak,
            r_since_q=r_since_q,
            turns_since_summary=turns_since_summary,
            change_talk=change_talk,
            resistance=resistance,
            novelty=novelty,
            user_is_question=user_is_question,
            user_requests_info=user_requests_info,
        )


# ----------------------------
# C用: セッションを「固定クライアント台本」で回すドライバ
#   - DSPy最適化では forward() が呼ばれる
#   - 実運用では step_once() を使う
# ----------------------------
def _history_to_dialogue(history: List[Tuple[str, str]], max_turns: int = 20) -> str:
    lines: List[str] = []
    for role, text in history[-max_turns:]:
        prefix = "Client" if role == "user" else "Counselor"
        lines.append(f"{prefix}: {text}")
    return "\n".join(lines)


def _to_phase_label(p: Phase) -> PhaseLabel:
    # Phase Enum の value をそのまま PhaseLabel として使う
    return p.value  # type: ignore[return-value]


def _safe_clip01(x: float) -> float:
    if x != x:  # NaN
        return 0.0
    return max(0.0, min(1.0, float(x)))


def _unique_ranked_actions(rank1: str, rank2: str, rank3: str) -> List[MainAction]:
    seen = set()
    out: List[MainAction] = []
    for r in [rank1, rank2, rank3]:
        if r in seen:
            continue
        seen.add(r)
        parsed = coerce_main_action(r)
        if parsed is None:
            continue
        out.append(parsed)
    return out


class MISessionDriverProgram(dspy.Module):
    """
    セッション（複数ターン）を回すDSPyプログラム。

    - A/B/C をまとめて最適化したいとき：この Program を compile する
    - 実運用（1ターンずつ）では step_once を呼ぶ
    """

    def __init__(
        self,
        cfg: Optional[PlannerConfig] = None,
        use_phase_program: bool = False,
        use_ctr_program: bool = False,
        use_action_ranker: bool = False,
    ):
        super().__init__()
        self.cfg = cfg or PlannerConfig(stochastic=False)  # セッション評価は基本 deterministic 推奨

        self.reply = MIReplyProgram(temperature=0.2)
        self.repair = MIReplyRepairProgram(temperature=0.2)

        self.phase_program = MIPhaseProgram(temperature=0.0) if use_phase_program else None
        self.ctr_program = MIChangeTalkResistanceProgram(temperature=0.0) if use_ctr_program else None
        self.action_ranker = MIActionRankerProgram(temperature=0.0) if use_action_ranker else None

    def step_once(
        self,
        *,
        state: DialogueState,
        history: List[Tuple[str, str]],
        user_text: str,
    ) -> Tuple[str, Decision, DialogueState, PlannerFeatures]:
        # 1) 履歴更新（user）
        history.append(("user", user_text))

        # 2) フェーズ更新（Bを使うならDSPy、それ以外はヒューリスティック）
        if self.phase_program is None:
            phase = classify_phase_heuristic(user_text, state.phase)
        else:
            pred = self.phase_program(user_text=user_text, current_phase=_to_phase_label(state.phase))
            # 変な値が来たら fallback
            try:
                phase = Phase([p for p in Phase if p.value == pred.phase][0])  # type: ignore[index]
            except Exception:
                phase = classify_phase_heuristic(user_text, state.phase)

        state.phase = phase

        # 3) 特徴量（基本は既存heuristicを使い、Bがあれば change_talk/resistance を差し替え）
        features = extract_features(user_text, state, self.cfg)

        if self.ctr_program is not None:
            pred2 = self.ctr_program(user_text=user_text, last_user_text=state.last_user_text or "")
            ct = _safe_clip01(float(getattr(pred2, "change_talk", 0.0)))
            rs = _safe_clip01(float(getattr(pred2, "resistance", 0.0)))

            # allow_reflect_override を差し替え後の値で再計算
            allow = (
                ct >= self.cfg.allow_override_change_talk
                or rs >= self.cfg.allow_override_resistance
                or features.novelty >= self.cfg.allow_override_novelty
            )
            features = PlannerFeatures(
                user_is_question=features.user_is_question,
                user_requests_info=features.user_requests_info,
                has_permission=features.has_permission,
                resistance=rs,
                change_talk=ct,
                novelty=features.novelty,
                topic_shift=features.topic_shift,
                need_summary=features.need_summary,
                allow_reflect_override=allow,
            )

        # permissionを明確に拒否なら解除
        if state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is False:
            state.info_mode = InfoMode.NONE

        # 4) 行動選択（ranker出力を action mask で強制採用）
        ranker_actions: List[MainAction] = []
        if self.action_ranker is not None:
            pr = self.action_ranker(
                user_text=user_text,
                phase=_to_phase_label(state.phase),
                info_mode=state.info_mode.value,
                reflect_streak=state.reflect_streak,
                r_since_q=state.r_since_q,
                turns_since_summary=state.turns_since_summary,
                change_talk=features.change_talk,
                resistance=features.resistance,
                novelty=features.novelty,
                user_is_question=features.user_is_question,
                user_requests_info=features.user_requests_info,
            )
            ranker_actions = _unique_ranked_actions(pr.rank1, pr.rank2, pr.rank3)

        action_mask = compute_allowed_actions(
            state=state,
            features=features,
            cfg=self.cfg,
        )
        allowed_actions = action_mask.get("allowed_actions") or [MainAction.REFLECT_COMPLEX]
        allowed_set = set(allowed_actions)
        fallback_action = allowed_actions[0]
        ranker_candidate = ranker_actions[0] if ranker_actions else None
        if ranker_candidate in allowed_set:
            action = ranker_candidate
            debug = {
                "action_source": "ranker_masked_directive",
                "ranker_proposal_applied": ranker_candidate.value.lower(),
                "allowed_actions": [a.value for a in allowed_actions],
                "action_mask": action_mask,
            }
        else:
            action = fallback_action
            debug = {
                "action_source": "allowed_action_mask_fallback",
                "ranker_proposal_applied": (
                    "no_ranker_action_fallback"
                    if ranker_candidate is None
                    else "fallback_to_allowed_head"
                ),
                "invalid_action": ranker_candidate is not None,
                "invalid_ranker_action": ranker_candidate.value if ranker_candidate else None,
                "allowed_actions": [a.value for a in allowed_actions],
                "action_mask": action_mask,
            }

        # 5) 是認の付加
        add_affirm_mode = decide_affirm(features, state, user_text)

        # 6) 次状態（このターンの想定更新）
        next_state = apply_action_to_state(
            state=state, features=features, action=action, add_affirm=add_affirm_mode
        )

        decision = Decision(
            phase=state.phase,
            main_action=action,
            add_affirm=add_affirm_mode,
            next_state=next_state,
            debug={"features": asdict(features), **debug},
        )

        # 7) 発話生成（A）
        dialogue = _history_to_dialogue(history, max_turns=20)
        pred3 = self.reply(
            dialogue=dialogue,
            phase=_to_phase_label(state.phase),
            main_action=action.value,  # type: ignore[arg-type]
            add_affirm=bool(add_affirm_mode),
        )
        reply = str(pred3.reply).strip()

        ok, reason = validate_output(action, reply)
        if not ok:
            pred4 = self.repair(
                dialogue=dialogue,
                phase=_to_phase_label(state.phase),
                main_action=action.value,  # type: ignore[arg-type]
                add_affirm=bool(add_affirm_mode),
                bad_reply=reply,
                violation_reason=reason,
            )
            reply = str(pred4.reply).strip()

        # 8) 履歴更新（assistant）
        history.append(("assistant", reply))

        # 9) last_user_text 更新
        next_state.last_user_text = user_text

        return reply, decision, next_state, features

    def forward(self, client_script: List[str], max_turns: int = 8):
        """
        セッション最適化用（固定台本のクライアント発話で回す）
        """
        state = DialogueState()
        history: List[Tuple[str, str]] = []
        session_log: List[dict] = []

        turns = client_script[:max_turns]
        for user_text in turns:
            reply, decision, next_state, features = self.step_once(
                state=state, history=history, user_text=user_text
            )

            session_log.append(
                {
                    "client": user_text,
                    "counselor": reply,
                    "phase": decision.phase.value,
                    "main_action": decision.main_action.value,
                    "add_affirm": decision.add_affirm,
                    "features": asdict(features),
                    "debug": decision.debug,
                }
            )
            state = next_state

        return dspy.Prediction(session_log=session_log)
