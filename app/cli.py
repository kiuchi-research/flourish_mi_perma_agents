from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
import site
from typing import Any, Dict, Optional

from conversation_environment import ConversationEnvironment, ConversationTurn
from env_utils import load_openai_api_key
from perma_client_agent import DEFAULT_FIRST_CLIENT_UTTERANCE, SimpleClientLLM
from client_llm_loader import build_client_llms
from session_log_tools import finalize_session
from counselor_llm_loader import build_counselor_stack


# ==============================
# LLM ラッパー（Chat Completions）
# ==============================
def _format_phase_debug(debug: Dict[str, Any]) -> str:
    """フェーズ判定の簡易要約を作る。"""
    method = debug.get("method") or "rule"
    confidence = debug.get("confidence")
    fallback = debug.get("fallback_phase")
    parts = [f"method={method}"]
    try:
        if confidence is not None:
            parts.append(f"conf={float(confidence):.2f}")
    except (TypeError, ValueError):
        pass
    if fallback:
        parts.append(f"fallback={fallback}")
    return " / ".join(parts)


def _format_action_debug(debug: Dict[str, Any]) -> str:
    """主動作選択の簡易要約を作る。"""
    sampling = debug.get("sampling")
    llm_bias = debug.get("llm_rank_bias") or []
    ranker_debug = debug.get("ranker_debug") or {}
    risk_level = debug.get("risk_level")
    if sampling == "crisis_override":
        return f"危機優先(risk={risk_level})"
    if ranker_debug.get("error"):
        return f"ranker_error={ranker_debug.get('error')}"
    if sampling in ("argmax", "stochastic"):
        bias = ", ".join(llm_bias) if llm_bias else "-"
        bias_part = f"LLMバイアス={bias}" if llm_bias else "LLMバイアスなし"
        return f"ルール決定({sampling}; {bias_part})"
    return sampling or "rule"


def _format_evaluation_debug(debug: Dict[str, Any]) -> str:
    """応答評価（MI準拠スコアなど）がある場合の要約を作る。"""
    evaluation = debug.get("evaluation") or {}
    if not evaluation:
        return "評価器なし"
    score = evaluation.get("score")
    feedback = evaluation.get("feedback")
    parts = []
    try:
        if score is not None:
            parts.append(f"score={float(score):.2f}")
    except (TypeError, ValueError):
        parts.append(f"score={score}")
    if feedback:
        trimmed = str(feedback)
        if len(trimmed) > 120:
            trimmed = trimmed[:117] + "..."
        parts.append(f"feedback={trimmed}")
    return " / ".join(parts) if parts else "評価情報なし"


# ==============================
# conda 環境チェック（人間クライアント CLI 用）
# ==============================

def _find_python_venv_candidates(env_name: str) -> list[Path]:
    """conda が無い場合に使えそうな Python 仮想環境パス候補を列挙する。"""
    name = env_name or "py-dspy"
    root = Path(__file__).resolve().parent.parent
    cwd = Path.cwd()
    home = Path.home()
    candidates = [
        root / ".venv" / name,
        root / ".venv",
        cwd / ".venv" / name,
        cwd / ".venv",
        home / ".venv" / name,
        home / "venv" / name,
    ]
    seen = set()
    found: list[Path] = []
    for p in candidates:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        bin_dir = p / ("Scripts" if os.name == "nt" else "bin")
        python_bin = bin_dir / ("python.exe" if os.name == "nt" else "python")
        if python_bin.exists():
            found.append(p)
    return found


def _detect_site_packages(venv_path: Path) -> Optional[Path]:
    """仮想環境配下の site-packages を推定する（Unix/Windows 両対応）。"""
    lib_dir = venv_path / "lib"
    if lib_dir.is_dir():
        for child in sorted(lib_dir.iterdir()):
            if child.is_dir() and child.name.startswith("python"):
                sp = child / "site-packages"
                if sp.is_dir():
                    return sp
    win_sp = venv_path / "Lib" / "site-packages"
    if win_sp.is_dir():
        return win_sp
    return None


def _activate_python_venv(venv_path: Path) -> bool:
    """
    conda が無い場合のフォールバックとして、Python 仮想環境を「擬似アクティベート」する。
    - PATH 先頭に venv/bin を追加
    - VIRTUAL_ENV をセット
    - site-packages を sys.path に追加
    """
    try:
        bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
        python_bin = bin_dir / ("python.exe" if os.name == "nt" else "python")
        if not python_bin.exists():
            return False

        site_packages = _detect_site_packages(venv_path)
        if site_packages and site_packages.exists():
            site.addsitedir(str(site_packages))

        os.environ["VIRTUAL_ENV"] = str(venv_path)
        old_path = os.environ.get("PATH", "")
        if str(bin_dir) not in old_path.split(os.pathsep):
            os.environ["PATH"] = str(bin_dir) + os.pathsep + old_path

        print(
            f"✅ conda環境が見つからなかったため、Python仮想環境 '{venv_path}' を利用するように設定しました。"
        )
        return True
    except Exception as e:
        print(f"⚠️  Python仮想環境の設定に失敗しました: {e}")
        return False


def _maybe_activate_python_venv(env_name: str) -> bool:
    """conda が使えない場合に、同名の Python venv を探して設定する。"""
    candidates = _find_python_venv_candidates(env_name)
    for p in candidates:
        if _activate_python_venv(p):
            return True
    if candidates:
        print("⚠️  Python仮想環境は見つかったものの、設定に失敗しました。")
    else:
        print("⚠️  conda 環境と Python 仮想環境（.venv）どちらも見つかりませんでした。")
        print("   必要なら '--conda-env \"\"' でチェックをスキップし、手動で環境を有効化してください。")
    return False


def activate_conda_env(env_name: str = "py-dspy") -> bool:
    """conda 環境をアクティベートする（失敗しても続行）。"""
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if current_env == env_name:
        print(f"✅ conda環境 '{env_name}' は既にアクティブです。")
        return True

    print(f"🔄 conda環境 '{env_name}' をアクティベート中...")
    try:
        result = subprocess.run(
            ["conda", "shell.bash", "hook"],
            capture_output=True,
            text=True,
            check=True,
        )
        activate_cmd = f"source <(conda shell.bash hook) && conda activate {env_name}"
        result = subprocess.run(
            activate_cmd,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            env_list_result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
            if env_name in env_list_result.stdout:
                print(f"✅ conda環境 '{env_name}' のアクティベートを試みました。")
                print(
                    f"⚠️  注意: 完全なアクティベートには、シェルから "
                    f"'conda activate {env_name}' を実行してください。"
                )
                return True
            print(f"❌ エラー: conda環境 '{env_name}' が見つかりません。")
            return _maybe_activate_python_venv(env_name)
        print("⚠️  警告: conda環境のアクティベートに失敗しました。")
        print(f"   手動で 'conda activate {env_name}' を実行してください。")
        return _maybe_activate_python_venv(env_name)
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: condaコマンドの実行に失敗しました: {e}")
        return _maybe_activate_python_venv(env_name)
    except FileNotFoundError:
        print("❌ エラー: condaがインストールされていません。")
        return _maybe_activate_python_venv(env_name)


def check_and_activate_conda_env(env_name: str = "py-dspy") -> None:
    """現在の環境を確認し、必要ならアクティベートを試みる。"""
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if current_env != env_name:
        print(f"⚠️  警告: 現在のconda環境は '{current_env}' です。推奨: '{env_name}'")
        if not activate_conda_env(env_name):
            print(
                f"\n⚠️  自動アクティベートに失敗しましたが続行します。"
                f"\n   問題が出た場合は 'conda activate {env_name}' を実行してください。\n"
            )


# ==============================
# サブコマンド: 人間クライアント × MI ボット
# ==============================

def run_human_client_counselor_cli(
    *,
    script_name: str = "human_client_counselor_cli",
    conda_env: str = "py-dspy",
) -> None:
    check_and_activate_conda_env(conda_env)

    api_key = load_openai_api_key()
    counselor_mode = os.getenv("COUNSELOR_MODE", "counselor_llm")
    counselor_stack = build_counselor_stack(api_key=api_key)
    counselor = counselor_stack["counselor"]
    llm = counselor_stack["llm"]
    counselor_cfg = counselor_stack["counselor_cfg"]
    counselor_phase_cfg = counselor_stack["phase_cfg"]
    counselor_action_cfg = counselor_stack["action_cfg"]
    risk_detector_cfg = counselor_stack["risk_cfg"]
    mi_evaluator_cfg = counselor_stack["mi_eval_cfg"]
    counselor.phase_confidence_threshold = 0.3
    session_meta = {
        "session_mode": "human_client",
        "openai_model": counselor_cfg.get("model", ""),
        "phase_classifier_model": counselor_phase_cfg.get("model", "") if counselor_phase_cfg.get("enabled") else "",
        "action_ranker_model": counselor_action_cfg.get("model", "") if counselor_action_cfg.get("enabled") else "",
        "risk_detector_model": risk_detector_cfg.get("model", "") if risk_detector_cfg.get("enabled") else "",
        "mi_evaluator_model": mi_evaluator_cfg.get("model", "") if mi_evaluator_cfg.get("enabled") else "",
        "counselor_mode": counselor_mode,
        "script_name": script_name,
        "planner_config": asdict(counselor.cfg),
    }
    env = ConversationEnvironment(counselor=counselor, session_meta=session_meta)

    print("MIボットとの対話を始めます。'exit' で終了します。")

    while True:
        try:
            user_text = input("Client: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n入力が閉じられたため終了します。")
            break

        if user_text.lower() == "exit":
            break

        reply = env.step_with_human(user_text)
        print("Counselor:", reply)
        counselor_meta = env.log[-1].meta or {}
        debug = counselor_meta.get("debug") or {}
        phase_text = counselor_meta.get("phase", "")
        action_text = counselor_meta.get("main_action", "")
        add_affirm = counselor_meta.get("add_affirm")
        phase_debug = debug.get("phase_debug") or {}
        print("判定結果:")
        print(f"  フェーズ判定: {phase_text} ({_format_phase_debug(phase_debug)})")
        affirm_status = "是認あり" if add_affirm else "是認なし"
        print(f"  行動判定: {action_text} ({affirm_status}; {_format_action_debug(debug)})")
        print(f"  応答判定: {_format_evaluation_debug(debug)}")
        print("---")

    finalize_session(env, llm, log_prefix=f"session_{script_name}")


# ==============================
# サブコマンド: 自己対話シミュレーション
# ==============================

def _print_simulation_log(log: List[ConversationTurn]) -> None:
    for idx, turn in enumerate(log):
        prefix = "C" if turn.speaker == "client" else "T"
        print(f"[{idx:02d}] {prefix}: {turn.text}")
        if turn.meta and turn.speaker == "counselor":
            phase = turn.meta.get("phase")
            action = turn.meta.get("main_action")
            print(f"      meta: phase={phase}, action={action}")


def run_agent_dual_simulation(
    *,
    script_name: str = "agent_dual_simulation",
    # 人間カウンセラー側と同じ初期発話生成ロジックに統一
    first_client_utterance: str = DEFAULT_FIRST_CLIENT_UTTERANCE,
    max_turns: int = 5,
    conda_env: Optional[str] = "py-dspy",
) -> None:
    if conda_env:
        check_and_activate_conda_env(conda_env)
    api_key = load_openai_api_key()
    counselor_mode = os.getenv("COUNSELOR_MODE", "counselor_llm")
    counselor_stack = build_counselor_stack(api_key=api_key)
    counselor = counselor_stack["counselor"]
    counselor_llm = counselor_stack["llm"]
    counselor_cfg = counselor_stack["counselor_cfg"]
    counselor_phase_cfg = counselor_stack["phase_cfg"]
    counselor_action_cfg = counselor_stack["action_cfg"]
    risk_detector_cfg = counselor_stack["risk_cfg"]
    mi_evaluator_cfg = counselor_stack["mi_eval_cfg"]
    client_llms = build_client_llms(api_key=api_key)
    client_cfg = client_llms["client_cfg"]
    client_state_cfg = client_llms["client_state_cfg"]
    client_reply_cfg = client_llms["client_reply_cfg"]
    client_llm_state = client_llms["client_llm_state"]
    client_llm_reply = client_llms["client_llm_reply"]
    counselor.phase_confidence_threshold = 0.3
    client_code = (os.getenv("CLIENT_CODE") or "C01").strip() or "C01"
    client, client_bundle = SimpleClientLLM.from_profile(
        client_code=client_code,
        llm=client_llm_reply,
        llm_state=client_llm_state,
        llm_reply=client_llm_reply,
        env_style=os.getenv("CLIENT_STYLE", "auto"),
        first_client_utterance_env=os.getenv("FIRST_CLIENT_UTTERANCE"),
        max_state_step_env=os.getenv("CLIENT_MAX_STATE_STEP", "none"),
        default_first_utterance=first_client_utterance,
    )
    session_meta = {
        "session_mode": "self_play",
        "openai_model": counselor_cfg.get("model", ""),
        "script_name": script_name,
        "client_style": client_bundle.style,
        "client_code": client_code,
        "client_pattern": client_bundle.derived_meta.get("pattern_code", ""),
        "client_pattern_label": client_bundle.derived_meta.get("pattern_label", ""),
        "client_primary_focus": client_bundle.derived_meta.get("primary_focus_code", ""),
        "client_primary_focus_label": client_bundle.derived_meta.get("primary_focus_label", ""),
        "client_interpersonal_style": client_bundle.derived_meta.get("interpersonal_style_code", ""),
        "client_interpersonal_style_label": client_bundle.derived_meta.get("interpersonal_style_label", ""),
        "client_profiles_path": str(client_bundle.profiles_path),
        "client_model_state": client_state_cfg.get("model", ""),
        "client_model_reply": client_reply_cfg.get("model", ""),
        "phase_classifier_model": counselor_phase_cfg.get("model", "") if counselor_phase_cfg.get("enabled") else "",
        "action_ranker_model": counselor_action_cfg.get("model", "") if counselor_action_cfg.get("enabled") else "",
        "risk_detector_model": risk_detector_cfg.get("model", "") if risk_detector_cfg.get("enabled") else "",
        "mi_evaluator_model": mi_evaluator_cfg.get("model", "") if mi_evaluator_cfg.get("enabled") else "",
        "counselor_mode": counselor_mode,
        "planner_config": asdict(counselor.cfg),
    }
    env = ConversationEnvironment(counselor=counselor, client=client, session_meta=session_meta)
    env.reset()

    print("自己対話シミュレーションを開始します...")
    env.simulate(
        first_client_utterance=client_bundle.first_utterance,
        max_turns=max_turns,
        progress=True,
    )
    print("シミュレーション完了。ログを出力します。")

    print("\n==== SIMULATION LOG ====")
    _print_simulation_log(env.log)
    finalize_session(env, counselor_llm, log_prefix="session_simulation")


# ==============================
# サブコマンド: 人間カウンセラー × LLMクライアント
# ==============================

def run_human_counselor_client_cli(
    *,
    script_name: str = "human_counselor_client_cli",
    conda_env: Optional[str] = "py-dspy",
) -> None:
    # 実装本体は cli_human_counselor_client.py へ移設
    from cli_human_counselor_client import main as _human_counselor_main

    if conda_env:
        check_and_activate_conda_env(conda_env)

    log_prefix = f"session_{script_name}"
    _human_counselor_main(script_name=script_name, log_prefix=log_prefix)


# ==============================
# エントリーポイント
# ==============================

def main() -> None:
    parser = argparse.ArgumentParser(description="MI Bot CLI entrypoint (human-client/self-play/human-counselor)")
    sub = parser.add_subparsers(dest="command", required=True)

    human_client = sub.add_parser("human-client", help="人間クライアント × MIボット")
    human_client.add_argument("--conda-env", default="py-dspy", help="使用する conda 環境名（既定: py-dspy）")

    self_play = sub.add_parser("self-play", help="LLM同士の自己対話シミュレーション")
    self_play.add_argument("--max-turns", type=int, default=5, help="カウンセラー→クライアントのターン数")
    self_play.add_argument("--conda-env", default="py-dspy", help="使用する conda 環境名（空文字で無効化）")

    human_counselor = sub.add_parser("human-counselor", help="人間カウンセラー × LLMクライアント（自動ラベル付け）")
    human_counselor.add_argument("--conda-env", default="py-dspy", help="使用する conda 環境名（空文字で無効化）")

    args = parser.parse_args()

    if args.command == "human-client":
        run_human_client_counselor_cli(conda_env=args.conda_env)
    elif args.command == "self-play":
        run_agent_dual_simulation(max_turns=args.max_turns, conda_env=args.conda_env)
    elif args.command == "human-counselor":
        run_human_counselor_client_cli(conda_env=args.conda_env)
    else:
        parser.error("unknown command")


if __name__ == "__main__":
    main()
