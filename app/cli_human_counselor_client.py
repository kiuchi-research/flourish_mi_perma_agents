import os
import json
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from env_utils import build_llm_from_config, get_model_config, load_openai_api_key
from client_llm_loader import build_client_llms
from perma_client_agent import SimpleClientLLM
from conversation_environment import ConversationTurn, ManualConversationEnvironment
from session_log_tools import finalize_session
from mi_counselor_agent import (
    DialogueState,
    InfoMode,
    LLMClient,
    LLMPhaseClassifier,
    MainAction,
    Phase,
    PlannerConfig,
    apply_action_to_state,
    extract_features,
)

# =========================
# LLM action classifier (for counselor utterance)
# =========================
_ACTION_LABELS = [a.value for a in MainAction]


def _extract_first_json_object(text: str) -> Optional[str]:
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    return m.group(0)


def _heuristic_add_affirm(counselor_text: str) -> bool:
    # かなり雑なヒューリスティック（失敗時のフォールバック用）
    markers = ["工夫", "努力", "頑張", "大事に", "大切に", "強み", "前進", "できて", "良いですね"]
    return any(m in counselor_text for m in markers)


def _heuristic_action(counselor_text: str) -> MainAction:
    t = counselor_text.strip()
    if not t:
        return MainAction.REFLECT

    # ASK_PERMISSION を先に判定（"してもよろしいですか" 等）
    if any(k in t for k in ["よろしいでしょうか", "よろしいですか", "してもいい", "してもよい", "差し支え", "共有しても"]):
        if ("？" in t) or ("?" in t) or ("ですか" in t) or ("でしょうか" in t):
            return MainAction.ASK_PERMISSION

    # PROVIDE_INFO（情報提示っぽい）
    if any(k in t for k in ["例えば", "一般に", "方法", "コツ", "選択肢", "ポイント", "目安"]):
        return MainAction.PROVIDE_INFO

    # SUMMARY（まとめ）
    if any(k in t for k in ["まとめると", "要するに", "ここまで", "整理すると"]):
        return MainAction.SUMMARY

    # QUESTION
    if ("？" in t) or ("?" in t) or t.endswith("ですか") or t.endswith("でしょうか"):
        return MainAction.QUESTION

    return MainAction.REFLECT


class LLMActionClassifier:
    """
    人間カウンセラーの発話を、LLMにより MainAction + add_affirm に分類します。
    （ラベルデータ作成のための自動アノテーション）
    """

    def __init__(self, llm: LLMClient, *, temperature: float = 0.0, max_history_turns: int = 8):
        self.llm = llm
        self.temperature = float(temperature)
        self.max_history_turns = int(max_history_turns)

    def classify(
        self,
        *,
        phase: Phase,
        last_client_text: str,
        counselor_text: str,
        history: List[Tuple[str, str]],
    ) -> Tuple[MainAction, bool, Dict[str, Any]]:
        """
        返り値:
          - main_action
          - add_affirm
          - debug
        """
        labels = " / ".join(_ACTION_LABELS)

        # 履歴（短縮）
        lines: List[str] = []
        for role, text in history[-self.max_history_turns :]:
            prefix = "Client" if role == "user" else "Counselor"
            lines.append(f"{prefix}: {text}")
        dialogue = "\n".join(lines)

        system = (
            "あなたは対話ログのアノテーション担当です。\n"
            "次のカウンセラー発話を、MI（動機づけ面接）のOARSに沿う行動ラベルへ分類します。\n"
            "\n"
            f"【main_action ラベル】{labels}\n"
            "\n"
            "【ラベル定義（短縮）】\n"
            "- REFLECT: 相手の言葉/感情/価値の言い換え・反射。基本的に質問しない。\n"
            "- QUESTION: 1つの質問（情報収集・掘り下げ）。\n"
            "- SUMMARY: ここまでの要点をまとめる。\n"
            "- ASK_PERMISSION: 情報提供/提案の前に許可を取る。\n"
            "- PROVIDE_INFO: 中立に情報・選択肢・提案を提示し、最後に反応を尋ねてもよい。\n"
            "\n"
            "【add_affirm】\n"
            "- True: 努力/工夫/強み/価値観/前進を具体的に認める一言が含まれる\n"
            "- False: それ以外\n"
            "\n"
            "【出力形式】\n"
            "- 余計な文章は書かず、次の JSON だけを1行で出力してください。\n"
            '  例: {"main_action":"REFLECT","add_affirm":false}\n'
        )

        user = (
            f"【フェーズ】{phase.value}\n"
            f"【直近の対話】\n{dialogue}\n"
            "\n"
            f"【直近のクライアント発話】{last_client_text}\n"
            f"【分類対象のカウンセラー発話】{counselor_text}\n"
            "\n"
            "出力："
        )

        raw = self.llm.generate(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.temperature,
        )
        raw = str(raw).strip()

        main_action: Optional[MainAction] = None
        add_affirm: Optional[bool] = None

        # JSONパース
        try:
            js = _extract_first_json_object(raw) or raw
            obj = json.loads(js)
            ma = str(obj.get("main_action", "")).strip()
            af = obj.get("add_affirm", None)

            if ma in _ACTION_LABELS:
                main_action = MainAction(ma)

            if isinstance(af, bool):
                add_affirm = af
            elif isinstance(af, (int, float)):
                add_affirm = bool(af)

        except Exception:
            pass

        # フォールバック
        if main_action is None:
            main_action = _heuristic_action(counselor_text)
        if add_affirm is None:
            add_affirm = _heuristic_add_affirm(counselor_text)

        debug = {
            "raw": raw,
            "main_action": main_action.value,
            "add_affirm": bool(add_affirm),
        }
        return main_action, bool(add_affirm), debug


# =========================
# main loop
# =========================
def main(
    *,
    script_name: str = "human_counselor_client_cli",
    log_prefix: str = "session_human_counselor_client_cli",
) -> None:
    api_key = load_openai_api_key()
    phase_cfg = get_model_config(
        "counselor_phase",
        role="counselor",
    )
    action_cfg = get_model_config(
        "counselor_action",
        role="counselor",
    )
    client_llms = build_client_llms(api_key=api_key)
    client_cfg = client_llms["client_cfg"]
    client_state_cfg = client_llms["client_state_cfg"]
    client_reply_cfg = client_llms["client_reply_cfg"]
    client_llm_state = client_llms["client_llm_state"]
    client_llm_reply = client_llms["client_llm_reply"]
    # ---- client_profiles.yaml からクライアント特性をロード ----
    client_code = (os.getenv("CLIENT_CODE") or "C01").strip() or "C01"
    # counselor (labeler) / action classifier / client LLM
    phase_llm = build_llm_from_config(phase_cfg, api_key)
    action_llm = build_llm_from_config(action_cfg, api_key)
    llm_for_eval = client_llm_reply

    # LLMクライアント（会話相手）
    client, client_bundle = SimpleClientLLM.from_profile(
        client_code=client_code,
        llm=client_llm_reply,
        llm_state=client_llm_state,
        llm_reply=client_llm_reply,
        env_style=os.getenv("CLIENT_STYLE", "auto"),
        first_client_utterance_env=os.getenv("FIRST_CLIENT_UTTERANCE"),
        max_state_step_env=os.getenv("CLIENT_MAX_STATE_STEP", "none"),
    )

    # LLMでフェーズ判定（8フェーズ想定。mi_counselor_agent.Phase に依存）
    phase_clf = LLMPhaseClassifier(llm=phase_llm, temperature=0.0, max_history_turns=8)

    # LLMで「カウンセラー発話の行動ラベル」を推定
    action_clf = LLMActionClassifier(llm=action_llm, temperature=0.0, max_history_turns=10)

    cfg = PlannerConfig()  # 特徴量抽出用（確率制御は人間が喋るので使いません）
    state = DialogueState()
    session_meta = {
        "session_mode": "human_counselor",
        "openai_model": phase_cfg.get("model", ""),
        "action_model": action_cfg.get("model", ""),
        "client_model_state": client_state_cfg.get("model", ""),
        "client_model_reply": client_reply_cfg.get("model", ""),
        "client_reasoning_effort": client_reply_cfg.get("reasoning_effort", ""),
        "client_verbosity": client_reply_cfg.get("verbosity", ""),
        "script_name": script_name,
        "client_style": client_bundle.style,
        "client_code": client_code,
        "client_pattern": client_bundle.derived_meta.get("pattern_code", ""),
        "client_pattern_label": client_bundle.derived_meta.get("pattern_label", ""),
        "client_primary_focus": client_bundle.derived_meta.get("primary_focus_code", ""),
        "client_primary_focus_label": client_bundle.derived_meta.get("primary_focus_label", ""),
        "client_interpersonal_style": client_bundle.derived_meta.get("interpersonal_style_code", ""),
        "client_interpersonal_style_label": client_bundle.derived_meta.get("interpersonal_style_label", ""),
        "client_profiles_path": str(client_bundle.profiles_path),
        "planner_config": asdict(cfg),
    }
    env = ManualConversationEnvironment(session_meta=session_meta)

    # 直近対話（mi_counselor_agent の想定に合わせて user/assistant で持つ）
    history_pairs: List[Tuple[str, str]] = []

    # 初期クライアント発話（デフォルト。必要なら環境変数で上書き）
    first_client_utterance = client_bundle.first_utterance

    env.log.append(ConversationTurn(speaker="client", text=first_client_utterance, meta=None))
    history_pairs.append(("user", first_client_utterance))
    current_client_text = first_client_utterance

    print("人間カウンセラー × LLMクライアント（自動ラベル付け）を開始します。")
    print("Counselor: にあなたの返答を入力してください。'exit' で終了します。")
    print("============================================================")

    while True:
        # ---- 1) フェーズ判定（クライアント発話から）
        phase, phase_debug = phase_clf.classify(history=history_pairs, state=state, user_text=current_client_text)
        state.phase = phase

        # ---- 2) 特徴量（クライアント発話から）
        features = extract_features(current_client_text, state, cfg)

        # WAITING_PERMISSION で明確に拒否なら解除（安全側に倒す）
        if state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is False:
            state.info_mode = InfoMode.NONE

        # ---- 3) 人間カウンセラーの入力
        print(f"Client: {current_client_text}")
        try:
            counselor_text = input("Counselor: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n入力が閉じられたため終了します。")
            break

        if counselor_text.lower() == "exit":
            break

        # ---- 4) 行動ラベル判定（カウンセラー発話から）
        action, add_affirm, action_debug = action_clf.classify(
            phase=phase,
            last_client_text=current_client_text,
            counselor_text=counselor_text,
            history=history_pairs,
        )

        # ---- 5) ログ（カウンセラーターン）
        meta_debug = {
            # CSVで出したいもの（session_log_tools.save_log_csv が参照）
            "reflect_streak": state.reflect_streak,
            "r_since_q": state.r_since_q,
            # 追加情報
            "turn_index": state.turn_index,
            "turns_since_summary": state.turns_since_summary,
            "turns_since_affirm": state.turns_since_affirm,
            "info_mode": state.info_mode.value,
            "features": asdict(features),
            "phase_llm": phase_debug,
            "action_llm": action_debug,
        }

        env.log.append(
            ConversationTurn(
                speaker="counselor",
                text=counselor_text,
                meta={
                    "phase": phase.value,
                    "main_action": action.value,
                    "add_affirm": bool(add_affirm),
                    "debug": meta_debug,
                },
            )
        )
        history_pairs.append(("assistant", counselor_text))

        # ---- 6) state 更新（反射ストリーク/質問間隔など）
        next_state = apply_action_to_state(state=state, features=features, action=action, add_affirm=add_affirm)
        next_state.last_user_text = current_client_text
        state = next_state

        # ---- 7) 次のクライアント発話（LLM）
        next_client_text = client.respond(counselor_text, env.log)

        # ★ 追加：クライアント内部状態をメタ情報として保存
        client_meta: Dict[str, Any] = {}
        client_debug = None
        if hasattr(client, "get_internal_state"):
            try:
                client_state = client.get_internal_state()
                client_meta["client_internal_state"] = client_state
            except Exception:
                pass

        # デバッグ目的でクライアント内部ログをコンソール表示（数値のみ）
        if hasattr(client, "get_last_debug_info"):
            try:
                client_debug = client.get_last_debug_info()
                state_reason = client_debug.get("internal_state_reason") or {}
                meta_extra = client_debug.get("meta") or {}
                parse_status = meta_extra.get("parse_status") or client_debug.get("parse_status")
                new_state = client_debug.get("new_state")

                if isinstance(new_state, dict):
                    printable_state = {k: v for k, v in new_state.items() if not str(k).startswith("trait_")}
                    print("  [client state]", json.dumps(printable_state, ensure_ascii=False))
                if parse_status and parse_status != "ok":
                    print(f"  [client state parse_status] {parse_status}")

                # ログには判断根拠も保持
                if state_reason:
                    client_meta["client_internal_state_reason"] = state_reason
                if meta_extra:
                    client_meta["client_meta"] = meta_extra
                # パース状況がわかるように追加
                if parse_status:
                    client_meta["parse_status"] = parse_status
                if "raw_reply" in (client_debug or {}):
                    client_meta["client_raw"] = client_debug.get("raw_reply")
                elif "raw_state" in (client_debug or {}):
                    client_meta["client_raw"] = client_debug.get("raw_state")
            except Exception:
                client_debug = None

        env.log.append(ConversationTurn(speaker="client", text=next_client_text, meta=(client_meta or None)))
        history_pairs.append(("user", next_client_text))
        current_client_text = next_client_text

        print(f"  [auto-label] phase={phase.value} / action={action.value} / add_affirm={bool(add_affirm)}")
        print("------------------------------------------------------------")

    print("\n==== SESSION DONE ====")

    # ログを日時入りファイル名で保存
    if env.log:
        finalize_session(env, llm_for_eval, log_prefix=log_prefix)


if __name__ == "__main__":
    main()
