import os
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from mi_client_agents import SimpleClientLLM
from mi_environment import ConversationTurn
from mi_log_tools import (
    save_log_csv,
    evaluate_session_from_client_pov,
    save_client_evaluation_json,
)
from mi_rhythm_bot import (
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


class OpenAILLM(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-nano",
        reasoning_effort: str = "low",
        verbosity: str = "low",
    ):
        # OpenAI Python SDK (v1系)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity

    @staticmethod
    def _should_use_json_mode(messages: List[Dict[str, str]]) -> bool:
        """
        メッセージ本文に 'json' が含まれるかどうかで JSON モードを判定（大文字小文字は区別しない）
        """
        try:
            for m in messages:
                content = str(m.get("content", "") or "").lower()
                if "json" in content:
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _extract_output_text_from_response(response: Any) -> str:
        """
        openai.responses.create の返り値からテキストを抽出。
        SDKが提供する output_text があればそれを優先し、無ければ output を走査して連結する。
        """
        out_text = getattr(response, "output_text", None)
        if isinstance(out_text, str):
            return out_text

        # フォールバック: response.output[*].content[*].text を連結
        chunks: List[str] = []
        output = getattr(response, "output", None)
        if output:
            for item in output:
                content = getattr(item, "content", None)
                if not content:
                    continue
                for c in content:
                    t = getattr(c, "text", None)
                    if isinstance(t, str):
                        chunks.append(t)
        return "".join(chunks)

    @staticmethod
    def _model_disallows_temperature(model: str) -> bool:
        """
        GPT-5-mini / GPT-5-nano 等では temperature を送るとエラーになり得るため抑止。
        （モデル名はスナップショット名も考慮して prefix 判定）
        """
        m = (model or "").strip()
        return (
            m == "gpt-5"
            or m.startswith("gpt-5-mini")
            or m.startswith("gpt-5-nano")
        )

    def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """
        LLMClient インタフェースに合わせた Responses API ラッパー。

        - input は messages（role/content の配列）をそのまま渡します。
        - JSON が必要そうなときだけ text.format=json_object を付与します。
        - gpt-5-mini / gpt-5-nano 等では temperature を送らない（互換性の都合）。
        - seed は Responses API では一般に使えない/保証されないため黙って捨てます（エラー回避）。
        """

        # kwargs の破壊を避けたいのでコピー
        extra: Dict[str, Any] = dict(kwargs) if kwargs else {}

        # Responses API 互換のために不要/危険な引数を除去
        extra.pop("seed", None)          # 呼び出し側が渡してきても落とさない
        extra.pop("messages", None)      # 念のため
        extra.pop("response_format", None)

        # max_tokens を使っている箇所が将来出ても動くように軽い救済
        if "max_tokens" in extra and "max_output_tokens" not in extra:
            extra["max_output_tokens"] = extra.pop("max_tokens")

        req: Dict[str, Any] = {
            "model": self.model,
            "input": messages,
            # 会話ログ系なら store=False の方が安全（API側に「後で取得できる形で保存」しない）
            "store": False,
        }

        # JSONモード判定 → Responses API の text.format に変換
        if self._should_use_json_mode(messages):
            req["text"] = {"format": {"type": "json_object"}}
        else:
            # デフォルトは通常テキスト出力
            req["text"] = {"format": {"type": "text"}}

        # verbosity は text 配下で指定する（JSON/Text 共通）
        if self.verbosity:
            req.setdefault("text", {})
            req["text"]["verbosity"] = self.verbosity

        # reasoning effort は top-level の reasoning で指定
        if self.reasoning_effort:
            req["reasoning"] = {"effort": self.reasoning_effort}

        # temperature は gpt-5-mini / gpt-5-nano では送らない（互換性注意）
        if not self._model_disallows_temperature(self.model):
            req["temperature"] = float(temperature)

        # 残りのオプションをマージ（model/input/store/text を上書きしない）
        for k, v in extra.items():
            if k in ("model", "input", "store", "text"):
                continue
            req[k] = v

        # Responses API 呼び出し
        response = self.client.responses.create(**req)

        return self._extract_output_text_from_response(response)


def load_openai_api_key() -> str:
    """
    .env（OPENAI_API_KEY）または環境変数からAPIキーを取得する。
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(".env または環境変数に OPENAI_API_KEY が設定されていません。")
    return api_key


# =========================
# Manual environment (duck-typed for mi_log_tools)
# =========================
@dataclass
class ManualConversationEnvironment:
    log: List[ConversationTurn] = field(default_factory=list)
    session_meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "session_id" not in self.session_meta:
            self.session_meta["session_id"] = str(uuid.uuid4())

    def to_json_serializable(self) -> List[Dict[str, Any]]:
        session_meta = dict(self.session_meta)
        return [{"speaker": t.speaker, "text": t.text, "meta": t.meta, "session_meta": session_meta} for t in self.log]


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
def main():
    api_key = load_openai_api_key()
    model = os.getenv("OPENAI_MODEL", "gpt-5-nano")
    client_model = os.getenv("OPENAI_CLIENT_MODEL", "gpt-5-mini")
    client_reasoning_effort = os.getenv("OPENAI_CLIENT_REASONING_EFFORT", "medium")
    client_verbosity = os.getenv("OPENAI_CLIENT_VERBOSITY", "low")
    client_style = os.getenv("CLIENT_STYLE", "cooperative")
    # 状態変化幅（Noneなら制限なし）
    client_max_step_env = os.getenv("CLIENT_MAX_STATE_STEP", "none")
    try:
        client_max_step = float(client_max_step_env)
    except (TypeError, ValueError):
        # "none" などは制限なしとして扱う
        client_max_step = None

    llm = OpenAILLM(api_key=api_key, model=model)
    client_llm = OpenAILLM(
        api_key=api_key,
        model=client_model,
        reasoning_effort=client_reasoning_effort,
        verbosity=client_verbosity,
    )

    # LLMクライアント（会話相手）
    client = SimpleClientLLM(llm=client_llm, style=client_style, max_state_step=client_max_step)

    # LLMでフェーズ判定（8フェーズ想定。mi_rhythm_bot.Phase に依存）
    phase_clf = LLMPhaseClassifier(llm=llm, temperature=0.0, max_history_turns=8)

    # LLMで「カウンセラー発話の行動ラベル」を推定
    action_clf = LLMActionClassifier(llm=llm, temperature=0.0, max_history_turns=10)

    cfg = PlannerConfig()  # 特徴量抽出用（確率制御は人間が喋るので使いません）
    state = DialogueState()
    session_meta = {
        "session_mode": "human_counselor",
        "openai_model": model,
        "client_model": client_model,
        "client_reasoning_effort": client_reasoning_effort,
        "client_verbosity": client_verbosity,
        "script_name": "console_chat_counselor",
        "client_style": client_style,
        "planner_config": asdict(cfg),
    }
    env = ManualConversationEnvironment(session_meta=session_meta)

    # 直近対話（mi_rhythm_bot の想定に合わせて user/assistant で持つ）
    history_pairs: List[Tuple[str, str]] = []

    # 初期クライアント発話（デフォルト。必要なら環境変数で上書き）
    first_client_utterance = os.getenv(
        "FIRST_CLIENT_UTTERANCE",
        "相談させてください。",
    )

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
            # CSVで出したいもの（mi_log_tools.save_log_csv が参照）
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
                parse_status = client_debug.get("meta", {}).get("parse_status") or client_debug.get("parse_status")
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
                if "parse_status" in (client_debug or {}):
                    client_meta["parse_status"] = client_debug.get("parse_status")
                if "raw" in (client_debug or {}):
                    client_meta["client_raw"] = client_debug.get("raw")
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
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # ① 従来通りの CSV ログ
        log_path = logs_dir / f"session_human_counselor_{timestamp}.csv"
        save_log_csv(env, str(log_path))
        print(f"ログを保存しました: {log_path}")

        # ② クライアント視点のセッション評価（LLM）
        client_eval = evaluate_session_from_client_pov(env, llm)
        eval_path = logs_dir / f"session_human_counselor_{timestamp}_client_eval.json"
        save_client_evaluation_json(client_eval, str(eval_path))
        print(f"クライアント評価を保存しました: {eval_path}")


if __name__ == "__main__":
    main()
