#!/usr/bin/env bash
# app/scripts/run_human_client_cli.sh
# human_client_counselor_cli.py を実行する前に conda 環境 py-dspy をアクティベートするラッパースクリプト

set -euo pipefail

# スクリプトのあるディレクトリとアプリルートを解決
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$APP_ROOT"

# conda環境名
ENV_NAME="py-dspy"

echo "🚀 human_client_counselor_cli.py を起動します..."
echo "============================================================"

# condaがインストールされているかチェック
if ! command -v conda &> /dev/null; then
    echo "❌ エラー: condaがインストールされていません"
    echo "   AnacondaまたはMinicondaをインストールしてください"
    exit 1
fi

# conda shell hookを初期化
eval "$(conda shell.bash hook)"

# conda環境をアクティベート
echo "🔄 conda環境 '${ENV_NAME}' をアクティベート中..."
if conda activate "${ENV_NAME}"; then
    if [[ "$CONDA_DEFAULT_ENV" == "${ENV_NAME}" ]]; then
        echo "✅ conda環境 '${ENV_NAME}' がアクティブになりました"
        echo ""
    else
        echo "⚠️  警告: 環境のアクティベートに失敗しましたが、続行します"
        echo ""
    fi
else
    echo "⚠️  警告: conda環境 '${ENV_NAME}' のアクティベートに失敗しました"
    echo "   環境が存在しない場合は、以下のコマンドで作成してください:"
    echo "   conda create -n ${ENV_NAME} python=3.x"
    echo ""
    echo "   続行しますが、問題が発生する可能性があります..."
    echo ""
fi

# Pythonスクリプトを実行
echo "============================================================"
python human_client_counselor_cli.py "$@"
