from __future__ import annotations

"""
既存の ConversationEnvironment にそのまま刺せる DSPy 版カウンセラー。

- Aだけ: reply_program を load
- Bも: phase_program / ctr_program を load
- Cも: session_driver（中に reply/ranker 等を含む）を load

※既存の mi_counselor_agent.py / conversation_environment.py / session_log_tools.py は変更不要。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
import dspy

from mi_counselor_agent import (
    Decision,
    DialogueState,
    PlannerConfig,
)

from mi_dspy_programs import (
    MISessionDriverProgram,
)


def configure_dspy_lm(model: str = "openai/gpt-4o-mini") -> None:
    """
    DSPy の LM を設定します。
    OPENAI_API_KEY は .env または環境変数から読み取ります。
    """
    # 既存プロジェクトに合わせて ../.env を読む
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    # dspy.LM は環境変数 OPENAI_API_KEY を読むので、ここでは存在チェックだけ
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(".env または環境変数に OPENAI_API_KEY が設定されていません。")

    lm = dspy.LM(model)
    dspy.configure(lm=lm)


@dataclass
class MIRhythmBotDSPy:
    """
    ConversationEnvironment 互換: step(user_text) -> (reply, Decision)
    """
    cfg: PlannerConfig = field(default_factory=lambda: PlannerConfig(stochastic=False))
    state: DialogueState = field(default_factory=DialogueState)
    history: List[Tuple[str, str]] = field(default_factory=list)

    # 内部エンジン（DSPy program）
    engine: MISessionDriverProgram = field(default_factory=MISessionDriverProgram)

    @classmethod
    def from_compiled(
        cls,
        *,
        dspy_model: str = "openai/gpt-4o-mini",
        # A/B 個別ロード
        compiled_reply: Optional[str] = None,
        compiled_phase: Optional[str] = None,
        compiled_ctr: Optional[str] = None,
        compiled_action_ranker: Optional[str] = None,
        # C 統合ロード（最優先）
        compiled_session_driver: Optional[str] = None,
        stochastic: bool = False,
    ) -> "MIRhythmBotDSPy":
        configure_dspy_lm(dspy_model)

        cfg = PlannerConfig(stochastic=stochastic)

        if compiled_session_driver:
            engine = MISessionDriverProgram(
                cfg=cfg,
                use_phase_program=True,
                use_ctr_program=True,
                use_action_ranker=True,
            )
            engine.load(compiled_session_driver)
            return cls(cfg=cfg, engine=engine)

        # 個別ロード（A/B/Cを段階的に）
        use_phase = bool(compiled_phase)
        use_ctr = bool(compiled_ctr)
        use_ranker = bool(compiled_action_ranker)

        engine = MISessionDriverProgram(
            cfg=cfg,
            use_phase_program=use_phase,
            use_ctr_program=use_ctr,
            use_action_ranker=use_ranker,
        )

        if compiled_reply:
            engine.reply.load(compiled_reply)
        if compiled_phase and engine.phase_program is not None:
            engine.phase_program.load(compiled_phase)
        if compiled_ctr and engine.ctr_program is not None:
            engine.ctr_program.load(compiled_ctr)
        if compiled_action_ranker and engine.action_ranker is not None:
            engine.action_ranker.load(compiled_action_ranker)

        return cls(cfg=cfg, engine=engine)

    def step(self, user_text: str):
        reply, decision, next_state, _features = self.engine.step_once(
            state=self.state,
            history=self.history,
            user_text=user_text,
        )
        self.state = next_state
        return reply, decision
