import os
import sys
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from openai import OpenAI

from mi_rhythm_bot import MIRhythmBot, LLMClient
from mi_environment import ConversationEnvironment


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
        # content が分割テキストの場合のフォールバック
        try:
            return "".join(getattr(part, "text", "") for part in content or [])
        except Exception:
            return ""


def activate_conda_env(env_name: str = "py-dspy") -> bool:
    """
    conda環境をアクティベートする。
    現在の環境が指定された環境でない場合、自動的にアクティベートを試みる。
    
    Args:
        env_name: アクティベートするconda環境名
        
    Returns:
        アクティベートに成功した場合True、失敗した場合False
    """
    # 現在のconda環境をチェック
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    
    if current_env == env_name:
        print(f"✅ conda環境 '{env_name}' は既にアクティブです。")
        return True
    
    print(f"🔄 conda環境 '{env_name}' をアクティベート中...")
    
    # conda環境をアクティベート
    try:
        # conda shell hookを初期化
        result = subprocess.run(
            ["conda", "shell.bash", "hook"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # conda環境をアクティベート
        activate_cmd = f"source <(conda shell.bash hook) && conda activate {env_name}"
        result = subprocess.run(
            activate_cmd,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True
        )
        
        # 環境変数を更新（現在のプロセス内で）
        # 注意: これは現在のプロセス内でのみ有効
        # 完全なアクティベートにはシェルから実行する必要がある
        if result.returncode == 0:
            # conda環境のパスを取得
            env_list_result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 環境が存在するかチェック
            if env_name in env_list_result.stdout:
                print(f"✅ conda環境 '{env_name}' のアクティベートを試みました。")
                print(f"⚠️  注意: 完全なアクティベートには、シェルから以下のコマンドを実行してください:")
                print(f"   conda activate {env_name}")
                return True
            else:
                print(f"❌ エラー: conda環境 '{env_name}' が見つかりません。")
                print(f"   以下のコマンドで環境を作成してください:")
                print(f"   conda create -n {env_name} python=3.x")
                return False
        else:
            print(f"⚠️  警告: conda環境のアクティベートに失敗しました。")
            print(f"   手動で以下のコマンドを実行してください:")
            print(f"   conda activate {env_name}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: condaコマンドの実行に失敗しました: {e}")
        print(f"   手動で以下のコマンドを実行してください:")
        print(f"   conda activate {env_name}")
        return False
    except FileNotFoundError:
        print(f"❌ エラー: condaがインストールされていません。")
        print(f"   AnacondaまたはMinicondaをインストールしてください。")
        return False


def check_and_activate_conda_env(env_name: str = "py-dspy") -> None:
    """
    conda環境をチェックし、必要に応じてアクティベートする。
    環境がアクティブでない場合、警告を表示して続行を確認する。
    """
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    
    if current_env != env_name:
        print(f"⚠️  警告: 現在のconda環境は '{current_env}' です。")
        print(f"   推奨環境: '{env_name}'")
        
        # 自動アクティベートを試みる
        if not activate_conda_env(env_name):
            print(f"\n⚠️  環境の自動アクティベートに失敗しましたが、続行します。")
            print(f"   問題が発生した場合は、手動で 'conda activate {env_name}' を実行してください。\n")
        else:
            print()


def load_openai_api_key() -> str:
    """
    .env（OPENAI_API_KEY）または環境変数からAPIキーを取得する。
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            ".env または環境変数に OPENAI_API_KEY が設定されていません。"
        )
    return api_key


def main():
    # conda環境のチェックとアクティベート
    check_and_activate_conda_env("py-dspy")
    
    api_key = load_openai_api_key()
    model = os.getenv("OPENAI_MODEL", "gpt-4")
    llm = OpenAILLM(api_key=api_key, model=model)
    counselor = MIRhythmBot(llm=llm)
    session_meta = {
        "session_mode": "human_client",
        "openai_model": model,
        "script_name": "console_chat",
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

    # ログを日時入りファイル名で保存
    if env.log:
        from mi_log_tools import save_log_csv

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"session_console_{timestamp}.csv"
        save_log_csv(env, str(log_path))
        print(f"ログを保存しました: {log_path}")


if __name__ == "__main__":
    main()
