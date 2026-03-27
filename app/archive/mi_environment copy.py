from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from mi_rhythm_bot import DummyLLM, LLMClient, MIRhythmBot
from mi_client_agents import ClientAgent, SimpleClientLLM


Speaker = Literal["client", "counselor"]


@dataclass
class ConversationTurn:
    """
    対話の1発話分のログ。
    - speaker: "client" または "counselor"
    - text: 実際の発話テキスト
    - meta: カウンセラー側のときだけ、フェーズやアクション等のメタ情報を入れる（クライアント側は通常 None）
    """
    speaker: Speaker
    text: str
    meta: Optional[Dict[str, Any]] = None


@dataclass
class ConversationEnvironment:
    """
    カウンセラーエージェント（MIRhythmBot）とクライアントエージェントの
    両者のやり取りと履歴を一元管理する「環境」クラス。

    - counselor: MIRhythmBot（フェーズ判定・リズム制御を内蔵）
    - client: ClientAgent（シミュレーション用途。人間クライアントなら None でもOK）
    - log: ConversationTurn のリストとして、時系列の全発話とメタ情報を保持
    - session_meta: セッション共通のメタデータ（session_id / mode / model など）を格納
    """
    counselor: MIRhythmBot
    client: Optional[ClientAgent] = None
    log: List[ConversationTurn] = field(default_factory=list)
    session_meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "session_id" not in self.session_meta:
            self.session_meta["session_id"] = str(uuid.uuid4())

    def reset(self, *, new_session_id: bool = True) -> None:
        """環境とログをリセット。counselor/clientの内部状態も初期化し、必要なら新しいsession_idを振る。"""
        self.log.clear()
        if hasattr(self.counselor, "reset"):
            self.counselor.reset()
        if self.client is not None and hasattr(self.client, "reset"):
            self.client.reset()  # type: ignore[call-arg]
        if new_session_id:
            self.session_meta["session_id"] = str(uuid.uuid4())

    # ===== 人間クライアント用：1ターン分のやり取り =====
    def step_with_human(self, user_text: str) -> str:
        """
        人間クライアントとの対話に使う入口。
        - 入力: クライアント（人間）の発話
        - 出力: カウンセラーの返答
        """
        # クライアント発話をログに追加
        self.log.append(ConversationTurn(speaker="client", text=user_text, meta=None))

        # カウンセラーの応答（MIRhythmBot が MI ロジック＋LLM で生成）
        reply, decision = self.counselor.step(user_text)

        # カウンセラー発話＋MIの決定ログを追加
        self.log.append(
            ConversationTurn(
                speaker="counselor",
                text=reply,
                meta={
                    "phase": decision.phase.value,
                    "main_action": decision.main_action.value,
                    "add_affirm": decision.add_affirm,
                    "debug": decision.debug,
                },
            )
        )
        return reply

    # ===== LLMクライアントとの自動対話（シミュレーション） =====
    def simulate(
        self,
        first_client_utterance: str,
        max_turns: int = 10,
    ) -> List[ConversationTurn]:
        """
        クライアント側も LLM で自動生成する「自己対話シミュレーション」用。
        - first_client_utterance: 最初のクライアント発話
        - max_turns: カウンセラー→クライアントのラウンド数（片方ずつで2*max_turns発話）
        """
        if self.client is None:
            raise ValueError("simulate() を使うには client エージェントが必要です。")

        user_text = first_client_utterance
        self.log.append(ConversationTurn(speaker="client", text=user_text, meta=None))

        for _ in range(max_turns):
            # 1) カウンセラーが応答
            reply, decision = self.counselor.step(user_text)
            self.log.append(
                ConversationTurn(
                    speaker="counselor",
                    text=reply,
                    meta={
                        "phase": decision.phase.value,
                        "main_action": decision.main_action.value,
                        "add_affirm": decision.add_affirm,
                        "debug": decision.debug,
                    },
                )
            )

            # 2) クライアントが応答
            user_text = self.client.respond(reply, self.log)
            self.log.append(ConversationTurn(speaker="client", text=user_text, meta=None))

        return self.log

    # ===== ログのエクスポート =====
    def to_json_serializable(self) -> List[Dict[str, Any]]:
        """ログを JSON シリアライズしやすい形に変換します。"""
        session_meta = dict(self.session_meta)
        return [
            {"speaker": t.speaker, "text": t.text, "meta": t.meta, "session_meta": session_meta}
            for t in self.log
        ]

    def print_log(self) -> None:
        """コンソールでざっとログを確認したいとき用。"""
        for i, turn in enumerate(self.log):
            head = "C" if turn.speaker == "client" else "T"  # C=Client, T=Therapist
            print(f"[{i:02d}] {head}: {turn.text}")
            if turn.meta:
                phase = turn.meta.get("phase")
                action = turn.meta.get("main_action")
                print(f"      meta: phase={phase}, action={action}")


# ===== デモ用スクリプト =====

def demo_human_like() -> None:
    """
    人間クライアントを想定した簡易デモ。
    """
    counselor = MIRhythmBot(llm=DummyLLM())
    env = ConversationEnvironment(counselor=counselor)

    inputs = [
        "最近、夜更かしが増えてしまって困っています。",
        "でも仕事が忙しくて、ついだらだらしてしまいます。",
        "そうですね…本当は、もう少し自分の時間も大事にしたい気持ちがあります。",
    ]

    for u in inputs:
        reply = env.step_with_human(u)
        print("Client   :", u)
        print("Counselor:", reply)
        print("---")

    print("==== LOG ====")
    env.print_log()


def demo_two_agents() -> None:
    """
    カウンセラーとクライアントの両方を LLM で回すシミュレーションのデモ（DummyLLM）。
    """
    counselor = MIRhythmBot(llm=DummyLLM())
    client = SimpleClientLLM(llm=DummyLLM())
    env = ConversationEnvironment(counselor=counselor, client=client)

    env.simulate(
        first_client_utterance="最近、生活リズムが崩れてしまって、気持ちも落ち込んでいます。",
        max_turns=5,
    )

    print("==== SIMULATION LOG ====")
    env.print_log()


if __name__ == "__main__":
    demo_human_like()
    print("\n\n")
    demo_two_agents()
