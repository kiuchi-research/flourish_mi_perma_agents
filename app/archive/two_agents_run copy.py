import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from mi_rhythm_bot import LLMClient, MIRhythmBot
from mi_client_agents import SimpleClientLLM
from mi_environment import ConversationEnvironment, ConversationTurn


class OpenAILLM(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        # v1 OpenAI Python クライアントを利用
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, messages: List[Dict[str, str]], *, temperature: float = 0.2) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        try:
            return "".join(getattr(part, "text", "") for part in content or [])
        except Exception:
            return ""


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


def main():
    api_key = load_openai_api_key()
    model = os.getenv("OPENAI_MODEL", "gpt-4")
    client_style = os.getenv("CLIENT_STYLE", "cooperative")
    llm = OpenAILLM(api_key=api_key, model=model)

    counselor = MIRhythmBot(llm=llm)
    client = SimpleClientLLM(llm=llm, style=client_style)

    session_meta = {
        "session_mode": "self_play",
        "openai_model": model,
        "script_name": "two_agents_run",
        "client_style": client_style,
        "planner_config": asdict(counselor.cfg),
    }
    env = ConversationEnvironment(counselor=counselor, client=client, session_meta=session_meta)

    # 進行を逐次表示しながらシミュレーション
    first = "最近、生活リズムが崩れてしまって、気持ちも落ち込んでいます。"
    max_turns = 5

    env.reset()
    env.log.append(ConversationTurn(speaker="client", text=first, meta=None))
    print(f"[00] C: {first}")

    for _ in range(max_turns):
        # カウンセラーの応答
        reply, decision = env.counselor.step(env.log[-1].text)
        meta = {
            "phase": decision.phase.value,
            "main_action": decision.main_action.value,
            "add_affirm": decision.add_affirm,
            "debug": decision.debug,
        }
        env.log.append(ConversationTurn(speaker="counselor", text=reply, meta=meta))
        print(f"[{len(env.log)-1:02d}] T: {reply}")
        print(f"      meta: phase={meta['phase']}, action={meta['main_action']}")

        # クライアント（LLM）の応答
        user_text = env.client.respond(reply, env.log)  # type: ignore[union-attr]
        env.log.append(ConversationTurn(speaker="client", text=user_text, meta=None))
        print(f"[{len(env.log)-1:02d}] C: {user_text}")

    print("\n==== SIMULATION DONE ====")

    # ログを日時入りファイル名で保存
    if env.log:
        from mi_log_tools import save_log_csv

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"session_simulation_{timestamp}.csv"
        save_log_csv(env, str(log_path))
        print(f"ログを保存しました: {log_path}")


if __name__ == "__main__":
    main()
