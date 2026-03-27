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
├── cli.py                         # サブコマンド CLI（human-client / self-play / human-counselor、self-play は mi_sim package に委譲）
├── cli_human_counselor_client.py  # 人間カウンセラー × LLM クライアントの実装（自動ラベル付け）
├── human_client_counselor_cli.py  # 互換ラッパー（人間クライアント向け旧コマンド名）
├── human_counselor_client_cli.py  # 互換ラッパー（人間カウンセラー向け旧コマンド名）
├── agent_dual_simulation.py       # 互換ラッパー（自己対話シミュレーションの旧コマンド名、app/cli 経由で mi_sim を呼ぶ）
├── counselor_llm_loader.py        # カウンセラーボットと補助LLM（フェーズ/行動/リスク/評価）をまとめて構築
├── client_llm_loader.py           # クライアント用 LLM セットをまとめて構築
├── mi_counselor_agent.py          # MIロジック本体（8フェーズ判定・リズム制御・安全/評価レイヤ）
├── conversation_environment.py    # 環境：履歴管理＋クライアント/カウンセラーのやり取り
├── perma_client_agent.py          # PERMA課題を持つシミュレーション用クライアントエージェント
├── session_log_tools.py           # ログ保存（JSONL/CSV）・クライアント評価JSON・解析
├── openai_llm.py                  # OpenAI Responses/Chat 共通ラッパー
├── env_utils.py                   # .env ローダーとモデル設定（デフォルト+YAMLの統合）
├── scripts/run_human_client_cli.sh # conda 確認付きラッパー
├── client_profiles.yaml           # クライアント設定サンプル（CLIENT_CODEで選択）
├── DsPy/                          # DSPy 版 bot・プログラム・学習スクリプト
├── logs/                          # 実行ログの出力先（実行時に自動生成）
├── archive/                       # 旧版のバックアップ
├── config/model_settings.yaml     # モード別の LLM 設定（Responses/Chat・reasoning/verbosity 等）
└── config/client_prompt_rules.md  # クライアント追加ルール（persona に追記）
```

## 依存・前提・モデル設定

- Python 3.11 前後を想定。LLM 呼び出しは `openai` 1.x（Responses API が既定）＋ `python-dotenv`。  
- `app/.env` を優先し、未配置なら従来どおりルート `.env` も使えます。新規作成時は `app/.env.example` を雛形にしてください。  
- モデル設定は `app/config/model_settings.yaml` を参照します（存在しないキーは組み込みデフォルトが補完）。モデル・reasoning・verbosity は YAML 設定がそのまま使われます。  
- OpenAI 呼び出しの待機制御は `.env`（`OPENAI_TIMEOUT_SECONDS` / `OPENAI_MAX_RETRIES` / `OPENAI_RETRY_BASE_SECONDS` / `OPENAI_RETRY_MAX_SECONDS` / `OPENAI_RETRY_LOG`）または `app/config/model_settings.yaml` の各モデル設定（`timeout_seconds` / `max_retries` / `retry_base_seconds` / `retry_max_seconds` / `retry_log`）で調整できます。  
- フェーズ遷移の最低品質閾値は `.env` の `PHASE_SLOT_QUALITY_MIN_THRESHOLD`（0.0〜1.0、既定 0.8）で調整できます。  
- クライアント追加ルールは `app/config/client_prompt_rules.md` を優先して読み込みます。`CLIENT_PROMPT_RULES_MD_PATH` を設定すると別ファイルへ切り替えできます。  
- `counselor_phase_slot_filler` / `counselor_action` は既定で有効。`counselor_risk_detector`（安全リスク判定）と `counselor_mi_evaluator`（MI 準拠セルフチェック）は YAML 側で `enabled: true` にすると利用。  
- 追加の MI 知識は `app/config/mi_knowledge.md` を読み込みます。`MI_KNOWLEDGE_MD_PATH` で別ファイル指定も可能です。  
- DSPy 系は別途 `dspy-ai` をインストールし、`OPENAI_API_KEY` を使える状態にしてください（デフォルトモデル: `openai/gpt-4o-mini`）。  
- `cli.py` の各サブコマンドは既定で `--conda-env=py-dspy` を確認して自動アクティベートを試みます（空文字指定で無効化可）。実行前に `python utility/check_env.py` を走らせることを推奨します。

## 使い方

### API不要のダミーデモ（DummyLLM）
- `python mi_counselor_agent.py` : `_run_demo()` で最小動作を確認。  
- `python conversation_environment.py` : 人間想定の簡易デモと DummyLLM 同士の自己対話を実行。  
- `python session_log_tools.py` : 簡易シミュレーション → 解析表示 → `session_example.jsonl` / `session_example.csv` を保存。  
- 簡易スモーク: `python -m py_compile app/mi_counselor_agent.py app/conversation_environment.py app/session_log_tools.py`

### 人間クライアント × LLM カウンセラー（CLI）
1. `app/.env` またはルート `.env` に `OPENAI_API_KEY=...` を設定。  
2. 推奨: `python utility/check_env.py` を実行して環境を確認。  
3. 対話を開始: `python app/cli.py human-client --conda-env py-dspy`  
   - 互換コマンド: `python app/human_client_counselor_cli.py` / `./app/scripts/run_human_client_cli.sh`  
   - フェーズ/行動ランカー、任意のリスク検知・MI評価は `app/config/model_settings.yaml` を優先して読み込みます。  
4. `Client:` プロンプトに入力し、`exit` で終了。  
5. 終了後、`app/logs/session_human_client_counselor_cli_<timestamp>.csv` と `..._client_eval.json` が保存されます（判定デバッグを含む）。

### Counselor/Client 両方 LLM で回す
- `python app/cli.py self-play --max-turns 10 --max-total-turns 16`（互換: `python app/agent_dual_simulation.py`）。`--conda-env ""` で conda チェック無効化。  
- 15ケース一括実行は `python app/cli.py self-play --all-cases --max-turns 40`。`LANG|SOCIAL|UNSOCIAL × MGR|LOWINC|ISO|STABLE|MOB` を順次回し、同じコマンドを再実行すると `CSV` と `client_eval.json` がそろったケースは自動スキップします。  
- 終了制御:
  - `--max-turns` は `phase_to_closing` で `REVIEW_REFLECTION` へ入るトリガー（実質「振り返り開始ターン」）。
  - `--max-turns-completion` は終了方式（`phase_to_closing` / `hard_stop`、既定 `phase_to_closing`）。
  - `--max-total-turns` は `phase_to_closing` 時の安全上限（未指定なら `max-turns + 7`、実質「最遅終了ターン」）。
  - 厳密に `N` ターンで終わらせるなら `--max-turns-completion hard_stop --max-turns N` を使用。
  - 現状は `--review-start-turn` / `--end-turn` の専用フラグはなく、上記3オプションで制御。
  - 例: `python app/cli.py self-play --max-turns 8 --max-turns-completion phase_to_closing --max-total-turns 14`
- クライアントは `CLIENT_CODE`（例: `LANG_MGR`、未指定時も `LANG_MGR`）で選択し、`CLIENT_STYLE=cooperative|ambivalent|resistant|auto`、`FIRST_CLIENT_UTTERANCE`、`CLIENT_MAX_STATE_STEP`、`CLIENT_PROFILES_PATH` で調整可能。初期発話は LLM 生成が既定です。  
- CLI 引数でも `--client-code SOCIAL_STABLE` のように単発ケースを明示できます。`--client-code all` でも15ケース一括実行になります。  
- `CLIENT_CODE` の命名規則: `{PERMAパターン}_{ケース群}`  
  - PERMAパターン: `LANG` / `SOCIAL` / `UNSOCIAL`
  - ケース群: `MGR`（過重責任ミドルマネジャー）/ `LOWINC`（親同居・低所得）/ `ISO`（独居・地域孤立）/ `STABLE`（安定就業だが対人関係が細い）/ `MOB`（転職反復・自己評価低下）
  - 例: `SOCIAL_STABLE`, `UNSOCIAL_MOB`
- 単発時は `app/logs/session_simulation_<timestamp>.csv` と `..._client_eval.json` を出力。一括時は `app/logs/self_play_batch/<設定別ディレクトリ>/` 配下にケースごとの固定ファイル名で出力します。

### 人間カウンセラー × LLM クライアント（自動ラベル付け）
- `python app/cli.py human-counselor`（実装は `cli_human_counselor_client.py`）。  
- ヒューリスティックでクライアント発話からフェーズを推定し、`LLMActionClassifier` が人間カウンセラー発話の `main_action/add_affirm` を自動ラベル。  
- クライアント選択と環境変数は self-play と同じ（`CLIENT_CODE` など）。ログにはクライアント内部状態の時系列も含み、`app/logs/session_human_counselor_client_cli_<timestamp>.csv` と `..._client_eval.json` を保存。

### DSPy 版カウンセラーと最適化
- `DsPy/mi_counselor_dspy.py` の `MIRhythmBotDSPy` は `ConversationEnvironment` と互換。`from_compiled(...)` で `compiled/*.json` をロードし、返り値は `(reply, Decision)`。  
- `DsPy/train_a_generation.py` / `train_b_estimators.py` / `train_c_session.py` で順に 発話生成 → フェーズ/行動推定 → セッション最適化 を実行（入力は `app/logs/*.csv`）。  
- データ/メトリクスは `DsPy/mi_dspy_data.py`・`DsPy/mi_dspy_metrics.py` を参照。コンパイル結果は `compiled/` に保存。

### クイック実行の目安
- `python app/human_client_counselor_cli.py` : カウンセラーボット × 人間クライアントで対話。  
- `python app/human_counselor_client_cli.py` : 人間カウンセラー × クライアントボットで対話（自動ラベル付け）。  
- `python app/agent_dual_simulation.py` : エージェント同士の自己対話（既定5ターン）。  
いずれも `.env` に `OPENAI_API_KEY` が必要で、セッション終了後に `app/logs/` へログが保存されます。`conda` の `py-dspy` もしくは同名の Python 仮想環境を自動で有効化しようとするため、事前に `environment.yml` または `requirements.txt` で準備しておくと確実です。

## ログ保存と解析（session_log_tools.py）

- `finalize_session(env, llm, log_prefix=...)` は CSV とクライアント評価 JSON をまとめて保存（`app/logs/`）。  
- `save_log_csv` は BOM 付き UTF-8。counselor ターンの `phase/main_action/add_affirm`、`reflect_streak_before` / `r_since_q_before`、`features_json`、クライアント内部状態（`client_internal_state_json` / `..._reason_json` / `client_meta_json` / `client_raw` / `client_parse_status`）、`planner_config_json`、クライアントプロファイル情報などを列に含めます。  
- 解析: `analyze_phases` / `analyze_actions` / `analyze_reflect_streaks` / `analyze_change_talk_responses` / `analyze_resistance_responses`、まとめ表示 `print_basic_analysis`。  
- クライアント視点評価: `evaluate_session_from_client_pov` が satisfaction / importance / confidence / alliance / affect を 0〜10 で返し、`save_client_evaluation_json` で保存。

## コアロジックのハイライト（mi_counselor_agent.py）

- **フェーズ管理**: 8フェーズをスロットレビュー＋ルールゲートで更新し、初回/挨拶直後のガードレールで遷移を安定化。  
- **特徴量抽出**: 質問/情報要求、有無の許可、抵抗・チェンジトーク・新情報スコア、要約推奨、反射上限解除可否などをルールで算出。  
- **行動決定と安全レイヤ**: `compute_allowed_actions` で action mask（許可集合）を計算し、LLM ランカーの提案を mask 内で強制採用。mask 外提案はフォールバックされ、`invalid_action` がログに残ります。`LLMRiskDetector`（任意）で危機を検知したときは情報共有モードを解除し、安全案内を優先。  
- **応答生成・検査**: `build_prompt` がフェーズ/主動作別の出力制約を付け、`validate_output` が最低限のチェックを実施。MI 準拠スコアを `LLMMIEvaluator`（任意）で採点し、`evaluation_rewrite_threshold` 未満なら自動で一度書き直します。  
- **状態更新**: 反射ストリーク・質問間隔・要約間隔・是認間隔・情報共有モードを更新し、同じ主動作の連続出力や過剰な反射を抑制。

## メモ

- `archive/` には旧版のバックアップがあります。最新の動作は app/ 直下と DsPy/ のファイルを参照してください。
