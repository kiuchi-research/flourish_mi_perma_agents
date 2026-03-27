# 最適化結果を使って人と対話

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse

from conversation_environment import ConversationEnvironment
from session_log_tools import save_log_csv
from mi_counselor_dspy import MIRhythmBotDSPy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="openai/gpt-4o-mini", help="DSPyのLM指定（例: openai/gpt-4o-mini）")
    parser.add_argument("--reply", default="compiled/mi_reply.json", help="Aで作った発話生成のcompiled")
    parser.add_argument("--phase", default="compiled/mi_phase.json", help="Bで作ったフェーズ判定のcompiled")
    parser.add_argument("--ctr", default="compiled/mi_ctr.json", help="Bで作ったCT/抵抗推定のcompiled")
    parser.add_argument("--ranker", default=None, help="Cの行動ランキング単体をロードしたい場合（通常はsessionを使う）")
    parser.add_argument("--session", default=None, help="Cで作った統合ドライバ compiled/mi_session_driver.json")
    parser.add_argument("--stochastic", action="store_true", help="ルール選択を確率的に（研究用途。推奨はFalse）")
    args = parser.parse_args()

    counselor = MIRhythmBotDSPy.from_compiled(
        dspy_model=args.model,
        compiled_reply=(args.reply if Path(args.reply).exists() else None),
        compiled_phase=(args.phase if Path(args.phase).exists() else None),
        compiled_ctr=(args.ctr if Path(args.ctr).exists() else None),
        compiled_action_ranker=(args.ranker if args.ranker and Path(args.ranker).exists() else None),
        compiled_session_driver=(args.session if args.session and Path(args.session).exists() else None),
        stochastic=args.stochastic,
    )

    env = ConversationEnvironment(counselor=counselor)  # 型ヒント上はMIRhythmBotだが実行は問題ありません

    print("DSPy最適化版 MIボットとの対話を始めます。'exit' で終了します。")

    while True:
        try:
            user_text = input("Client: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n入力が閉じられたため終了します。")
            break

        if user_text.lower() == "exit":
            break

        reply = env.step_with_human(user_text)
        if env.session_meta.get("session_ended"):
            print("セッション終了条件を満たしたため終了します。")
            break
        print("Counselor:", reply)
        print("---")

    # ログ保存
    if env.log:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"session_console_dspy_{timestamp}.csv"
        save_log_csv(env, str(log_path))
        print(f"ログを保存しました: {log_path}")


if __name__ == "__main__":
    main()
