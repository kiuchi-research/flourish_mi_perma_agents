from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
import site
from typing import Any, Dict, Optional

from app_paths import PROJECT_ROOT, resolve_env_path

SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mi_sim.cli import run_self_play as _run_self_play_package
from mi_sim.cli import run_self_play_batch as _run_self_play_batch_package
from conversation_environment import ConversationEnvironment
from dotenv import load_dotenv
from env_utils import load_openai_api_key
from perma_client_agent import DEFAULT_FIRST_CLIENT_UTTERANCE
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
    action_source = str(debug.get("action_source") or "")
    ranker_debug = debug.get("ranker_debug") or {}
    risk_level = debug.get("risk_level")
    if sampling == "crisis_override":
        return f"危機優先(risk={risk_level})"
    if ranker_debug.get("error"):
        return f"ranker_error={ranker_debug.get('error')}"
    if action_source == "ranker_masked_directive":
        applied = debug.get("ranker_proposal_applied") or debug.get("ranker_directive_main_action") or "-"
        return f"ranker確定採用(mask内:{applied})"
    if action_source in {"allowed_action_mask_fallback", "mask_rule_fallback"}:
        applied = debug.get("ranker_proposal_applied") or "-"
        return f"maskフォールバック({applied})"
    if sampling:
        return f"ルール決定({sampling})"
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


def _format_affirm_status(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"COMPLEX"}:
        return "複雑是認"
    if raw in {"SIMPLE", "TRUE", "1"}:
        return "単純是認"
    return "是認なし"


# ==============================
# conda 環境チェック（人間クライアント CLI 用）
# ==============================

def _find_python_venv_candidates(env_name: str) -> list[Path]:
    """conda が無い場合に使えそうな Python 仮想環境パス候補を列挙する。"""
    name = env_name or "py-dspy"
    cwd = Path.cwd()
    home = Path.home()
    candidates = [
        PROJECT_ROOT / ".venv" / name,
        PROJECT_ROOT / ".venv",
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
    counselor_slot_fill_cfg = counselor_stack.get("slot_fill_cfg", {})
    counselor_action_cfg = counselor_stack["action_cfg"]
    risk_detector_cfg = counselor_stack["risk_cfg"]
    mi_evaluator_cfg = counselor_stack["mi_eval_cfg"]
    session_meta = {
        "session_mode": "human_client",
        "openai_model": counselor_cfg.get("model", ""),
        "reasoning_effort": counselor_cfg.get("reasoning_effort", ""),
        "phase_slot_filler_model": counselor_slot_fill_cfg.get("model", "") if counselor_slot_fill_cfg.get("enabled") else "",
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
        if env.session_meta.get("session_ended"):
            condition = env.session_meta.get("session_end_condition") or {}
            phase_text = condition.get("phase", "")
            phase_intent_text = condition.get("phase_intent_effective", "")
            reason_text = env.session_meta.get("session_end_reason", "session_end_triggered")
            print("セッション終了条件を満たしたため終了します。")
            print(
                f"  理由: {reason_text} "
                f"(phase={phase_text}, phase_intent={phase_intent_text})"
            )
            break
        print("Counselor:", reply)
        counselor_meta = env.log[-1].meta or {}
        debug = counselor_meta.get("debug") or {}
        phase_text = counselor_meta.get("phase", "")
        action_text = counselor_meta.get("main_action", "")
        add_affirm = counselor_meta.get("add_affirm")
        phase_debug = debug.get("phase_debug") or {}
        print("判定結果:")
        print(f"  フェーズ判定: {phase_text} ({_format_phase_debug(phase_debug)})")
        affirm_status = _format_affirm_status(add_affirm)
        print(f"  行動判定: {action_text} ({affirm_status}; {_format_action_debug(debug)})")
        print(f"  応答判定: {_format_evaluation_debug(debug)}")
        print("---")

    finalize_session(env, llm, log_prefix=f"session_{script_name}")


# ==============================
# サブコマンド: 自己対話シミュレーション
# ==============================

def run_agent_dual_simulation(
    *,
    script_name: str = "agent_dual_simulation",
    # 人間カウンセラー側と同じ初期発話生成ロジックに統一
    first_client_utterance: str = DEFAULT_FIRST_CLIENT_UTTERANCE,
    max_turns: int = 15,
    max_turns_completion: str = "phase_to_closing",
    max_total_turns: Optional[int] = None,
    conda_env: Optional[str] = "py-dspy",
    client_style: Optional[str] = None,
    client_code: Optional[str] = None,
    logs_dir: Optional[Path] = None,
    log_prefix: str = "session_simulation",
    artifact_id: Optional[str] = None,
    print_full_log: bool = True,
) -> Dict[str, str]:
    if conda_env:
        check_and_activate_conda_env(conda_env)
    resolved_logs_dir = logs_dir or (Path(__file__).resolve().parent / "logs")
    return _run_self_play_package(
        script_name=script_name,
        first_client_utterance=first_client_utterance,
        max_turns=max_turns,
        max_turns_completion=max_turns_completion,
        max_total_turns=max_total_turns,
        client_style=client_style,
        client_code=client_code,
        logs_dir=resolved_logs_dir,
        log_prefix=log_prefix,
        artifact_id=artifact_id,
        print_full_log=print_full_log,
    )


def run_agent_dual_simulation_batch(
    *,
    script_name: str = "agent_dual_simulation_batch",
    first_client_utterance: str = DEFAULT_FIRST_CLIENT_UTTERANCE,
    max_turns: int = 15,
    max_turns_completion: str = "phase_to_closing",
    max_total_turns: Optional[int] = None,
    conda_env: Optional[str] = "py-dspy",
    client_style: Optional[str] = None,
    logs_dir: Optional[Path] = None,
) -> None:
    if conda_env:
        check_and_activate_conda_env(conda_env)
    resolved_logs_dir = logs_dir or (Path(__file__).resolve().parent / "logs" / "self_play_batch")
    _run_self_play_batch_package(
        script_name=script_name,
        first_client_utterance=first_client_utterance,
        max_turns=max_turns,
        max_turns_completion=max_turns_completion,
        max_total_turns=max_total_turns,
        client_style=client_style,
        logs_dir=resolved_logs_dir,
    )


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
    # app/.env を優先し、未配置なら従来のルート .env も使えるようにする。
    load_dotenv(dotenv_path=resolve_env_path())
    parser = argparse.ArgumentParser(description="MI Bot CLI entrypoint (human-client/self-play/human-counselor)")
    sub = parser.add_subparsers(dest="command", required=True)

    human_client = sub.add_parser("human-client", help="人間クライアント × MIボット")
    human_client.add_argument("--conda-env", default="py-dspy", help="使用する conda 環境名（既定: py-dspy）")

    self_play = sub.add_parser("self-play", help="LLM同士の自己対話シミュレーション")
    self_play.add_argument("--max-turns", type=int, default=5, help="カウンセラー→クライアントのターン数")
    self_play.add_argument(
        "--max-turns-completion",
        choices=["hard_stop", "phase_to_closing"],
        default="phase_to_closing",
        help="max-turns 到達後の終了方式（既定: phase_to_closing）",
    )
    self_play.add_argument(
        "--max-total-turns",
        type=int,
        default=None,
        help="phase_to_closing 時の安全上限（未指定なら max-turns + 7）",
    )
    self_play.add_argument("--conda-env", default="py-dspy", help="使用する conda 環境名（空文字で無効化）")
    self_play.add_argument(
        "--client-style",
        choices=["auto", "cooperative", "ambivalent", "resistant"],
        default=None,
        help="クライアントのペルソナ（既定: auto=プロファイルから推定）。",
    )
    self_play.add_argument(
        "--client-code",
        default=None,
        help="単発実行する CLIENT_CODE。'all' で15ケース一括実行。",
    )
    self_play.add_argument(
        "--all-cases",
        action="store_true",
        help="LANG|SOCIAL|UNSOCIAL × MGR|LOWINC|ISO|STABLE|MOB の15ケースを順次実行し、既存成果物は自動スキップ。",
    )
    self_play.add_argument(
        "--logs-dir",
        default=None,
        help="ログ出力先。--all-cases 時はこの配下に設定別サブディレクトリを作成。",
    )

    human_counselor = sub.add_parser("human-counselor", help="人間カウンセラー × LLMクライアント（自動ラベル付け）")
    human_counselor.add_argument("--conda-env", default="py-dspy", help="使用する conda 環境名（空文字で無効化）")

    args = parser.parse_args()

    if args.command == "human-client":
        run_human_client_counselor_cli(conda_env=args.conda_env)
    elif args.command == "self-play":
        logs_dir = Path(args.logs_dir).expanduser() if args.logs_dir else None
        run_all_cases = bool(args.all_cases) or str(args.client_code or "").strip().lower() == "all"
        if run_all_cases:
            run_agent_dual_simulation_batch(
                max_turns=args.max_turns,
                max_turns_completion=args.max_turns_completion,
                max_total_turns=args.max_total_turns,
                conda_env=args.conda_env,
                client_style=args.client_style,
                logs_dir=logs_dir,
            )
        else:
            run_agent_dual_simulation(
                max_turns=args.max_turns,
                max_turns_completion=args.max_turns_completion,
                max_total_turns=args.max_total_turns,
                conda_env=args.conda_env,
                client_style=args.client_style,
                client_code=args.client_code,
                logs_dir=logs_dir,
            )
    elif args.command == "human-counselor":
        run_human_counselor_client_cli(conda_env=args.conda_env)
    else:
        parser.error("unknown command")


if __name__ == "__main__":
    main()
