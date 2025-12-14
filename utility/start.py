#!/usr/bin/env python3
"""
プロジェクト起動スクリプト
このスクリプトは、プロジェクトの実行環境を自動的にセットアップし、必要なチェックを実行します。
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description, check=True):
    """コマンドを実行し、結果を表示"""
    print(f"🔄 {description}...")
    print(f"   実行コマンド: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        
        if result.stdout:
            print(f"   出力: {result.stdout.strip()}")
        
        if result.stderr and check:
            print(f"   警告: {result.stderr.strip()}")
        
        if result.returncode == 0:
            print(f"   ✅ {description}完了")
            return True
        else:
            print(f"   ❌ {description}失敗 (終了コード: {result.returncode})")
            if result.stderr:
                print(f"   エラー: {result.stderr.strip()}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description}でエラーが発生: {e}")
        return False
    except Exception as e:
        print(f"   ❌ {description}で予期しないエラー: {e}")
        return False

def check_conda_installed():
    """condaがインストールされているかチェック"""
    try:
        result = subprocess.run(['conda', '--version'], 
                              capture_output=True, text=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_env_exists(env_name):
    """指定されたconda環境が存在するかチェック"""
    try:
        result = subprocess.run(['conda', 'env', 'list'], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return env_name in result.stdout
        return False
    except FileNotFoundError:
        return False

def create_conda_env_from_yml(env_file):
    """environment.ymlからconda環境を作成"""
    print(f"🔧 environment.ymlから環境を作成中...")
    
    command = f"conda env create -f {env_file}"
    return run_command(command, f"environment.ymlからの環境作成")

def update_conda_env_from_yml(env_file):
    """environment.ymlでconda環境を更新"""
    print(f"🔧 environment.ymlで環境を更新中...")
    
    command = f"conda env update -f {env_file}"
    return run_command(command, f"environment.ymlでの環境更新")

def run_environment_check():
    """環境チェックスクリプトを実行"""
    check_script = Path("utility/check_env.py")
    if not check_script.exists():
        print("⚠️ utility/check_env.pyが見つかりません。スキップします。")
        return True
    
    command = f"python {check_script}"
    return run_command(command, "環境チェック", check=False)

def main():
    """メイン関数"""
    print("🚀 プロジェクト起動スクリプトを開始します...")
    print("=" * 60)
    
    env_name = "py-dspy"
    env_file = "environment.yml"
    
    # 1. condaの確認
    print("📋 ステップ 1: condaの確認")
    if not check_conda_installed():
        print("❌ エラー: condaがインストールされていません")
        print("   AnacondaまたはMinicondaをインストールしてください")
        print("   https://docs.conda.io/en/latest/miniconda.html")
        sys.exit(1)
    
    print("✅ condaがインストールされています")
    print()
    
    # 2. environment.ymlの確認
    print("📋 ステップ 2: environment.ymlの確認")
    if not Path(env_file).exists():
        print(f"❌ エラー: {env_file}が見つかりません")
        print(f"   {env_file}ファイルを作成してください")
        sys.exit(1)
    
    print(f"✅ {env_file}が存在します")
    print()
    
    # 3. 環境の確認・作成・更新
    print("📋 ステップ 3: conda環境の確認・作成・更新")
    if not check_env_exists(env_name):
        print(f"環境 '{env_name}' が存在しません。environment.ymlから作成します...")
        if not create_conda_env_from_yml(env_file):
            print("❌ 環境の作成に失敗しました")
            sys.exit(1)
    else:
        print(f"✅ 環境 '{env_name}' が存在します")
        print("environment.ymlで環境を更新します...")
        if not update_conda_env_from_yml(env_file):
            print("❌ 環境の更新に失敗しました")
            sys.exit(1)
    
    print()
    
    # 4. 環境のアクティベート
    print("📋 ステップ 4: 環境のアクティベート")
    print(f"🔄 環境 '{env_name}' をアクティベート中...")
    
    # 現在のOSに応じてアクティベートコマンドを決定
    if platform.system() == "Windows":
        activate_cmd = f"conda activate {env_name}"
    else:
        activate_cmd = f"source activate {env_name}"
    
    print(f"   実行してください: {activate_cmd}")
    print("   または: conda activate py-dspy")
    print()
    
    # 5. 環境チェック
    print("📋 ステップ 5: 環境チェック")
    if not run_environment_check():
        print("⚠️ 環境チェックで問題が検出されました")
        print("   手動で確認してください: python utility/check_env.py")
    
    print()
    print("=" * 60)
    print("🎉 セットアップ完了！")
    print()
    print("📋 次のステップ:")
    print(f"1. conda activate {env_name}")
    print("2. python utility/check_env.py  # 環境チェック")
    print("3. プロジェクト固有のコマンドを実行")
    print()
    print("💡 ヒント:")
    print("   - 環境を非アクティブにする: conda deactivate")
    print("   - 環境を削除する: conda env remove -n py-dspy")
    print("   - 環境を更新する: conda env update -f environment.yml")
    print("   - 利用可能な環境を確認: conda env list")

if __name__ == "__main__":
    main() 
