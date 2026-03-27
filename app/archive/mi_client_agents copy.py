from __future__ import annotations

"""
クライアント側エージェント（シミュレーション用）

- mi_environment.py から切り出したい場合のための独立モジュールです。
- 人間カウンセラー × LLMクライアント（ラベル付け用）
- LLMカウンセラー × LLMクライアント（自己対話シミュレーション）

の両方で共通に使えます。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Literal, Optional
import json

from mi_rhythm_bot import LLMClient


class ClientAgent(Protocol):
    """
    クライアント側エージェントのインタフェース。

    respond:
      - counselor_text: 直近のカウンセラー発話（今回の入力）
      - history: ConversationTurn っぽいオブジェクトのリスト（speaker/text 属性があればOK）
      - return: 次のクライアント発話（str）
    """

    def respond(self, counselor_text: str, history: List[Any]) -> str:
        ...


# ==============================
# クライアント内部状態
# ==============================

@dataclass
class ClientInternalState:
    """
    クライアントの「内部ログ」として持つ6つの指標（すべて 0〜10 の連続値）。

    - pos_affect: ポジティブ感情の強さ
    - neg_affect: ネガティブ感情の強さ
    - importance_change: 変化・目標達成の重要度の認識
    - confidence_change: 変化・目標達成の自信度の認識
    - like_counselor: カウンセラーへの好感
    - tension_counselor: カウンセラーへの不和感・緊張
    """

    pos_affect: float = 5.0
    neg_affect: float = 5.0
    importance_change: float = 5.0
    confidence_change: float = 5.0
    like_counselor: float = 5.0
    tension_counselor: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "pos_affect": float(self.pos_affect),
            "neg_affect": float(self.neg_affect),
            "importance_change": float(self.importance_change),
            "confidence_change": float(self.confidence_change),
            "like_counselor": float(self.like_counselor),
            "tension_counselor": float(self.tension_counselor),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientInternalState":
        """
        JSON などから復元するためのヘルパー。
        想定外のキーや値は無視しつつ、既定値をベースに上書きします。
        """
        base = cls()
        if not isinstance(data, dict):
            return base

        for key in base.to_dict().keys():
            v = data.get(key)
            if v is None:
                continue
            try:
                setattr(base, key, float(v))
            except (TypeError, ValueError):
                # 数値に変換できないときは無視
                continue

        return base


@dataclass
class SimpleClientLLM(ClientAgent):
    """
    LLMを使ったシンプルなクライアントエージェント。

    - 「悩みを持つクライアント」として自然に返答する役
    - 実験・シミュレーション用途
    """
    llm: LLMClient
    style: Literal["cooperative", "ambivalent", "resistant"] = "cooperative"
    persona: Optional[str] = None
    temperature: float = 0.4
    max_history_turns: int = 20

    # ★ クライアントの内部状態（ターンごとに更新）
    internal_state: ClientInternalState = field(default_factory=ClientInternalState)

    def __post_init__(self) -> None:
        if self.persona is None:
            self.persona = self._build_persona(self.style)
        else:
            self.persona = str(self.persona)

    def reset(self) -> None:
        """
        セッションリセット時に呼ばれることを想定。
        内部状態も初期値に戻します。
        """
        self.internal_state = ClientInternalState()

    def get_internal_state(self) -> Dict[str, float]:
        """
        ConversationEnvironment からログ用に呼ぶためのアクセサ。
        """
        return self.internal_state.to_dict()

    @staticmethod
    def _build_persona(style: str) -> str:
        presets = {
            "cooperative": (
                "あなたは、生活や行動のことで少し困りごとを抱えているクライアントです。\n"
                "自分の気持ちや状況を、できる範囲で正直に、丁寧な口調で話してください。\n"
                "カウンセラーと対立するのではなく、自分の本音や迷いを表現してよい場です。\n"
            ),
            "ambivalent": (
                "あなたは、変わりたい気持ちと『どうせ無理かも』という迷いが混ざったクライアントです。\n"
                "前向きな気持ちと不安やためらいの両方を、丁寧な口調で率直に言葉にしてください。\n"
                "反射には自然に反応しつつ、時には尻込みしたり、決めきれない様子も出してかまいません。\n"
            ),
            "resistant": (
                "あなたは、少し構え気味で、変化に疑問や不信感を持つクライアントです。\n"
                "丁寧さは保ちつつも『でも』『どうせ』『前も失敗した』など、抵抗や懐疑がにじむ返答を織り交ぜてください。\n"
                "ただし攻撃的にはならず、本音ベースでの反応に留めてください。\n"
            ),
        }
        return presets.get(style, presets["cooperative"])

    # ------------------------------
    # 返答＋内部状態更新
    # ------------------------------
    def respond(self, counselor_text: str, history: List[Any]) -> str:
        """
        - これまでの履歴＋現在の内部状態を LLM に渡す
        - LLM から
            { "reply": ..., "internal_state": {...} }
          という JSON を生成させる
        - reply を返しつつ、internal_state を更新する
        """
        # いま時点の内部状態
        state_dict = self.internal_state.to_dict()

        # システムプロンプト：ペルソナ＋内部状態＋出力形式の指定
        system_prompt = (
            (self.persona or "")
            + "\n\n"
            "【あなたの内部状態スコアについて】\n"
            "あなたには、次の6つの内部状態スコアがあります。すべて 0〜10 の範囲です。\n"
            "- pos_affect: ポジティブな気分の強さ\n"
            "- neg_affect: ネガティブな気分の強さ\n"
            "- importance_change: 変化・目標達成の重要度の感じ方\n"
            "- confidence_change: 変化・目標達成の自信度\n"
            "- like_counselor: カウンセラーへの好感\n"
            "- tension_counselor: カウンセラーへの不和感・緊張\n\n"
            f"現時点のスコア: {json.dumps(state_dict, ensure_ascii=False)}\n\n"
            "これまでの会話と現在のスコアを踏まえて、"
            "直近のカウンセラーの発話に対するあなたの次の発話と、"
            "その発話後に更新されたスコアを出力してください。\n"
            "出力は必ず次の JSON 形式「だけ」で返してください:\n"
            "{\n"
            '  "reply": "<クライアントとしての次の発話>",\n'
            '  "internal_state": {\n'
            '    "pos_affect": 0〜10の数値,\n'
            '    "neg_affect": 0〜10の数値,\n'
            '    "importance_change": 0〜10の数値,\n'
            '    "confidence_change": 0〜10の数値,\n'
            '    "like_counselor": 0〜10の数値,\n'
            '    "tension_counselor": 0〜10の数値\n'
            "  }\n"
            "}\n"
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # history は ConversationTurn を想定（speaker/text 属性）。型が違っても duck typing で動きます。
        for turn in history[-self.max_history_turns :]:
            speaker = getattr(turn, "speaker", "")
            text = getattr(turn, "text", "")
            if not isinstance(text, str):
                continue
            role = "assistant" if speaker == "counselor" else "user"
            messages.append({"role": role, "content": text})

        # 直近の counselor_text を明示的に加える（ただし、すでに同一内容が末尾にあるなら二重に入れない）
        if not (
            history
            and getattr(history[-1], "speaker", None) == "counselor"
            and getattr(history[-1], "text", "").strip() == counselor_text.strip()
        ):
            messages.append({"role": "assistant", "content": counselor_text})

        raw = self.llm.generate(messages, temperature=float(self.temperature))
        reply, new_state_dict = self._parse_reply_and_state(str(raw))

        # 内部状態を更新
        self.internal_state = ClientInternalState.from_dict(new_state_dict)

        return str(reply).strip()

    def _parse_reply_and_state(self, raw: str) -> tuple[str, Dict[str, float]]:
        """
        LLM からの出力をパースして
        - reply（発話）
        - internal_state（辞書形式）
        を取り出す。

        JSON でなかった場合は、raw 全体を発話とみなし、内部状態は変えずに返します。
        """
        raw = raw.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # フォールバック：そのまま返答として扱う
            return raw, self.internal_state.to_dict()

        if not isinstance(data, dict):
            return raw, self.internal_state.to_dict()

        reply = str(data.get("reply", "")).strip() or raw

        state_in = data.get("internal_state") or {}
        merged = self.internal_state.to_dict()

        if isinstance(state_in, dict):
            for key in merged.keys():
                v = state_in.get(key)
                if v is None:
                    continue
                try:
                    merged[key] = float(v)
                except (TypeError, ValueError):
                    continue

        # 値を 0〜10 にクリップ
        for k, v in list(merged.items()):
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            if f < 0.0:
                f = 0.0
            elif f > 10.0:
                f = 10.0
            merged[k] = f

        return reply, merged
