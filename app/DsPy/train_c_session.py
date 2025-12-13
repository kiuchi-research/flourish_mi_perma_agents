# C: セッション全体を丸ごと最適化

from __future__ import annotations

import os
from pathlib import Path

from dspy.evaluate import Evaluate
from dspy.teleprompt import MIPROv2

from mi_counselor_dspy import configure_dspy_lm
from mi_dspy_data import (
    build_C_session_rows_from_logs,
    split_train_dev,
    write_jsonl,
    load_session_examples,
)
from mi_dspy_metrics import session_score_metric
from mi_dspy_programs import MISessionDriverProgram
from mi_counselor_agent import PlannerConfig


def main():
    configure_dspy_lm(os.getenv("DSPY_MODEL", "openai/gpt-4o-mini"))

    data_dir = Path("data")
    out_dir = Path("compiled")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_path = data_dir / "c_session_train.jsonl"
    dev_path = data_dir / "c_session_dev.jsonl"

    if (not train_path.exists()) or (not dev_path.exists()):
        rows = build_C_session_rows_from_logs("logs")
        if not rows:
            raise RuntimeError("logs/*.csv が見つかりません。先にログを作ってください。")
        tr, dv = split_train_dev(rows, dev_ratio=0.2)
        write_jsonl(str(train_path), tr)
        write_jsonl(str(dev_path), dv)
        print(f"✅ wrote: {train_path} ({len(tr)}), {dev_path} ({len(dv)})")

    trainset = load_session_examples(str(train_path))
    devset = load_session_examples(str(dev_path))

    # セッション評価は deterministic 推奨（stochastic=False）
    cfg = PlannerConfig(stochastic=False)

    # Cでは「行動ランキング＋生成」を最適化対象にする
    program = MISessionDriverProgram(
        cfg=cfg,
        use_phase_program=True,
        use_ctr_program=True,
        use_action_ranker=True,
    )

    evaluator = Evaluate(devset=devset, metric=session_score_metric, num_threads=1, display_progress=True)
    base = evaluator(program)
    print(f"=== baseline session score: {base}")

    tele = MIPROv2(
        metric=session_score_metric,
        auto="light",
        max_bootstrapped_demos=4,
        max_labeled_demos=0,  # セッションは教師ラベルがないことが多いので基本0でOK
    )
    compiled = tele.compile(student=program.deepcopy(), trainset=trainset, valset=devset)

    save_path = out_dir / "mi_session_driver.json"
    compiled.save(str(save_path))
    print(f"✅ saved compiled session driver: {save_path}")

    new = evaluator(compiled)
    print(f"=== compiled session score: {new}")


if __name__ == "__main__":
    main()
