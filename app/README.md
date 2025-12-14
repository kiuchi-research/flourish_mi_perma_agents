# MI Rhythm Bot / DSPy README

## これは何をするものか

最大の目的は「カウンセリングログの収集」です。  
- **カウンセラーエージェント**: 動機づけ面接（MI）の8フェーズを追い、聞き返し／質問／要約／許可付き情報共有（Elicit–Provide–Elicit）をルール＋確率で選択して生成。反射連発の抑制、チェンジトーク・抵抗・新情報に応じたリズム制御に加え、任意で安全リスク検知と MI 準拠セルフチェックを挟めます。  
- **クライアントエージェント**: PERMA 領域の課題を抱える設定で、内部状態（ポジ・ネガ感情、重要度、自信、ラポール／緊張など）の変動をログに残しながら応答。初期発話は LLM 生成が既定（環境変数で上書き可）。  
- **ログ収集の対象セッション**:  
  - 人間カウンセラー × クライアントエージェント（自動ラベル付け）  
  - カウンセラーエージェント × 人間クライアント  
  - カウンセラーエージェント × クライアントエージェント  
  いずれも同じ形式で CSV/JSONL とクライアント評価 JSON を残し、後段の解析や DSPy 最適化に使います。  
`app/DsPy/` には同じロジックを DSPy で最適化するためのプログラムと学習スクリプトがあります。

## 主なファイル構成（app/）

```text
app/
├── cli.py                         # サブコマンド CLI（human-client / self-play / human-counselor）
├── cli_human_counselor_client.py  # 人間カウンセラー × LLM クライアントの実装（自動ラベル付け）
├── human_client_counselor_cli.py  # 互換ラッパー（人間クライアント向け旧コマンド名）
├── human_counselor_client_cli.py  # 互換ラッパー（人間カウンセラー向け旧コマンド名）
├── agent_dual_simulation.py       # 互換ラッパー（自己対話シミュレーションの旧コマンド名）
├── counselor_llm_loader.py        # カウンセラーボットと補助LLM（フェーズ/行動/リスク/評価）をまとめて構築
├── client_llm_loader.py           # クライアント用 LLM セットをまとめて構築
├── mi_counselor_agent.py          # MIロジック本体（8フェーズ判定・リズム制御・安全/評価レイヤ）
├── conversation_environment.py    # 環境：履歴管理＋クライアント/カウンセラーのやり取り
├── perma_client_agent.py          # PERMA課題を持つシミュレーション用クライアントエージェント
├── session_log_tools.py           # ログ保存（JSONL/CSV）・クライアント評価JSON・解析
├── openai_llm.py                  # OpenAI Responses/Chat 共通ラッパー
├── env_utils.py                   # .env ローダーとモデル設定（デフォルト+YAML+環境変数の統合）
├── scripts/run_human_client_cli.sh # conda 確認付きラッパー
├── client_profiles.yaml           # クライアント設定サンプル（CLIENT_CODEで選択）
├── DsPy/                          # DSPy 版 bot・プログラム・学習スクリプト
├── logs/                          # 実行ログの出力先（実行時に自動生成）
├── archive/                       # 旧版のバックアップ
└── ../config/model_settings.yaml  # モード別の LLM 設定（Responses/Chat・reasoning/verbosity 等）※app の外に配置
```

## 依存・前提・モデル設定

- Python 3.11 前後を想定。LLM 呼び出しは `openai` 1.x（Responses API が既定）＋ `python-dotenv`。  
- ルート `.env` に `OPENAI_API_KEY=...`（必要なら `OPENAI_MODEL` 等）を置いてください。  
- モデル設定は `config/model_settings.yaml`（存在しないキーは組み込みデフォルトが補完）。`OPENAI_MODEL/OPENAI_REASONING_EFFORT/OPENAI_VERBOSITY` でカウンセラー用、`OPENAI_CLIENT_MODEL/OPENAI_CLIENT_REASONING_EFFORT/OPENAI_CLIENT_VERBOSITY` でクライアント用を上書きできます。  
- `counselor_phase` / `counselor_action` は既定で有効。`counselor_risk_detector`（安全リスク判定）と `counselor_mi_evaluator`（MI 準拠セルフチェック）は YAML 側で `enabled: true` にすると利用。  
- DSPy 系は別途 `dspy-ai` をインストールし、`OPENAI_API_KEY` を使える状態にしてください（デフォルトモデル: `openai/gpt-4o-mini`）。  
- `cli.py` の各サブコマンドは既定で `--conda-env=py-dspy` を確認して自動アクティベートを試みます（空文字指定で無効化可）。実行前に `python utility/check_env.py` を走らせることを推奨します。

## 使い方

### API不要のダミーデモ（DummyLLM）
- `python mi_counselor_agent.py` : `_run_demo()` で最小動作を確認。  
- `python conversation_environment.py` : 人間想定の簡易デモと DummyLLM 同士の自己対話を実行。  
- `python session_log_tools.py` : 簡易シミュレーション → 解析表示 → `session_example.jsonl` / `session_example.csv` を保存。  
- 簡易スモーク: `python -m py_compile app/mi_counselor_agent.py app/conversation_environment.py app/session_log_tools.py`

### OpenAI API を使って対話する（人間クライアント）
1. ルートの `.env` に `OPENAI_API_KEY=...`（必要に応じて `OPENAI_MODEL` ほか）を設定。  
2. `python app/cli.py human-client --conda-env py-dspy`（互換: `python app/human_client_counselor_cli.py` / `./app/scripts/run_human_client_cli.sh`）。  
   - フェーズ/行動ランカー、任意のリスク検知・MI評価は `config/model_settings.yaml` の設定に従います。  
3. `Client:` に入力し、`exit` で終了。`app/logs/session_human_client_counselor_cli_<timestamp>.csv` と `..._client_eval.json` を保存します（判定デバッグも含む）。

### Counselor/Client 両方 LLM で回す
- `python app/cli.py self-play --max-turns 5`（互換: `python app/agent_dual_simulation.py`）。`--conda-env ""` で conda チェック無効化。  
- クライアントは `CLIENT_CODE`（デフォルト C01）で選択し、`CLIENT_STYLE=cooperative|ambivalent|resistant|auto`、`FIRST_CLIENT_UTTERANCE`、`CLIENT_MAX_STATE_STEP`、`CLIENT_PROFILES_PATH` で調整可能。初期発話は LLM 生成が既定です。  
- `app/logs/session_simulation_<timestamp>.csv` と `..._client_eval.json` を出力。

### 人間カウンセラー × LLM クライアント（自動ラベル付け）
- `python app/cli.py human-counselor`（実装は `cli_human_counselor_client.py`）。  
- `LLMPhaseClassifier` がクライアント発話からフェーズを推定し、`LLMActionClassifier` が人間カウンセラー発話の `main_action/add_affirm` を自動ラベル。  
- クライアント選択と環境変数は self-play と同じ（`CLIENT_CODE` など）。ログにはクライアント内部状態の時系列も含み、`app/logs/session_human_counselor_client_cli_<timestamp>.csv` と `..._client_eval.json` を保存。

### DSPy 版カウンセラーと最適化
- `DsPy/mi_counselor_dspy.py` の `MIRhythmBotDSPy` は `ConversationEnvironment` と互換。`from_compiled(...)` で `compiled/*.json` をロードし、返り値は `(reply, Decision)`。  
- `DsPy/train_a_generation.py` / `train_b_estimators.py` / `train_c_session.py` で順に 発話生成 → フェーズ/行動推定 → セッション最適化 を実行（入力は `app/logs/*.csv`）。  
- データ/メトリクスは `DsPy/mi_dspy_data.py`・`DsPy/mi_dspy_metrics.py` を参照。コンパイル結果は `compiled/` に保存。

## ログ保存と解析（session_log_tools.py）

- `finalize_session(env, llm, log_prefix=...)` は CSV とクライアント評価 JSON をまとめて保存（`app/logs/`）。  
- `save_log_csv` は BOM 付き UTF-8。counselor ターンの `phase/main_action/add_affirm`、`reflect_streak_before` / `r_since_q_before`、`features_json`、クライアント内部状態（`client_internal_state_json` / `..._reason_json` / `client_meta_json` / `client_raw` / `client_parse_status`）、`planner_config_json`、クライアントプロファイル情報などを列に含めます。  
- 解析: `analyze_phases` / `analyze_actions` / `analyze_reflect_streaks` / `analyze_change_talk_responses` / `analyze_resistance_responses`、まとめ表示 `print_basic_analysis`。  
- クライアント視点評価: `evaluate_session_from_client_pov` が satisfaction / importance / confidence / alliance / affect を 0〜10 で返し、`save_client_evaluation_json` で保存。

## コアロジックのハイライト（mi_counselor_agent.py）

- **フェーズ管理**: 8フェーズをルールで更新しつつ、`LLMPhaseClassifier` が有効なら信頼度付きで上書き（低信頼時はフォールバック）。  
- **特徴量抽出**: 質問/情報要求、有無の許可、抵抗・チェンジトーク・新情報スコア、要約推奨、反射上限解除可否などをルールで算出。  
- **行動決定と安全レイヤ**: `plan_next_action` がリズム制御し、LLM ランカーがあればバイアスとして反映。`LLMRiskDetector`（任意）で危機を検知したときは情報共有モードを解除し、安全案内を優先。  
- **応答生成・検査**: `build_prompt` がフェーズ/主動作別の出力制約を付け、`validate_output` が最低限のチェックを実施。MI 準拠スコアを `LLMMIEvaluator`（任意）で採点し、`evaluation_rewrite_threshold` 未満なら自動で一度書き直します。  
- **状態更新**: 反射ストリーク・質問間隔・要約間隔・是認間隔・情報共有モードを更新し、同じ主動作の連続出力や過剰な反射を抑制。

## メモ

- `archive/` には旧版のバックアップがあります。最新の動作は app/ 直下と DsPy/ のファイルを参照してください。
