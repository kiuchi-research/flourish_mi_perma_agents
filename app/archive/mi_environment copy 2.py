from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Protocol, Tuple

from mi_client_agents import ClientAgent, SimpleClientLLM
from mi_rhythm_bot import Decision, DummyLLM, MIRhythmBot


Speaker = Literal["client", "counselor"]


@dataclass
class ConversationTurn:
    """
    対話の1発話分のログ。
    - speaker: "client" または "counselor"
    - text: 実際の発話テキスト
    - meta: カウンセラー側のときだけ、フェーズ/アクション等のメタ情報（クライアント側は通常 None）
    """
    speaker: Speaker
    text: str
    meta: Optional[Dict[str, Any]] = None


class CounselorAgent(Protocol):
    """
    カウンセラー側エージェントのインタフェース。

    MIRhythmBot / MIRhythmBotDSPy / 人間カウンセラー入力用エージェント など、
    step(user_text) -> (reply, Decision) を満たすものを受け取れます。
    """

    def step(self, user_text: str) -> Tuple[str, Decision]:
        ...


@dataclass
class ConversationEnvironment:
    """
    カウンセラーエージェントとクライアントエージェントの
    両者のやり取りと履歴を一元管理する「環境」クラス。

    - counselor: CounselorAgent（例: MIRhythmBot）
    - client: ClientAgent（シミュレーション用途。人間クライアントなら None でもOK）
    - log: ConversationTurn のリストとして、時系列の全発話とメタ情報を保持
    """
    counselor: CounselorAgent
    client: Optional[ClientAgent] = None
    log: List[ConversationTurn] = field(default_factory=list)

    def reset(self) -> None:
        """環境とログをリセット。"""
        self.log.clear()

    # ===== 人間クライアント用：1ターン分のやり取り =====
    def step_with_human(self, user_text: str) -> str:
        """
        人間クライアントとの対話に使う入口……ですが、
        「入力が文字列である」なら人間/LLMどちらでも使えます。

        - 入力: クライアント発話（人間でもLLMでも可）
        - 出力: カウンセラーの返答

        内部では:
        - ログに client/counselor の発話とメタ情報を追加
        - counselor 内部の状態も更新（counselor実装次第）
        """
        # クライアント発話をログに追加
        self.log.append(ConversationTurn(speaker="client", text=user_text, meta=None))

        # カウンセラーに渡す（MIロジック＋LLM あるいは 人間入力 などで応答を生成）
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
        返り値は全 ConversationTurn のログ。
        """
        if self.client is None:
            raise ValueError("simulate() を使うには client エージェントが必要です。")

        # 初手のクライアント発話
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
        """ログを JSON シリアライズしやすい形に変換するユーティリティ。"""
        return [{"speaker": t.speaker, "text": t.text, "meta": t.meta} for t in self.log]

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
    実際には input()/GUI などで user_text を受け取る部分を別に作って、
    この関数のロジックを参考にしてください。
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
    カウンセラーとクライアントの両方を LLM（ここではDummyLLM）で回すシミュレーションのデモ。
    """
    counselor = MIRhythmBot(llm=DummyLLM())
    client = SimpleClientLLM(llm=DummyLLM())
    env = ConversationEnvironment(counselor=counselor, client=client)

    env.reset()
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
