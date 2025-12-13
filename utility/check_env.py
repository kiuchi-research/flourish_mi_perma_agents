#!/usr/bin/env python3
"""
環境チェックスクリプト
このプロジェクトでPythonコードを実行する前に、必ずこのスクリプトを実行してください。
"""

import sys
import subprocess
import os
import re
from pathlib import Path

def parse_environment_yml(env_file: str) -> list:
    """environment.ymlファイルを解析してパッケージ名のリストを取得"""
    packages = []
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # pipセクションからパッケージを抽出
        pip_section = re.search(r'pip:\s*\n((?:\s+-\s+.*\n?)*)', content)
        if pip_section:
            pip_packages = pip_section.group(1)
            for line in pip_packages.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    package = line[2:]  # "- "を除去
                    # バージョン指定を除去
                    package_name = re.split(r'[<>=!~]', package)[0].strip()
                    if package_name:
                        packages.append(package_name)
                        
    except FileNotFoundError:
        print(f"❌ エラー: {env_file} が見つかりません")
        return []
    except Exception as e:
        print(f"❌ エラー: {env_file} の解析に失敗: {e}")
        return []
    
    return packages

def check_conda_env():
    """conda環境の確認（具体的な環境名は問わない）"""
    print("🔍 conda環境をチェック中...")
    env_name = os.environ.get('CONDA_DEFAULT_ENV')
    if not env_name:
        print("❌ エラー: conda環境がアクティブではありません")
        print("実行例: conda activate <your-env-name>")
        print("⚠️ 注意: READMEやルールファイルで推奨仮想環境名を明記してください")
        return False
    print(f"✅ conda環境がアクティブです（環境名: {env_name}）")
    # 仮想環境名が 'base' の場合は警告
    if env_name == 'base':
        print("⚠️ 警告: 'base' 環境での開発は推奨されません。専用の仮想環境を作成し、README等で環境名を明記してください。")
    return True

def check_dependencies():
    """依存関係の確認"""
    print("🔍 依存関係をチェック中...")
    
    # environment.ymlからパッケージリストを動的に取得
    env_file = "environment.yml"
    required_packages = parse_environment_yml(env_file)
    
    if not required_packages:
        print(f"❌ エラー: {env_file} からパッケージリストを取得できませんでした")
        return False
    
    print(f"📦 チェック対象パッケージ数: {len(required_packages)}")
    
    missing_packages = []
    
    for package in required_packages:
        try:
            # パッケージ名の正規化（ハイフンをアンダースコアに変換）
            import_name = package.replace('-', '_')
            
            # 特殊なインポート名の処理
            if package == 'python-dateutil':
                import dateutil
            elif package == 'python-dotenv':
                import dotenv
            elif package == 'typing-extensions':
                import typing_extensions
            elif package == 'pyyaml':
                import yaml
            else:
                __import__(import_name)
                
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 不足している依存関係: {', '.join(missing_packages)}")
        print("実行してください: conda env update -f environment.yml")
        return False
    
    print("✅ 主要な依存関係がインストールされています")
    return True

def check_environment_files():
    """environment.ymlファイルの存在確認"""
    print("🔍 environment.ymlファイルをチェック中...")
    
    env_file = Path("environment.yml")
    
    if not env_file.exists():
        print("⚠️ 警告: environment.ymlが見つかりません")
        return False
    
    print("✅ environment.ymlファイルが存在します")
    return True

def main():
    """メイン関数"""
    print("🚀 環境チェックを開始します...")
    print("=" * 50)
    
    env_ok = check_conda_env()
    print()
    
    env_files_ok = check_environment_files()
    print()
    
    deps_ok = check_dependencies()
    print()

    # Codex CLI/IDE 用の設定確認
    print("🔍 Codex 設定をチェック中...")
    codex_dir = Path('.codex')
    codex_config = codex_dir / 'config.toml'
    if codex_dir.exists() and codex_config.exists():
        try:
            # TOML は標準ライブラリに含まれないため軽量に手動抽出
            policy = None
            sandbox = None
            model = None
            with open(codex_config, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'approval_policy' in line and '=' in line:
                        policy = line.split('=', 1)[1].strip().strip('"').strip("'\n ")
                    if 'sandbox_mode' in line and '=' in line and 'sandbox_workspace_write' not in line:
                        sandbox = line.split('=', 1)[1].strip().strip('"').strip("'\n ")
                    if line.strip().startswith('model') and '=' in line:
                        model = line.split('=', 1)[1].strip().strip('"').strip("'\n ")
            print("✅ .codex/config.toml を検出")
            if model:
                print(f"   • model: {model}")
            if policy:
                print(f"   • approval_policy: {policy}")
            if sandbox:
                print(f"   • sandbox_mode: {sandbox}")
        except Exception as e:
            print(f"⚠️ .codex/config.toml の読み取りに失敗: {e}")
    else:
        print("ℹ️ .codex/config.toml が見つかりません。Codex CLI/IDE を使う場合は作成してください。")
    print()
    
    print("=" * 50)
    
    if env_ok and deps_ok and env_files_ok:
        print("🎉 環境チェック完了！実行準備OK")
        active_env = os.environ.get('CONDA_DEFAULT_ENV', '不明')
        print(f"✅ 仮想環境: {active_env}")
        print("✅ 依存関係: インストール済み")
        print("✅ 設定ファイル: 存在確認済み")
        sys.exit(0)
    else:
        print("⚠️ 環境に問題があります。上記の指示に従って修正してください")
        print()
        print("📋 修正手順:")
        print("1. conda create -n <your-env-name> python=3.x  # 初回のみ")
        print("2. conda activate <your-env-name>")
        print("3. conda env update -f environment.yml")
        print("4. python utility/check_env.py  # 再チェック")
        print("\n⚠️ 注意: READMEやルールファイルで推奨仮想環境名を明記してください")
        sys.exit(1)

if __name__ == "__main__":
    main() 
