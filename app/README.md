# MI Rhythm Bot / DSPy README

## これは何をするものか

最大の目的は「カウンセリングログの収集」です。  
- **カウンセラーエージェント**: 動機づけ面接（Motivational Interviewing; MI）に基づき、8フェーズ（あいさつ〜クロージング）で状態を持ち、聞き返し・質問・要約・許可付き情報共有（Elicit–Provide–Elicit）をルール＋確率で選択して生成。反射の連発抑制やチェンジトーク／抵抗／新情報に応じたリズム制御を行います。  
- **クライアントエージェント**: PERMA 領域の課題を抱える設定で、内部状態（ポジ・ネガ感情、重要度、自信、ラポール／緊張など）の変動をログに取りながら、それに基づいて応答します。  
- **ログ収集の対象セッション**:  
  - 人間カウンセラー × クライアントエージェント  
  - カウンセラーエージェント × 人間クライアント  
  - カウンセラーエージェント × クライアントエージェント  
  いずれも同様の形式でログを保存し、後続の解析や最適化に利用します。  
将来的には、このログを活用してカウンセラー／クライアント両エージェントの評価や、DSPy による LLM 部分の最適化（発話・内部状態更新のチューニング）へ発展させることを目指しています。  
`app/DsPy/` には同じロジックを DSPy で最適化するパイプラインが追加されています。

## 主なファイル構成（app/）

```text
app/
├── mi_counselor_agent.py          # MIロジック本体（8フェーズ判定・リズム制御・プロンプト生成）
├── conversation_environment.py    # 環境：履歴管理＋クライアント/カウンセラーのやり取り
├── perma_client_agent.py          # PERMA課題を持つシミュレーション用クライアントエージェント
├── session_log_tools.py           # ログ保存（JSONL/CSV）と解析
├── openai_llm.py                  # OpenAI Chat/Responses 共通ラッパー
├── env_utils.py                   # OPENAI_API_KEY ローダー
├── cli.py                         # サブコマンド CLI（human-client / self-play / human-counselor）
├── human_client_counselor_cli.py  # 互換ラッパー（人間クライアント向け旧コマンド名）
├── human_counselor_client_cli.py  # 互換ラッパー（人間カウンセラー × LLM クライアントの旧コマンド名）
├── agent_dual_simulation.py       # 互換ラッパー（自己対話シミュレーションの旧コマンド名）
├── scripts/run_human_client_cli.sh # conda を確認して human_client_counselor_cli.py を起動するラッパー
├── client_profiles.yaml           # クライアント設定サンプル
├── DsPy/                          # DSPy 版 bot・プログラム・学習スクリプト
├── logs/                          # 実行ログの出力先（実行時に自動生成）
├── archive/                       # 旧版のバックアップ
└── ../config/model_settings.yaml  # モード別の LLM 設定（Responses/Chat・モデル・reasoning/verbosity など）※app の外に配置
```

## 依存・前提

- Python 3.11 前後を想定（`mi_counselor_agent.py` は標準ライブラリのみで動作）。  
- `cli.py` 配下のサブコマンド（human-client / human-counselor / self-play）では `openai`（0.x 系）と `python-dotenv` を使用します（旧ラッパーも同様）。  
- OpenAI を使うときはリポジトリ直下（`../.env`）に `OPENAI_API_KEY=...` を用意してください。  
  - human-client: `config/model_settings.yaml` の `human_client_counselor` 設定（既定: Responses + gpt-5-nano、reasoning/verbosity=low）。環境変数 `OPENAI_MODEL` などで上書き可。  
  - self-play: カウンセラーは `self_play_counselor`、クライアントは `self_play_client_state`（内部状態更新）と `self_play_client_reply`（応答生成）設定（既定: Responses + gpt-5-nano、reasoning/verbosity=low）。カウンセラー内部のフェーズ判定/行動ランクは `counselor_phase_classifier` / `counselor_action_ranker`（既定で enabled=true）。  
  - human-counselor: フェーズ判定は `human_counselor_phase_classifier`、行動判定は `human_counselor_action_classifier`（いずれも既定: Responses + gpt-5-nano）。クライアントは内部状態更新に `human_counselor_client_state`、応答生成に `human_counselor_client_reply`（既定: Responses + gpt-5-mini、reasoning=medium、verbosity=low）。環境変数 `OPENAI_MODEL`/`OPENAI_CLIENT_MODEL` などで上書き可。クライアント設定は `client_profiles.yaml` から読み込みます（`CLIENT_PROFILES_PATH` でパス指定可）。  
- DSPy 系は別途 `dspy-ai` をインストールし、`OPENAI_API_KEY` を使える状態にしてください（デフォルトは `openai/gpt-4o-mini`）。  
- 上位プロジェクトの手順に従い、`conda activate py-dspy` 等で環境を有効化し、必要に応じて `python utility/check_env.py` を実行することを推奨します。

## 使い方

### API不要のダミーデモ（DummyLLM）
- `python mi_counselor_agent.py` : `_run_demo()` で最小動作を確認。  
- `python conversation_environment.py` : 人間想定の簡易デモと DummyLLM 同士の自己対話を実行。  
- `python session_log_tools.py` : 簡易シミュレーション → 解析表示 → `session_example.jsonl` / `session_example.csv` を保存。  
- 簡易スモーク: `python -m py_compile app/mi_counselor_agent.py app/conversation_environment.py app/session_log_tools.py`

### OpenAI API を使って対話する
1. ルートの `.env` に `OPENAI_API_KEY=...`（必要なら `OPENAI_MODEL`）を設定。  
2. 環境を用意  
   - 推奨: `conda activate py-dspy` → `python cli.py human-client`  
   - 互換: `python human_client_counselor_cli.py` / `./scripts/run_human_client_cli.sh` も利用可
3. `client:` に入力し、`exit` で終了すると `logs/session_human_client_counselor_cli_<timestamp>.csv` とクライアント評価 JSON が保存されます（旧プレフィックスを維持）。  
   - `cli.py` の各サブコマンドは既定で `--conda-env=py-dspy` を確認して自動アクティベートを試みます（空文字指定で無効化可）。

### Counselor/Client 両方 LLM で回す
- `python cli.py self-play` を実行。進行を逐次表示（内部で progress=True）し、`logs/session_simulation_<timestamp>.csv` を出力します（`agent_dual_simulation.py` も互換で利用可能）。`--conda-env` で環境指定（既定 py-dspy）。

### 人間カウンセラー × LLM クライアント（自動ラベル付け）
- `python cli.py human-counselor` を実行（旧 `human_counselor_client_cli.py` も互換で利用可能）。`--conda-env` で環境指定（既定 py-dspy）。  
  - クライアントは `SimpleClientLLM` が応答。  
  - フェーズは `LLMPhaseClassifier`（8フェーズ）、行動ラベルは `LLMActionClassifier` で自動推定。  
  - クライアント内部状態推定: デフォルトで `gpt-5-mini` + `reasoning.effort=medium`（`OPENAI_CLIENT_*` 環境変数で上書き）。  
  - `client_profiles.yaml`（または `CLIENT_PROFILES_PATH` 指定の YAML）からクライアント設定をロードし、内部状態の変動もログします。  
  - 対話終了時に `logs/session_human_counselor_client_cli_<timestamp>.csv` とクライアント評価 JSON を保存します（features/debug も含む）。

### DSPy 版カウンセラーと最適化
- `DsPy/mi_counselor_dspy.py` の `MIRhythmBotDSPy` は `ConversationEnvironment` と同じインタフェースで動く drop-in 版です。`MIRhythmBotDSPy.from_compiled(...)` に `compiled/*.json` を渡すと、学習済みプログラムをロードできます。  
- `DsPy/train_a_generation.py` / `train_b_estimators.py` / `train_c_session.py` はそれぞれ  
  - A: 発話生成、B: フェーズ＋チェンジトーク/抵抗推定、C: セッション全体 を DSPy の MIPROv2 で最適化します。  
  - 事前に `logs/*.csv`（`session_log_tools.save_log_csv` 形式）が必要です。無ければ `python cli.py human-client` や `python cli.py self-play` でログを作成してください。  
- データ作成・I/O は `DsPy/mi_dspy_data.py`、メトリクスは `DsPy/mi_dspy_metrics.py` を参照。コンパイル結果は `compiled/` に JSON で保存されます。

## ログ保存と解析（session_log_tools.py）

- 保存  
  - `save_log_jsonl(env, path)`（UTF-8）  
  - `save_log_csv(env, path)`（BOM付きUTF-8、phase/main_action/add_affirm/reflect_streak_before/r_since_q_before/features_json 付き）
- 解析  
  - `analyze_phases`（出現回数と遷移）、`analyze_actions`（頻度と REFLECT/QUESTION 比）、`analyze_reflect_streaks`（連続反射分布）  
  - `analyze_change_talk_responses` / `analyze_resistance_responses`（特徴量が閾値以上のときの行動分布）  
  - `print_basic_analysis` で上記をまとめてコンソール表示

## コアロジックのハイライト（mi_counselor_agent.py）

- **フェーズ管理**: `Phase` は 8フェーズ。`classify_phase_heuristic`（ルール）＋ `LLMPhaseClassifier`（任意、信頼度閾値付き）で更新。  
- **特徴量抽出 `extract_features`**: 質問/情報要求、許可可否（情報共有待ちのとき）、抵抗/チェンジトーク/新情報スコア、話題転換、要約推奨フラグ、反射上限解除可否などを計算。  
- **行動決定 `plan_next_action`**: 情報共有モードを優先しつつ、`r_since_q` や反射ストリーク、新情報・抵抗・チェンジトーク、フェーズのバイアスで REFLECT/QUESTION/SUMMARY をスコア化。必要なら確率をキャップし、LLM/DSPy の順位提案を軽くバイアスとして使用可能。  
- **是認付加 `decide_affirm`**: チェンジトークや新情報が強いとき、抵抗×新情報が強いときに是認を付加（近接ターンでは抑制）。  
- **状態更新 `apply_action_to_state`**: 反射ストリーク、質問間隔、要約間隔、是認間隔、情報共有モードを更新。  
- **プロンプト生成 `build_prompt`**: フェーズ別ガイダンスと主動作に応じた出力制約を System に書き、直近20発話を渡す。  
- **出力検査 `validate_output`**: 主動作に応じた最低限のバリデーション。失敗時は System で一度だけ修正指示。

## メモ

- `archive/` には旧版のバックアップが入っています。最新の動作は上記ファイル群（app/直下と DsPy/）を参照してください。
