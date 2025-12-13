# A: 発話生成だけ最適化

from __future__ import annotations

import os
from pathlib import Path

import dspy
from dspy.evaluate import Evaluate
from dspy.teleprompt import MIPROv2

from mi_counselor_dspy import configure_dspy_lm
from mi_dspy_data import (
    build_A_turn_rows_from_logs,
    split_train_dev,
    write_jsonl,
    load_turn_examples,
)
from mi_dspy_metrics import reply_quality_metric
from mi_dspy_programs import MIReplyProgram


def main():
    configure_dspy_lm(os.getenv("DSPY_MODEL", "openai/gpt-4o-mini"))

    data_dir = Path("data")
    out_dir = Path("compiled")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_path = data_dir / "a_turn_train.jsonl"
    dev_path = data_dir / "a_turn_dev.jsonl"

    # データがなければ logs/ から作る（弱教師：replyはログのcounselor発話）
    if (not train_path.exists()) or (not dev_path.exists()):
        rows = build_A_turn_rows_from_logs("logs")
        if not rows:
            raise RuntimeError(
                "logs/*.csv が見つかりません。先に `python cli.py human-client` や "
                "`python cli.py self-play`（旧 human_client_counselor_cli.py / agent_dual_simulation.py） "
                "などでログを作ってください。"
            )
        train_rows, dev_rows = split_train_dev(rows, dev_ratio=0.2)
        write_jsonl(str(train_path), train_rows)
        write_jsonl(str(dev_path), dev_rows)
        print(f"✅ wrote: {train_path} ({len(train_rows)}), {dev_path} ({len(dev_rows)})")

    trainset = load_turn_examples(str(train_path))
    devset = load_turn_examples(str(dev_path))

    program = MIReplyProgram(temperature=0.2)

    # 事前評価
    evaluator = Evaluate(devset=devset, metric=reply_quality_metric, num_threads=1, display_progress=True)
    base_score = evaluator(program)
    print(f"=== baseline score: {base_score}")

    # 最適化（MIPROv2）
    teleprompter = MIPROv2(
        metric=reply_quality_metric,
        auto="light",
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    compiled = teleprompter.compile(student=program.deepcopy(), trainset=trainset, valset=devset)

    # 保存
    save_path = out_dir / "mi_reply.json"
    compiled.save(str(save_path))
    print(f"✅ saved compiled reply program: {save_path}")

    # 事後評価
    new_score = evaluator(compiled)
    print(f"=== compiled score: {new_score}")


if __name__ == "__main__":
    main()
