from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import asdict
from typing import Any, Dict, Optional

from conversation_environment import ConversationEnvironment, ConversationTurn
from env_utils import build_llm_from_config, get_model_config, load_openai_api_key
from mi_counselor_agent import LLMActionRanker, LLMPhaseClassifier, MIRhythmBot
from perma_client_agent import SimpleClientLLM
from session_log_tools import finalize_session


# ==============================
# LLM ラッパー（Chat Completions）
# ==============================


def _build_optional_phase_classifier(api_key: str, cfg: Dict[str, Any]) -> Optional[LLMPhaseClassifier]:
    """enabled が真のときだけ LLMPhaseClassifier を生成する。"""
    if not cfg:
        return None
    if cfg.get("enabled") is False:
        return None
    llm = build_llm_from_config(cfg, api_key)
    return LLMPhaseClassifier(llm=llm, temperature=0.0, max_history_turns=8)


def _build_optional_action_ranker(api_key: str, cfg: Dict[str, Any]) -> Optional[LLMActionRanker]:
    """enabled が真のときだけ LLMActionRanker を生成する。"""
    if not cfg:
        return None
    if cfg.get("enabled") is False:
        return None
    llm = build_llm_from_config(cfg, api_key)
    return LLMActionRanker(llm=llm)


# ==============================
# conda 環境チェック（人間クライアント CLI 用）
# ==============================

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
            return False
        print("⚠️  警告: conda環境のアクティベートに失敗しました。")
        print(f"   手動で 'conda activate {env_name}' を実行してください。")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: condaコマンドの実行に失敗しました: {e}")
        return False
    except FileNotFoundError:
        print("❌ エラー: condaがインストールされていません。")
        return False


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
    counselor_cfg = get_model_config(
        "human_client_counselor",
        role="counselor",
    )
    counselor_phase_cfg = get_model_config(
        "counselor_phase_classifier",
        role="counselor",
        fallback_modes=["human_client_counselor"],
    )
    counselor_action_cfg = get_model_config(
        "counselor_action_ranker",
        role="counselor",
        fallback_modes=["human_client_counselor"],
    )
    llm = build_llm_from_config(counselor_cfg, api_key)
    phase_classifier = _build_optional_phase_classifier(api_key, counselor_phase_cfg)
    action_ranker = _build_optional_action_ranker(api_key, counselor_action_cfg)
    counselor = MIRhythmBot(llm=llm, phase_classifier=phase_classifier, action_ranker=action_ranker)
    session_meta = {
        "session_mode": "human_client",
        "openai_model": counselor_cfg.get("model", ""),
        "phase_classifier_model": counselor_phase_cfg.get("model", "") if counselor_phase_cfg.get("enabled") else "",
        "action_ranker_model": counselor_action_cfg.get("model", "") if counselor_action_cfg.get("enabled") else "",
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
    first_client_utterance: str = "最近、生活リズムが崩れてしまって、気持ちも落ち込んでいます。",
    max_turns: int = 5,
    conda_env: Optional[str] = "py-dspy",
) -> None:
    if conda_env:
        check_and_activate_conda_env(conda_env)
    api_key = load_openai_api_key()
    counselor_cfg = get_model_config(
        "self_play_counselor",
        role="counselor",
        fallback_modes=["human_client_counselor"],
    )
    counselor_phase_cfg = get_model_config(
        "counselor_phase_classifier",
        role="counselor",
        fallback_modes=["self_play_counselor", "human_client_counselor"],
    )
    counselor_action_cfg = get_model_config(
        "counselor_action_ranker",
        role="counselor",
        fallback_modes=["self_play_counselor", "human_client_counselor"],
    )
    client_cfg = get_model_config("self_play_client", role="client", fallback_modes=["human_counselor_client"])
    client_state_cfg = get_model_config(
        "self_play_client_state",
        role="client",
        fallback_modes=["self_play_client", "human_counselor_client_state", "human_counselor_client"],
    )
    client_reply_cfg = get_model_config(
        "self_play_client_reply",
        role="client",
        fallback_modes=["self_play_client", "human_counselor_client_reply", "human_counselor_client"],
    )
    client_style = os.getenv("CLIENT_STYLE", "cooperative")
    counselor_llm = build_llm_from_config(counselor_cfg, api_key)
    client_llm_state = build_llm_from_config(client_state_cfg, api_key)
    client_llm_reply = build_llm_from_config(client_reply_cfg, api_key)
    phase_classifier = _build_optional_phase_classifier(api_key, counselor_phase_cfg)
    action_ranker = _build_optional_action_ranker(api_key, counselor_action_cfg)

    counselor = MIRhythmBot(llm=counselor_llm, phase_classifier=phase_classifier, action_ranker=action_ranker)
    client = SimpleClientLLM(
        llm=client_llm_reply,
        llm_state=client_llm_state,
        llm_reply=client_llm_reply,
        style=client_style,
    )
    session_meta = {
        "session_mode": "self_play",
        "openai_model": counselor_cfg.get("model", ""),
        "script_name": script_name,
        "client_style": client_style,
        "client_model_state": client_state_cfg.get("model", ""),
        "client_model_reply": client_reply_cfg.get("model", ""),
        "phase_classifier_model": counselor_phase_cfg.get("model", "") if counselor_phase_cfg.get("enabled") else "",
        "action_ranker_model": counselor_action_cfg.get("model", "") if counselor_action_cfg.get("enabled") else "",
        "planner_config": asdict(counselor.cfg),
    }
    env = ConversationEnvironment(counselor=counselor, client=client, session_meta=session_meta)
    env.reset()

    print("自己対話シミュレーションを開始します...")
    env.simulate(first_client_utterance=first_client_utterance, max_turns=max_turns, progress=True)
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
