#!/usr/bin/env bash
# utility/codex-session.sh
# 目的:
# - すべての一時/キャッシュ/出力をワークスペース内に固定
# - 仮想環境（conda または venv）をワークスペース内から起動
# - Codex (CLI: Command Line Interface) を安全に起動
set -euo pipefail

# 1) ディレクトリの事前作成
mkdir -p ./workbench/tmp ./workbench/logs ./results \
         ./.cache/pip ./.cache/tmp ./.config ./.pip ./.conda/envs ./.conda/pkgs

# 2) XDGベースの標準パスもワークスペース内へ
export XDG_CACHE_HOME="$PWD/.cache"
export XDG_CONFIG_HOME="$PWD/.config"

# 3) 一時ディレクトリを固定（macOS/Linux/Windows互換）
export TMPDIR="$PWD/workbench/tmp"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"

# 4) pip/conda キャッシュも固定
export PIP_CACHE_DIR="$PWD/.cache/pip"
export PIP_CONFIG_FILE="$PWD/.pip/pip.conf"
export CONDA_ENVS_PATH="$PWD/.conda/envs"
export CONDA_PKGS_DIRS="$PWD/.conda/pkgs"

# 5) 仮想環境（conda を優先）の起動
#    README の標準は conda 環境（py-mm-stress）なので conda を推奨。:contentReference[oaicite:5]{index=5}
TARGET_CONDA_ENV_PATH="$PWD/.conda/envs/py-mm-stress"
if command -v conda >/dev/null 2>&1 && [ -d "$TARGET_CONDA_ENV_PATH" ]; then
  # conda shell を読み込み
  eval "$(conda shell.bash hook)"
  conda activate "$TARGET_CONDA_ENV_PATH"
elif [ -d ".venv" ]; then
  # venv フォールバック
  # venv は requirements.txt を使わない運用が前提（同ファイルは CI 用の注意書きあり）:contentReference[oaicite:6]{index=6}
  # 必要パッケージは手動インストールしてください。
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# 6) Codex（IDE: Integrated Development Environment / CLI）をワークスペースで起動
#    --cd で明示的にルートを固定できる実装もあります（CLIの挙動として）。※参考情報
#    引数はそのまま Codex に渡します。
exec codex "$@"
