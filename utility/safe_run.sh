#!/usr/bin/env bash
# utility/safe_run.sh
# 指定コマンドを最大 N 回まで自動リトライ。全て失敗した時だけ非ゼロ終了(= Codex側の on-failure が発火)。
# 使い方: ./utility/safe_run.sh 2 make data
set -euo pipefail

RETRY=${1:-1}
shift || true

i=0
while :; do
  if "$@"; then
    exit 0
  fi
  i=$((i+1))
  if [ "$i" -gt "$RETRY" ]; then
    exit 1
  fi
  sleep 1
done
