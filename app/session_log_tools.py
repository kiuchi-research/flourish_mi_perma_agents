from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    # 実行時にはインポートしない（循環依存を避けるため）
    from conversation_environment import ConversationTurn
    from mi_counselor_agent import LLMClient


# ==============================
# Protocol for session log handling
# ==============================

class SupportsConversationTurn(Protocol):
    speaker: str
    text: str
    meta: Optional[Dict[str, Any]]


class SupportsSessionLog(Protocol):
    """
    session_log_tools が受け付ける最小限のインタフェース。
    - log: ConversationTurn 互換の配列（speaker/text/meta があればOK）
    - session_meta: セッション共通メタデータ（任意のMapping）
    - to_json_serializable(): JSON保存用のレコード配列を返す
    """

    log: Sequence[SupportsConversationTurn]
    session_meta: Mapping[str, Any]

    def to_json_serializable(self) -> List[Dict[str, Any]]:
        ...


def _to_json_records(env: SupportsSessionLog) -> List[Dict[str, Any]]:
    """to_json_serializable() の実行と簡易検証を一元化。"""
    records = env.to_json_serializable()
    if not isinstance(records, list):
        raise TypeError("to_json_serializable() は list を返す必要があります。")
    return records


# ==============================
# 保存系：JSONL / CSV
# ==============================

def save_log_jsonl(env: SupportsSessionLog, path: str) -> None:
    """
    SupportsSessionLog 互換のセッションログを JSONL 形式で保存します。
    - 1行1発話（ConversationTurn）となるように json を書き出します。
    - 文字コードは UTF-8（BOM なし）です。
    """
    records = _to_json_records(env)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")


def save_log_csv(env: SupportsSessionLog, path: str) -> None:
    """
    SupportsSessionLog 互換のセッションログを CSV 形式で保存します。
    - 文字コードは BOM 付き UTF-8（Excel などで文字化けしにくくするため）。
    - 各行は 1発話（ConversationTurn）です。
    - counselor 発話のときだけ phase / main_action / add_affirm / debug 情報が入ります。
    - session_meta（session_id / mode / model / planner_config など）があれば各行に付与します。
    """
    records = _to_json_records(env)

    fieldnames = [
        "index",
        "speaker",
        "text",
        "session_id",
        "session_mode",
        "openai_model",
        "client_code",
        "client_pattern",
        "client_pattern_label",
        "client_primary_focus",
        "client_primary_focus_label",
        "client_interpersonal_style",
        "client_interpersonal_style_label",
        "client_profiles_path",
        "planner_config_json",
        "phase",
        "main_action",
        "add_affirm",
        "reflect_streak_before",
        "r_since_q_before",
        "features_json",
        "client_internal_state_json",
        "client_internal_state_reason_json",
        "client_meta_json",
        "client_raw",
        "client_parse_status",
    ]

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, rec in enumerate(records):
            meta = rec.get("meta") or {}
            debug = meta.get("debug") or {}
            features = debug.get("features") or None
            features_json = json.dumps(features, ensure_ascii=False) if features is not None else ""
            client_state = meta.get("client_internal_state") or None
            client_state_json = json.dumps(client_state, ensure_ascii=False) if client_state is not None else ""
            client_state_reason = meta.get("client_internal_state_reason") or None
            client_state_reason_json = (
                json.dumps(client_state_reason, ensure_ascii=False) if client_state_reason is not None else ""
            )
            client_meta_extra = meta.get("client_meta") or None
            client_meta_json = json.dumps(client_meta_extra, ensure_ascii=False) if client_meta_extra is not None else ""
            client_raw = meta.get("client_raw", "")
            client_parse_status = meta.get("parse_status", "")
            session_meta = rec.get("session_meta") or {}
            planner_cfg = session_meta.get("planner_config")
            planner_json = json.dumps(planner_cfg, ensure_ascii=False) if planner_cfg is not None else ""
            client_profiles_path = session_meta.get("client_profiles_path") or session_meta.get("clients_yaml_path", "")

            row = {
                "index": idx,
                "speaker": rec.get("speaker"),
                "text": rec.get("text"),
                "session_id": session_meta.get("session_id", ""),
                "session_mode": session_meta.get("session_mode", ""),
                "openai_model": session_meta.get("openai_model", ""),
                "client_code": session_meta.get("client_code", ""),
                "client_pattern": session_meta.get("client_pattern", ""),
                "client_pattern_label": session_meta.get("client_pattern_label", ""),
                "client_primary_focus": session_meta.get("client_primary_focus", ""),
                "client_primary_focus_label": session_meta.get("client_primary_focus_label", ""),
                "client_interpersonal_style": session_meta.get("client_interpersonal_style", ""),
                "client_interpersonal_style_label": session_meta.get("client_interpersonal_style_label", ""),
                "client_profiles_path": client_profiles_path,
                "planner_config_json": planner_json,
                "phase": meta.get("phase", ""),
                "main_action": meta.get("main_action", ""),
                "add_affirm": meta.get("add_affirm", ""),
                "reflect_streak_before": debug.get("reflect_streak"),
                "r_since_q_before": debug.get("r_since_q"),
                "features_json": features_json,
                "client_internal_state_json": client_state_json,
                "client_internal_state_reason_json": client_state_reason_json,
                "client_meta_json": client_meta_json,
                "client_raw": client_raw,
                "client_parse_status": client_parse_status,
            }
            writer.writerow(row)


def finalize_session(
    env: SupportsSessionLog,
    llm: "LLMClient",
    *,
    log_prefix: str,
    logs_dir: Optional[Path] = None,
) -> Dict[str, str]:
    """
    CSV ログとクライアント視点評価 JSON をまとめて保存する共通関数。
    戻り値: {"csv": <path>, "client_eval": <path>}
    """
    if not getattr(env, "log", None):
        return {}

    base_dir = logs_dir or (Path(__file__).resolve().parent / "logs")
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = base_dir / f"{log_prefix}_{timestamp}.csv"
    save_log_csv(env, str(csv_path))
    print(f"ログを保存しました: {csv_path}")

    client_eval = evaluate_session_from_client_pov(env, llm)
    eval_path = base_dir / f"{log_prefix}_{timestamp}_client_eval.json"
    save_client_evaluation_json(client_eval, str(eval_path))
    print(f"クライアント評価を保存しました: {eval_path}")

    return {"csv": str(csv_path), "client_eval": str(eval_path)}


# ==============================
# 解析系：フェーズ・アクション・ストリーク
# ==============================

@dataclass
class PhaseAnalysis:
    phase_counts: Dict[str, int]
    transitions: Dict[str, int]  # "A->B" : count


@dataclass
class ActionAnalysis:
    action_counts: Dict[str, int]
    reflect_count: int
    question_count: int
    total_counselor_turns: int
    reflect_ratio: Optional[float]
    question_ratio: Optional[float]


@dataclass
class ReflectStreakAnalysis:
    streaks: List[int]                  # 各ストリークの長さ（1,2,3,...）
    distribution: Dict[int, int]        # 長さ -> 出現回数
    max_streak: int
    mean_streak: float


@dataclass
class ConditionalActionAnalysis:
    """
    「ある条件を満たすターンに対して、どの main_action が選ばれているか」
    を集計した結果（チェンジトークあり/抵抗あり のとき用）。
    """
    label: str                  # "change_talk" など
    threshold: float            # この値以上を「あり」とみなした閾値
    total_turns: int            # 条件を満たした counselor ターン数
    action_counts: Dict[str, int]
    action_ratios: Dict[str, float]


def analyze_phases(env: SupportsSessionLog) -> PhaseAnalysis:
    """
    ログからフェーズ推移を解析します。
    - 各フェーズの出現回数
    - フェーズ遷移 (A -> B) の回数
    """
    phases: List[str] = []
    for turn in env.log:
        if turn.speaker != "counselor" or not turn.meta:
            continue
        ph = turn.meta.get("phase")
        if ph:
            phases.append(ph)

    phase_counts = Counter(phases)

    transitions: Counter[Tuple[str, str]] = Counter()
    for i in range(len(phases) - 1):
        a = phases[i]
        b = phases[i + 1]
        transitions[(a, b)] += 1

    transitions_str: Dict[str, int] = {
        f"{a}->{b}": c for (a, b), c in transitions.items()
    }

    return PhaseAnalysis(
        phase_counts=dict(phase_counts),
        transitions=transitions_str,
    )


def analyze_actions(env: SupportsSessionLog) -> ActionAnalysis:
    """
    ログから main_action（REFLECT / QUESTION / SUMMARY / ASK_PERMISSION /
    PROVIDE_INFO など）の頻度と、
    反射 vs 質問 の比率を解析します。
    """
    actions: List[str] = []
    for turn in env.log:
        if turn.speaker != "counselor" or not turn.meta:
            continue
        act = turn.meta.get("main_action")
        if act:
            actions.append(act)

    counts = Counter(actions)
    reflect_count = counts.get("REFLECT", 0)
    question_count = counts.get("QUESTION", 0)
    total_counselor_turns = len(actions)

    rq_total = reflect_count + question_count
    if rq_total > 0:
        reflect_ratio = reflect_count / rq_total
        question_ratio = question_count / rq_total
    else:
        reflect_ratio = None
        question_ratio = None

    return ActionAnalysis(
        action_counts=dict(counts),
        reflect_count=reflect_count,
        question_count=question_count,
        total_counselor_turns=total_counselor_turns,
        reflect_ratio=reflect_ratio,
        question_ratio=question_ratio,
    )


def analyze_reflect_streaks(env: SupportsSessionLog) -> ReflectStreakAnalysis:
    """
    ログから「REFLECT が何回連続するか」のストリーク分布を解析します。
    例：
      REFLECT, REFLECT, QUESTION, REFLECT, SUMMARY
      -> ストリーク長 [2, 1]
    """
    streaks: List[int] = []
    current = 0

    for turn in env.log:
        if turn.speaker != "counselor" or not turn.meta:
            # counselor 以外 or meta なしのときはストリークを切る
            if current > 0:
                streaks.append(current)
                current = 0
            continue

        act = turn.meta.get("main_action")
        if act == "REFLECT":
            current += 1
        else:
            if current > 0:
                streaks.append(current)
                current = 0

    if current > 0:
        streaks.append(current)

    dist_counter: Counter[int] = Counter(streaks)
    distribution = dict(sorted(dist_counter.items(), key=lambda kv: kv[0]))
    max_streak = max(streaks) if streaks else 0
    mean_streak = (sum(streaks) / len(streaks)) if streaks else 0.0

    return ReflectStreakAnalysis(
        streaks=streaks,
        distribution=distribution,
        max_streak=max_streak,
        mean_streak=mean_streak,
    )


# ==============================
# クライアント内部状態ログ → 時系列データ
# ==============================

def collect_client_internal_trajectory(env: SupportsSessionLog) -> List[Dict[str, Any]]:
    """
    セッションログから「クライアント発話ごとの内部状態」の時系列を取り出します。

    戻り値の各要素は
      {
        "index": 発話インデックス（env.log 内の位置）,
        "text": そのときのクライアント発話,
        "internal_state": { ... } または None
      }
    の形になります。
    """
    trajectory: List[Dict[str, Any]] = []

    for idx, turn in enumerate(env.log):
        if turn.speaker != "client":
            continue
        state = None
        if turn.meta:
            state = turn.meta.get("client_internal_state")
        trajectory.append(
            {
                "index": idx,
                "text": turn.text,
                "internal_state": state,
            }
        )

    return trajectory


# ==============================
# 解析系：チェンジトーク／抵抗 → 次アクション
# ==============================

def _collect_conditional_actions(
    env: SupportsSessionLog,
    feature_key: str,
    threshold: float,
    label: str,
) -> ConditionalActionAnalysis:
    """
    feature_key（'change_talk' / 'resistance'）の値が threshold 以上の
    counselor ターンについて、main_action の分布を集計します。

    - feature は MIRhythmBot の Decision.meta["debug"]["features"] に
      格納されている前提です。
    """
    actions: List[str] = []

    for turn in env.log:
        if turn.speaker != "counselor" or not turn.meta:
            continue
        meta = turn.meta or {}
        debug = meta.get("debug") or {}
        features = debug.get("features") or {}
        value = features.get(feature_key)
        if value is None:
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue

        if v >= threshold:
            act = meta.get("main_action")
            if act:
                actions.append(act)

    counts = Counter(actions)
    total = sum(counts.values())
    if total > 0:
        ratios = {k: c / total for k, c in counts.items()}
    else:
        ratios = {}

    return ConditionalActionAnalysis(
        label=label,
        threshold=threshold,
        total_turns=total,
        action_counts=dict(counts),
        action_ratios=ratios,
    )


def analyze_change_talk_responses(
    env: SupportsSessionLog,
    threshold: float = 0.6,
) -> ConditionalActionAnalysis:
    """
    チェンジトーク（features['change_talk']）が threshold 以上のターンで、
    カウンセラーがどの main_action を選んでいるかを集計します。
    """
    return _collect_conditional_actions(
        env=env,
        feature_key="change_talk",
        threshold=threshold,
        label="change_talk",
    )


def analyze_resistance_responses(
    env: SupportsSessionLog,
    threshold: float = 0.6,
) -> ConditionalActionAnalysis:
    """
    抵抗（features['resistance']）が threshold 以上のターンで、
    カウンセラーがどの main_action を選んでいるかを集計します。
    """
    return _collect_conditional_actions(
        env=env,
        feature_key="resistance",
        threshold=threshold,
        label="resistance",
    )


# ==============================
# 結果をざっくり表示するユーティリティ
# ==============================

def print_basic_analysis(env: SupportsSessionLog) -> None:
    """
    フェーズ・アクション・反射ストリークに加えて、
    「チェンジトーク／抵抗が強いターンで次に何をしているか」
    も含めてざっくり統計をコンソールに出力します。
    """
    pa = analyze_phases(env)
    aa = analyze_actions(env)
    ra = analyze_reflect_streaks(env)

    ct_analysis = analyze_change_talk_responses(env, threshold=0.6)
    rs_analysis = analyze_resistance_responses(env, threshold=0.6)

    print("=== Phase Counts ===")
    for ph, c in pa.phase_counts.items():
        print(f"  {ph}: {c}")

    print("\n=== Phase Transitions ===")
    for k, v in pa.transitions.items():
        print(f"  {k}: {v}")

    print("\n=== Action Counts (overall) ===")
    for act, c in aa.action_counts.items():
        print(f"  {act}: {c}")
    print(f"  total counselor turns: {aa.total_counselor_turns}")
    if aa.reflect_ratio is not None:
        print(
            f"  REFLECT vs QUESTION = "
            f"{aa.reflect_count} vs {aa.question_count} "
            f"(ratio: {aa.reflect_ratio:.2f} / {aa.question_ratio:.2f})"
        )
    else:
        print("  REFLECT / QUESTION がほとんどありません。")

    print("\n=== Reflect Streaks ===")
    print(f"  streaks (per run): {ra.streaks}")
    print(f"  distribution (length -> count): {ra.distribution}")
    print(f"  max_streak: {ra.max_streak}")
    print(f"  mean_streak: {ra.mean_streak:.2f}")

    # ---- チェンジトークに対する応答 ----
    print("\n=== Responses to Change Talk ===")
    print(
        f"  condition: change_talk >= {ct_analysis.threshold:.2f}, "
        f"turns: {ct_analysis.total_turns}"
    )
    if ct_analysis.total_turns == 0:
        print("  該当ターンがありません。")
    else:
        for act, count in ct_analysis.action_counts.items():
            r = ct_analysis.action_ratios.get(act, 0.0)
            print(f"  {act}: {count} (ratio: {r:.2f})")

    # ---- 抵抗に対する応答 ----
    print("\n=== Responses to Resistance ===")
    print(
        f"  condition: resistance >= {rs_analysis.threshold:.2f}, "
        f"turns: {rs_analysis.total_turns}"
    )
    if rs_analysis.total_turns == 0:
        print("  該当ターンがありません。")
    else:
        for act, count in rs_analysis.action_counts.items():
            r = rs_analysis.action_ratios.get(act, 0.0)
            print(f"  {act}: {count} (ratio: {r:.2f})")


# ==============================
# クライアント視点のセッション評価（LLM 使用）
# ==============================

def evaluate_session_from_client_pov(
    env: SupportsSessionLog,
    llm: "LLMClient",
    *,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    クライアントの内部状態ログとセッション全体のやり取りを LLM に渡して、
    「クライアント本人の主観的評価（数値＋記述）」を JSON で生成してもらう関数。

    - ratings: 0〜10 の評価値（必要に応じて拡張可）
    - comment: 短いコメント（2〜4文）
    - long_comment: より詳しいコメント（省略可）
    """
    session_id = env.session_meta.get("session_id", "")

    # セッションログを、LLM に渡しやすいテキストに整形
    lines: List[str] = []
    for idx, turn in enumerate(env.log):
        if turn.speaker == "client":
            state = (turn.meta or {}).get("client_internal_state")
            state_str = json.dumps(state, ensure_ascii=False) if state is not None else ""
            lines.append(f"[{idx:02d}] client    : {turn.text}")
            if state_str:
                lines.append(f"       internal_state: {state_str}")
        else:
            lines.append(f"[{idx:02d}] counselor: {turn.text}")

    prompt = (
        "あなたはカウンセリング研究者です。\n"
        "以下は、クライアントとカウンセラーの1セッション分の対話ログです。\n"
        "クライアント発話には、そのときの内部状態を表す 0〜10 のスコアが付与されている場合があります。"
        "欠損している場合は文脈から推測して構いません。\n"
        "この情報をもとに、クライアント本人の視点からセッション全体を評価してください。\n\n"
        "出力は必ず次の JSON 形式「だけ」で返してください:\n"
        "{\n"
        '  "ratings": {\n'
        '    "overall_satisfaction": 0〜10の数値,\n'
        '    "goal_importance": 0〜10の数値,\n'
        '    "goal_confidence": 0〜10の数値,\n'
        '    "alliance_bond": 0〜10の数値,\n'
        '    "positive_affect": 0〜10の数値,\n'
        '    "negative_affect": 0〜10の数値\n'
        "  },\n"
        '  "comment": "日本語での短いコメント（2〜4文程度）",\n'
        '  "long_comment": "必要なら、もう少し詳しいコメント（省略可）"\n'
        "}\n\n"
        "=== セッションログ ===\n"
        + "\n".join(lines)
    )

    messages = [{"role": "user", "content": prompt}]
    raw = llm.generate(messages, temperature=float(temperature))
    text = str(raw).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # LLM がうっかり JSON 以外を返したときのフォールバック
        data = {
            "ratings": {},
            "comment": "",
            "long_comment": text,
        }

    data.setdefault("session_id", session_id)
    return data


def save_client_evaluation_json(evaluation: Dict[str, Any], path: str) -> None:
    """
    evaluate_session_from_client_pov の結果を JSON ファイルに保存する簡易ユーティリティ。
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)


# ==============================
# 簡単なデモ
# ==============================

def _demo() -> None:
    """
    conversation_environment.demo_two_agents() などで作られた env を想定して、
    解析と保存を一通り走らせるミニデモです。
    実際には、あなたの環境で対話を終えた ConversationEnvironment を
    渡して使ってください。
    """
    from mi_counselor_agent import MIRhythmBot, DummyLLM
    from conversation_environment import ConversationEnvironment
    from perma_client_agent import SimpleClientLLM

    counselor = MIRhythmBot(llm=DummyLLM())
    client = SimpleClientLLM(llm=DummyLLM())
    env = ConversationEnvironment(counselor=counselor, client=client)

    # 簡単なシミュレーション
    env.simulate(
        first_client_utterance="最近、生活リズムが崩れてしまって、気持ちも落ち込んでいます。",
        max_turns=5,
    )

    # 解析結果を表示
    print_basic_analysis(env)

    # JSONL / CSV に保存（ファイル名は例ですので、適宜変更してください）
    save_log_jsonl(env, "session_example.jsonl")
    save_log_csv(env, "session_example.csv")


if __name__ == "__main__":
    _demo()
