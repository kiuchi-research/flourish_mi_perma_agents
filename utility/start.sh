#!/bin/bash

# プロジェクト起動スクリプト
# このスクリプトは、プロジェクトの実行環境を自動的にセットアップし、必要なチェックを実行します。

set -e  # エラー時に停止

# 色付き出力の関数
print_info() {
    echo -e "\033[1;34mℹ️  $1\033[0m"
}

print_success() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_step() {
    echo -e "\033[1;36m📋 $1\033[0m"
}

# メイン処理
main() {
    echo "🚀 プロジェクト起動スクリプトを開始します..."
    echo "============================================================"
    
    ENV_NAME="myenv"
    ENV_FILE="environment.yml"
    
    # ステップ 1: condaの確認
    print_step "ステップ 1: condaの確認"
    if ! command -v conda &> /dev/null; then
        print_error "condaがインストールされていません"
        echo "   AnacondaまたはMinicondaをインストールしてください"
        echo "   https://docs.conda.io/en/latest/miniconda.html"
        exit 1
    fi
    
    print_success "condaがインストールされています"
    echo
    
    # ステップ 2: environment.ymlの確認
    print_step "ステップ 2: environment.ymlの確認"
    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "$ENV_FILEが見つかりません"
        echo "   $ENV_FILEファイルを作成してください"
        exit 1
    fi
    
    print_success "$ENV_FILEが存在します"
    echo
    
    # ステップ 3: 環境の確認・作成・更新
    print_step "ステップ 3: conda環境の確認・作成・更新"
    if ! conda env list | grep -q "^${ENV_NAME} "; then
        print_info "環境 '${ENV_NAME}' が存在しません。environment.ymlから作成します..."
        if conda env create -f "$ENV_FILE"; then
            print_success "環境 '${ENV_NAME}' を作成しました"
        else
            print_error "環境の作成に失敗しました"
            exit 1
        fi
    else
        print_success "環境 '${ENV_NAME}' が存在します"
        print_info "environment.ymlで環境を更新します..."
        if conda env update -f "$ENV_FILE"; then
            print_success "環境を更新しました"
        else
            print_error "環境の更新に失敗しました"
            exit 1
        fi
    fi
    
    echo
    
    # ステップ 4: 環境のアクティベート
    print_step "ステップ 4: 環境のアクティベート"
    print_info "環境 '${ENV_NAME}' をアクティベート中..."
    
    # conda環境をアクティベート
    eval "$(conda shell.bash hook)"
    conda activate "${ENV_NAME}"
    
    if [[ "$CONDA_DEFAULT_ENV" == "${ENV_NAME}" ]]; then
        print_success "環境 '${ENV_NAME}' がアクティブになりました"
    else
        print_error "環境のアクティベートに失敗しました"
        exit 1
    fi
    
    echo
    
    # ステップ 5: 環境チェック
    print_step "ステップ 5: 環境チェック"
    if [[ -f "utility/check_env.py" ]]; then
        print_info "環境チェックスクリプトを実行中..."
        if python utility/check_env.py; then
            print_success "環境チェックが完了しました"
        else
            print_warning "環境チェックで問題が検出されました"
            echo "   手動で確認してください: python utility/check_env.py"
        fi
    else
        print_warning "utility/check_env.pyが見つかりません。スキップします。"
    fi
    
    echo
    echo "============================================================"
    print_success "セットアップ完了！"
    echo
    echo "📋 次のステップ:"
    echo "1. conda activate ${ENV_NAME}"
    echo "2. python utility/check_env.py  # 環境チェック"
    echo "3. プロジェクト固有のコマンドを実行"
    echo
    echo "💡 ヒント:"
    echo "   - 環境を非アクティブにする: conda deactivate"
    echo "   - 環境を削除する: conda env remove -n ${ENV_NAME}"
    echo "   - 環境を更新する: conda env update -f ${ENV_FILE}"
    echo "   - 利用可能な環境を確認: conda env list"
}

# スクリプトの実行
main "$@" 