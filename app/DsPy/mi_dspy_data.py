from __future__ import annotations

"""
DSPy 用データセット（JSONL）を扱うユーティリティ

- logs/*.csv（save_log_csv の形式）から A/B/C 用の JSONL を作れるようにする
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import dspy


# ----------------------------
# JSONL I/O
# ----------------------------
def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            json.dump(r, f, ensure_ascii=False)
            f.write("\n")


# ----------------------------
# DSPy Example loader（A/B/C）
# ----------------------------
def load_turn_examples(jsonl_path: str) -> List[dspy.Example]:
    """
    A用（発話生成）:
      dialogue, phase, main_action, add_affirm, (optional) reply
    """
    rows = read_jsonl(jsonl_path)
    out: List[dspy.Example] = []
    for r in rows:
        ex = dspy.Example(
            dialogue=r["dialogue"],
            phase=r["phase"],
            main_action=r["main_action"],
            add_affirm=bool(r.get("add_affirm", False)),
        )
        # ラベル（任意）
        if "reply" in r and r["reply"]:
            ex.reply = r["reply"]
        ex = ex.with_inputs("dialogue", "phase", "main_action", "add_affirm")
        out.append(ex)
    return out


def load_phase_examples(jsonl_path: str) -> List[dspy.Example]:
    """
    B用（フェーズ分類）:
      user_text, current_phase, phase
    """
    rows = read_jsonl(jsonl_path)
    out: List[dspy.Example] = []
    for r in rows:
        ex = dspy.Example(
            user_text=r["user_text"],
            current_phase=r["current_phase"],
            phase=r["phase"],
        ).with_inputs("user_text", "current_phase")
        out.append(ex)
    return out


def load_ctr_examples(jsonl_path: str) -> List[dspy.Example]:
    """
    B用（change_talk/resistance 推定）:
      user_text, last_user_text, change_talk, resistance
    """
    rows = read_jsonl(jsonl_path)
    out: List[dspy.Example] = []
    for r in rows:
        ex = dspy.Example(
            user_text=r["user_text"],
            last_user_text=r.get("last_user_text", ""),
            change_talk=float(r.get("change_talk", 0.0)),
            resistance=float(r.get("resistance", 0.0)),
        ).with_inputs("user_text", "last_user_text")
        out.append(ex)
    return out


def load_session_examples(jsonl_path: str) -> List[dspy.Example]:
    """
    C用（セッション台本）:
      client_script: List[str]
    """
    rows = read_jsonl(jsonl_path)
    out: List[dspy.Example] = []
    for r in rows:
        ex = dspy.Example(client_script=list(r["client_script"])).with_inputs("client_script")
        out.append(ex)
    return out


# ----------------------------
# logs/*.csv からデータを作る
# ----------------------------
def _read_log_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _history_to_dialogue_from_lines(lines: List[str], max_lines: int = 40) -> str:
    return "\n".join(lines[-max_lines:])


def build_A_turn_rows_from_logs(logs_dir: str = "logs") -> List[Dict[str, Any]]:
    """
    A用（発話生成）: 各 counselor ターンを 1例にする。
    - input: dialogue, phase, main_action, add_affirm
    - label(optional): reply（実際の counselor 発話）
    """
    logs = sorted(Path(logs_dir).glob("*.csv"))
    rows_out: List[Dict[str, Any]] = []

    for fp in logs:
        data = _read_log_csv(fp)
        dialogue_lines: List[str] = []
        for row in data:
            speaker = (row.get("speaker") or "").strip()
            text = (row.get("text") or "").strip()
            if not text:
                continue

            if speaker == "client":
                dialogue_lines.append(f"Client: {text}")
                continue

            if speaker == "counselor":
                # この時点で dialogue_lines の末尾は（通常）直前 client
                phase = (row.get("phase") or "").strip()
                main_action = (row.get("main_action") or "").strip()
                add_affirm_raw = row.get("add_affirm")
                add_affirm = str(add_affirm_raw).lower() in ("true", "1", "yes")

                dialogue = _history_to_dialogue_from_lines(dialogue_lines, max_lines=40)
                rows_out.append(
                    {
                        "dialogue": dialogue,
                        "phase": phase,
                        "main_action": main_action,
                        "add_affirm": add_affirm,
                        "reply": text,
                        "source_log": fp.name,
                    }
                )
                dialogue_lines.append(f"Counselor: {text}")

    return rows_out


def build_B_phase_rows_from_logs(logs_dir: str = "logs") -> List[Dict[str, Any]]:
    """
    B用（フェーズ分類）: counselor ターンの phase をラベルとして使う（弱教師）。
    input: user_text, current_phase（前ターンの phase）, label: phase
    """
    logs = sorted(Path(logs_dir).glob("*.csv"))
    rows_out: List[Dict[str, Any]] = []

    for fp in logs:
        data = _read_log_csv(fp)
        prev_phase = "問題特定"
        last_client_text = ""

        for row in data:
            speaker = (row.get("speaker") or "").strip()
            text = (row.get("text") or "").strip()

            if speaker == "client":
                last_client_text = text
                continue

            if speaker == "counselor":
                phase = (row.get("phase") or "").strip()
                if not last_client_text or not phase:
                    prev_phase = phase or prev_phase
                    continue

                rows_out.append(
                    {
                        "user_text": last_client_text,
                        "current_phase": prev_phase or "問題特定",
                        "phase": phase,
                        "source_log": fp.name,
                    }
                )
                prev_phase = phase or prev_phase

    return rows_out


def build_B_ctr_rows_from_logs(logs_dir: str = "logs") -> List[Dict[str, Any]]:
    """
    B用（change_talk/resistance）: features_json をラベルとして使う（弱教師）。
    input: user_text, last_user_text, label: change_talk, resistance
    """
    logs = sorted(Path(logs_dir).glob("*.csv"))
    rows_out: List[Dict[str, Any]] = []

    for fp in logs:
        data = _read_log_csv(fp)
        last_client_text = ""
        prev_client_text = ""

        for row in data:
            speaker = (row.get("speaker") or "").strip()
            text = (row.get("text") or "").strip()

            if speaker == "client":
                prev_client_text = last_client_text
                last_client_text = text
                continue

            if speaker == "counselor":
                feats_json = (row.get("features_json") or "").strip()
                if not last_client_text or not feats_json:
                    continue
                try:
                    feats = json.loads(feats_json)
                except Exception:
                    continue

                ct = feats.get("change_talk", 0.0)
                rs = feats.get("resistance", 0.0)

                try:
                    ct = float(ct)
                    rs = float(rs)
                except Exception:
                    continue

                rows_out.append(
                    {
                        "user_text": last_client_text,
                        "last_user_text": prev_client_text,
                        "change_talk": ct,
                        "resistance": rs,
                        "source_log": fp.name,
                    }
                )

    return rows_out


def build_C_session_rows_from_logs(logs_dir: str = "logs") -> List[Dict[str, Any]]:
    """
    C用（固定台本セッション）: 各ログファイルの client 発話列を 1セッションとして使う。
    """
    logs = sorted(Path(logs_dir).glob("*.csv"))
    rows_out: List[Dict[str, Any]] = []

    for fp in logs:
        data = _read_log_csv(fp)
        client_utts: List[str] = []
        for row in data:
            if (row.get("speaker") or "").strip() == "client":
                t = (row.get("text") or "").strip()
                if t:
                    client_utts.append(t)

        if client_utts:
            rows_out.append({"client_script": client_utts, "source_log": fp.name})

    return rows_out


# ----------------------------
# 簡易 split（train/dev）
# ----------------------------
def split_train_dev(rows: List[Dict[str, Any]], dev_ratio: float = 0.2) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not rows:
        return [], []
    n = len(rows)
    n_dev = max(1, int(n * dev_ratio)) if n >= 5 else max(1, min(2, n))
    dev = rows[:n_dev]
    train = rows[n_dev:]
    return train, dev
