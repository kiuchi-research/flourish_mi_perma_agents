# B: フェーズ判定／CT・抵抗推定を最適化

from __future__ import annotations

import os
from pathlib import Path

import dspy
from dspy.evaluate import Evaluate
from dspy.teleprompt import MIPROv2

from mi_counselor_dspy import configure_dspy_lm
from mi_dspy_data import (
    build_B_phase_rows_from_logs,
    build_B_ctr_rows_from_logs,
    split_train_dev,
    write_jsonl,
    load_phase_examples,
    load_ctr_examples,
)
from mi_dspy_metrics import phase_accuracy_metric, ctr_regression_metric
from mi_dspy_programs import MIPhaseProgram, MIChangeTalkResistanceProgram


def _compile_one(name: str, program: dspy.Module, trainset, devset, metric, save_path: Path):
    evaluator = Evaluate(devset=devset, metric=metric, num_threads=1, display_progress=True)
    base = evaluator(program)
    print(f"=== [{name}] baseline: {base}")

    tele = MIPROv2(metric=metric, auto="light", max_bootstrapped_demos=4, max_labeled_demos=8)
    compiled = tele.compile(student=program.deepcopy(), trainset=trainset, valset=devset)

    compiled.save(str(save_path))
    print(f"✅ saved: {save_path}")

    new = evaluator(compiled)
    print(f"=== [{name}] compiled: {new}")


def main():
    configure_dspy_lm(os.getenv("DSPY_MODEL", "openai/gpt-4o-mini"))

    data_dir = Path("data")
    out_dir = Path("compiled")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- phase dataset
    phase_train = data_dir / "b_phase_train.jsonl"
    phase_dev = data_dir / "b_phase_dev.jsonl"
    if (not phase_train.exists()) or (not phase_dev.exists()):
        rows = build_B_phase_rows_from_logs("logs")
        if not rows:
            raise RuntimeError("logs/*.csv が見つかりません。先にログを作ってください。")
        tr, dv = split_train_dev(rows, dev_ratio=0.2)
        write_jsonl(str(phase_train), tr)
        write_jsonl(str(phase_dev), dv)
        print(f"✅ wrote: {phase_train} ({len(tr)}), {phase_dev} ({len(dv)})")

    # ---- ctr dataset
    ctr_train = data_dir / "b_ctr_train.jsonl"
    ctr_dev = data_dir / "b_ctr_dev.jsonl"
    if (not ctr_train.exists()) or (not ctr_dev.exists()):
        rows = build_B_ctr_rows_from_logs("logs")
        if not rows:
            raise RuntimeError("features_json が入った logs/*.csv が見つかりません。")
        tr, dv = split_train_dev(rows, dev_ratio=0.2)
        write_jsonl(str(ctr_train), tr)
        write_jsonl(str(ctr_dev), dv)
        print(f"✅ wrote: {ctr_train} ({len(tr)}), {ctr_dev} ({len(dv)})")

    # ---- compile phase
    phase_trainset = load_phase_examples(str(phase_train))
    phase_devset = load_phase_examples(str(phase_dev))
    phase_prog = MIPhaseProgram(temperature=0.0)
    _compile_one("phase", phase_prog, phase_trainset, phase_devset, phase_accuracy_metric, out_dir / "mi_phase.json")

    # ---- compile ctr
    ctr_trainset = load_ctr_examples(str(ctr_train))
    ctr_devset = load_ctr_examples(str(ctr_dev))
    ctr_prog = MIChangeTalkResistanceProgram(temperature=0.0)
    _compile_one("ctr", ctr_prog, ctr_trainset, ctr_devset, ctr_regression_metric, out_dir / "mi_ctr.json")


if __name__ == "__main__":
    main()
