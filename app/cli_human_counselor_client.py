import os
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from env_utils import build_llm_from_config, get_model_config, load_openai_api_key
from perma_client_agent import SimpleClientLLM
from conversation_environment import ConversationTurn, ManualConversationEnvironment
from session_log_tools import finalize_session
from mi_counselor_agent import (
    DialogueState,
    InfoMode,
    LLMClient,
    LLMPhaseClassifier,
    MainAction,
    Phase,
    PlannerConfig,
    apply_action_to_state,
    extract_features,
)


# =========================
# client_profiles.yaml loader / scenario builder
# =========================

def _find_client_profiles_path() -> Path:
    """client_profiles.yaml のパスを決める。

    探索順:
      1) 環境変数 CLIENT_PROFILES_PATH / CLIENTS_YAML_PATH / CLIENTS_YAML
      2) このスクリプトと同じディレクトリ（client_profiles.yaml → 旧 clients.yaml）
      3) 1つ上のディレクトリ（同上）
      4) カレントディレクトリ（同上）

    見つからない場合は FileNotFoundError。
    """

    env_path = (
        os.getenv("CLIENT_PROFILES_PATH")
        or os.getenv("CLIENTS_YAML_PATH")
        or os.getenv("CLIENTS_YAML")
    )
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.is_file():
            return p
        raise FileNotFoundError(f"client_profiles.yaml が見つかりません（環境変数指定）: {p}")

    candidates = [
        Path(__file__).resolve().parent / "client_profiles.yaml",
        Path(__file__).resolve().parent.parent / "client_profiles.yaml",
        Path.cwd() / "client_profiles.yaml",
        # 互換用（旧ファイル名）
        Path(__file__).resolve().parent / "clients.yaml",
        Path(__file__).resolve().parent.parent / "clients.yaml",
        Path.cwd() / "clients.yaml",
    ]

    for p in candidates:
        if p.is_file():
            return p

    tried = "\n".join([f"- {c}" for c in candidates])
    raise FileNotFoundError(
        "client_profiles.yaml が見つかりません。次の場所を探しました:\n"
        + tried
        + "\n\n必要なら、CLIENT_PROFILES_PATH=/path/to/client_profiles.yaml を指定してください。"
    )


def _load_client_profiles_yaml(path: Path) -> Dict[str, Any]:
    """client_profiles.yaml を読み込んで dict を返す。"""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _get_client_profile(cfg: Dict[str, Any], client_code: str) -> Dict[str, Any]:
    """cfg['clients'][client_code] を取得（存在しなければエラー）。"""
    clients = cfg.get("clients")
    if not isinstance(clients, dict):
        raise KeyError("client_profiles.yaml に 'clients' セクションがありません。")

    code = (client_code or "").strip()
    if code not in clients:
        available = ", ".join(sorted([str(k) for k in clients.keys()]))
        raise KeyError(f"client_profiles.yaml に client_code={code} がありません。利用可能: {available}")

    profile = clients.get(code)
    if not isinstance(profile, dict):
        raise TypeError(f"client_profiles.yaml の clients.{code} が dict ではありません。")

    return profile


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _derive_client_meta(profile: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, str]:
    """コード（M1/S1/Pなど）を definitions で展開し、表示用メタを作る。"""
    defs = cfg.get("definitions")
    defs = defs if isinstance(defs, dict) else {}

    perma_defs = defs.get("perma")
    perma_defs = perma_defs if isinstance(perma_defs, dict) else {}

    style_defs = defs.get("interpersonal_styles")
    style_defs = style_defs if isinstance(style_defs, dict) else {}

    pattern_defs = defs.get("perma_focus_patterns")
    pattern_defs = pattern_defs if isinstance(pattern_defs, dict) else {}

    pattern_code = _safe_str(profile.get("pattern"))
    pattern_info = pattern_defs.get(pattern_code)
    pattern_info = pattern_info if isinstance(pattern_info, dict) else {}
    pattern_label = _safe_str(pattern_info.get("label")) or pattern_code

    primary_focus_code = _safe_str(pattern_info.get("primary_focus"))
    primary_focus_label = _safe_str(perma_defs.get(primary_focus_code)) or primary_focus_code

    interpersonal_style_code = _safe_str(profile.get("interpersonal_style"))
    style_info = style_defs.get(interpersonal_style_code)
    style_info = style_info if isinstance(style_info, dict) else {}
    interpersonal_label = _safe_str(style_info.get("label")) or interpersonal_style_code
    interpersonal_brief = _safe_str(style_info.get("brief"))

    meta = {
        "pattern_code": pattern_code,
        "pattern_label": pattern_label,
        "primary_focus_code": primary_focus_code,
        "primary_focus_label": primary_focus_label,
        "interpersonal_style_code": interpersonal_style_code,
        "interpersonal_style_label": interpersonal_label,
        "interpersonal_style_brief": interpersonal_brief,
    }
    return meta


def _resolve_client_llm_style(*, env_style: str, interpersonal_style_code: str) -> str:
    """SimpleClientLLM.style（cooperative/ambivalent/resistant）を決める。

    - env_style が 'auto' のときは interpersonal_style_code（S1/S2/S3）から推定
    - それ以外は env_style を優先
    """

    s = (env_style or "auto").strip().lower()
    if s in ("cooperative", "ambivalent", "resistant"):
        return s

    # auto 推定
    code = (interpersonal_style_code or "").strip()
    mapping = {
        "S1": "cooperative",  # 内省・協力型
        "S2": "resistant",    # 防衛・懐疑型
        "S3": "cooperative",  # 助言志向・せっかち型（探索が長いと焦れやすいが、敵対とは限らない）
    }
    return mapping.get(code, "cooperative")


def _format_perma_baseline(baseline_perma: Any, cfg: Dict[str, Any]) -> List[str]:
    """baseline_perma（P/E/R/M/A）を definitions.perma を使って整形。"""
    defs = cfg.get("definitions")
    defs = defs if isinstance(defs, dict) else {}
    perma_defs = defs.get("perma")
    perma_defs = perma_defs if isinstance(perma_defs, dict) else {}

    if not isinstance(baseline_perma, dict):
        return []

    lines: List[str] = []
    order = ["P", "E", "R", "M", "A"]

    for k in order:
        if k not in baseline_perma:
            continue
        name = _safe_str(perma_defs.get(k)) or k
        try:
            v = float(baseline_perma.get(k))
            # 整数っぽいなら整数表示
            if abs(v - int(v)) < 1e-9:
                v_str = str(int(v))
            else:
                v_str = str(v)
        except Exception:
            v_str = _safe_str(baseline_perma.get(k))
        lines.append(f"- {name} [{k}]: {v_str}")

    # 追加キーがあれば後ろに
    for k, v in baseline_perma.items():
        if str(k) in order:
            continue
        name = _safe_str(perma_defs.get(str(k))) or str(k)
        lines.append(f"- {name} [{k}]: {v}")

    return lines


def _format_trait_expression(trait_expression: Any) -> List[str]:
    """trait_expression_*（-1/0/1）を読みやすく整形。"""
    if not isinstance(trait_expression, dict):
        return []

    desc = {
        -1: "出にくい",
        0: "標準",
        1: "出やすい",
    }

    label_map = {
        "trait_expression_pos": "pos_affect（ポジティブ感情）",
        "trait_expression_neg": "neg_affect（ネガティブ感情）",
        "trait_expression_importance": "importance_change（重要度）",
        "trait_expression_confidence": "confidence_change（自信）",
        "trait_expression_like": "like_counselor（好感）",
        "trait_expression_tension": "tension_counselor（緊張/不和）",
    }

    order = list(label_map.keys())
    lines: List[str] = []

    for k in order:
        if k not in trait_expression:
            continue
        try:
            v = float(trait_expression.get(k))
        except Exception:
            v = 0.0

        # -1/0/1 として表示（微妙な値が来た場合は丸める）
        if v <= -0.5:
            vi = -1
        elif v >= 0.5:
            vi = 1
        else:
            vi = 0

        label = label_map.get(k, k)
        lines.append(f"- {label}: {vi}（{desc.get(vi, '標準')}）")

    return lines


def _build_client_scenario_text(
    client_code: str,
    profile: Dict[str, Any],
    cfg: Dict[str, Any],
    meta: Dict[str, str],
) -> str:
    """SimpleClientLLM.scenario に渡すテキストを組み立てる。

    ここで「M1」「S1」「P/E/R/M/A」などのコードを definitions で展開し、
    LLM が誤解しにくい、読みやすい形にして渡します。
    """

    lines: List[str] = []

    # ---- 設定（コード + 展開） ----
    lines.append("【クライアント設定】")
    lines.append(f"- client_code: {client_code}")

    pattern_code = meta.get("pattern_code", "")
    pattern_label = meta.get("pattern_label", "")
    pf_code = meta.get("primary_focus_code", "")
    pf_label = meta.get("primary_focus_label", "")

    if pattern_code:
        if pf_code and pf_label:
            lines.append(f"- pattern: {pattern_code}（{pattern_label}） / primary_focus: {pf_code}（{pf_label}）")
        else:
            lines.append(f"- pattern: {pattern_code}（{pattern_label}）")

    is_code = meta.get("interpersonal_style_code", "")
    is_label = meta.get("interpersonal_style_label", "")
    is_brief = meta.get("interpersonal_style_brief", "")
    if is_code:
        if is_brief:
            lines.append(f"- interpersonal_style: {is_code}（{is_label}）: {is_brief}")
        else:
            lines.append(f"- interpersonal_style: {is_code}（{is_label}）")

    # ---- 背景 ----
    bg = profile.get("background")
    bg = bg if isinstance(bg, dict) else {}
    bg_lines: List[str] = []
    age = _safe_str(bg.get("age_range"))
    occ = _safe_str(bg.get("occupation_context"))
    living = _safe_str(bg.get("living_situation"))
    notes = _safe_str(bg.get("notes"))

    if age:
        bg_lines.append(f"- 年代: {age}")
    if occ:
        bg_lines.append(f"- 仕事文脈: {occ}")
    if living:
        bg_lines.append(f"- 生活状況: {living}")
    if notes:
        bg_lines.append(f"- 補足: {notes}")

    if bg_lines:
        lines.append("")
        lines.append("【背景】")
        lines.extend(bg_lines)

    # ---- 主訴 ----
    pc = _safe_str(profile.get("presenting_concern"))
    if pc:
        lines.append("")
        lines.append("【主訴】")
        lines.append(pc)

    # ---- 事前想定 PERMA ----
    baseline_perma = profile.get("baseline_perma")
    perma_lines = _format_perma_baseline(baseline_perma, cfg)
    if perma_lines:
        lines.append("")
        lines.append("【事前PERMA想定（0〜10）】")
        lines.extend(perma_lines)

    # ---- 強み/資源 ----
    strengths = profile.get("strengths_resources")
    if isinstance(strengths, list) and strengths:
        lines.append("")
        lines.append("【強み/資源】")
        for s in strengths:
            st = _safe_str(s)
            if st:
                lines.append(f"- {st}")

    # ---- 維持サイクル ----
    mc = _safe_str(profile.get("maintaining_cycle"))
    if mc:
        lines.append("")
        lines.append("【維持サイクル】")
        lines.append(mc)

    # ---- セッション目標 ----
    sg = _safe_str(profile.get("session_goal"))
    if sg:
        lines.append("")
        lines.append("【このセッションの目標】")
        lines.append(sg)

    # ---- 安全性 ----
    safety = profile.get("safety")
    safety = safety if isinstance(safety, dict) else {}
    if safety:
        lines.append("")
        lines.append("【安全性】")
        ac = safety.get("acute_crisis")
        si = safety.get("suicidal_ideation")
        if ac is not None:
            lines.append(f"- acute_crisis: {bool(ac)}")
        if si is not None:
            lines.append(f"- suicidal_ideation: {bool(si)}")

    # ---- 出やすさ特性（trait_expression_*） ----
    te = profile.get("trait_expression")
    te_lines = _format_trait_expression(te)
    if te_lines:
        lines.append("")
        lines.append("【発話としての出やすさ特性（-1/0/+1）】")
        lines.extend(te_lines)

    return "\n".join(lines).strip()


def _apply_trait_expression_to_client(client: Any, profile: Dict[str, Any]) -> None:
    """profile.trait_expression を SimpleClientLLM.internal_state に反映する。"""
    te = profile.get("trait_expression")
    if not isinstance(te, dict):
        return

    internal_state = getattr(client, "internal_state", None)
    if internal_state is None:
        return

    for k, v in te.items():
        if not hasattr(internal_state, str(k)):
            continue
        try:
            setattr(internal_state, str(k), float(v))
        except Exception:
            # 数値変換できないものは無視
            continue

# =========================
# LLM action classifier (for counselor utterance)
# =========================
_ACTION_LABELS = [a.value for a in MainAction]


def _extract_first_json_object(text: str) -> Optional[str]:
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    return m.group(0)


def _heuristic_add_affirm(counselor_text: str) -> bool:
    # かなり雑なヒューリスティック（失敗時のフォールバック用）
    markers = ["工夫", "努力", "頑張", "大事に", "大切に", "強み", "前進", "できて", "良いですね"]
    return any(m in counselor_text for m in markers)


def _heuristic_action(counselor_text: str) -> MainAction:
    t = counselor_text.strip()
    if not t:
        return MainAction.REFLECT

    # ASK_PERMISSION を先に判定（"してもよろしいですか" 等）
    if any(k in t for k in ["よろしいでしょうか", "よろしいですか", "してもいい", "してもよい", "差し支え", "共有しても"]):
        if ("？" in t) or ("?" in t) or ("ですか" in t) or ("でしょうか" in t):
            return MainAction.ASK_PERMISSION

    # PROVIDE_INFO（情報提示っぽい）
    if any(k in t for k in ["例えば", "一般に", "方法", "コツ", "選択肢", "ポイント", "目安"]):
        return MainAction.PROVIDE_INFO

    # SUMMARY（まとめ）
    if any(k in t for k in ["まとめると", "要するに", "ここまで", "整理すると"]):
        return MainAction.SUMMARY

    # QUESTION
    if ("？" in t) or ("?" in t) or t.endswith("ですか") or t.endswith("でしょうか"):
        return MainAction.QUESTION

    return MainAction.REFLECT


class LLMActionClassifier:
    """
    人間カウンセラーの発話を、LLMにより MainAction + add_affirm に分類します。
    （ラベルデータ作成のための自動アノテーション）
    """

    def __init__(self, llm: LLMClient, *, temperature: float = 0.0, max_history_turns: int = 8):
        self.llm = llm
        self.temperature = float(temperature)
        self.max_history_turns = int(max_history_turns)

    def classify(
        self,
        *,
        phase: Phase,
        last_client_text: str,
        counselor_text: str,
        history: List[Tuple[str, str]],
    ) -> Tuple[MainAction, bool, Dict[str, Any]]:
        """
        返り値:
          - main_action
          - add_affirm
          - debug
        """
        labels = " / ".join(_ACTION_LABELS)

        # 履歴（短縮）
        lines: List[str] = []
        for role, text in history[-self.max_history_turns :]:
            prefix = "Client" if role == "user" else "Counselor"
            lines.append(f"{prefix}: {text}")
        dialogue = "\n".join(lines)

        system = (
            "あなたは対話ログのアノテーション担当です。\n"
            "次のカウンセラー発話を、MI（動機づけ面接）のOARSに沿う行動ラベルへ分類します。\n"
            "\n"
            f"【main_action ラベル】{labels}\n"
            "\n"
            "【ラベル定義（短縮）】\n"
            "- REFLECT: 相手の言葉/感情/価値の言い換え・反射。基本的に質問しない。\n"
            "- QUESTION: 1つの質問（情報収集・掘り下げ）。\n"
            "- SUMMARY: ここまでの要点をまとめる。\n"
            "- ASK_PERMISSION: 情報提供/提案の前に許可を取る。\n"
            "- PROVIDE_INFO: 中立に情報・選択肢・提案を提示し、最後に反応を尋ねてもよい。\n"
            "\n"
            "【add_affirm】\n"
            "- True: 努力/工夫/強み/価値観/前進を具体的に認める一言が含まれる\n"
            "- False: それ以外\n"
            "\n"
            "【出力形式】\n"
            "- 余計な文章は書かず、次の JSON だけを1行で出力してください。\n"
            '  例: {"main_action":"REFLECT","add_affirm":false}\n'
        )

        user = (
            f"【フェーズ】{phase.value}\n"
            f"【直近の対話】\n{dialogue}\n"
            "\n"
            f"【直近のクライアント発話】{last_client_text}\n"
            f"【分類対象のカウンセラー発話】{counselor_text}\n"
            "\n"
            "出力："
        )

        raw = self.llm.generate(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.temperature,
        )
        raw = str(raw).strip()

        main_action: Optional[MainAction] = None
        add_affirm: Optional[bool] = None

        # JSONパース
        try:
            js = _extract_first_json_object(raw) or raw
            obj = json.loads(js)
            ma = str(obj.get("main_action", "")).strip()
            af = obj.get("add_affirm", None)

            if ma in _ACTION_LABELS:
                main_action = MainAction(ma)

            if isinstance(af, bool):
                add_affirm = af
            elif isinstance(af, (int, float)):
                add_affirm = bool(af)

        except Exception:
            pass

        # フォールバック
        if main_action is None:
            main_action = _heuristic_action(counselor_text)
        if add_affirm is None:
            add_affirm = _heuristic_add_affirm(counselor_text)

        debug = {
            "raw": raw,
            "main_action": main_action.value,
            "add_affirm": bool(add_affirm),
        }
        return main_action, bool(add_affirm), debug


# =========================
# main loop
# =========================
def main(
    *,
    script_name: str = "human_counselor_client_cli",
    log_prefix: str = "session_human_counselor_client_cli",
) -> None:
    api_key = load_openai_api_key()
    phase_cfg = get_model_config(
        "human_counselor_phase_classifier",
        role="counselor",
    )
    action_cfg = get_model_config(
        "human_counselor_action_classifier",
        role="counselor",
    )
    client_cfg = get_model_config("human_counselor_client", role="client")
    client_state_cfg = get_model_config(
        "human_counselor_client_state",
        role="client",
        fallback_modes=["human_counselor_client"],
    )
    client_reply_cfg = get_model_config(
        "human_counselor_client_reply",
        role="client",
        fallback_modes=["human_counselor_client"],
    )
    # ---- client_profiles.yaml からクライアント特性をロード ----
    client_code = (os.getenv("CLIENT_CODE") or "C01").strip() or "C01"
    client_profiles_path = _find_client_profiles_path()
    clients_cfg = _load_client_profiles_yaml(client_profiles_path)
    client_profile = _get_client_profile(clients_cfg, client_code)
    derived_meta = _derive_client_meta(client_profile, clients_cfg)
    scenario = _build_client_scenario_text(client_code, client_profile, clients_cfg, derived_meta)

    # CLIENT_STYLE=auto（既定）のときは interpersonal_style（S1/S2/S3）から推定します。
    # 例: CLIENT_STYLE=resistant など明示指定があればそれを優先します。
    client_style = _resolve_client_llm_style(
        env_style=os.getenv("CLIENT_STYLE", "auto"),
        interpersonal_style_code=str(client_profile.get("interpersonal_style") or "").strip(),
    )
    # 状態変化幅（Noneなら制限なし）
    client_max_step_env = os.getenv("CLIENT_MAX_STATE_STEP", "none")
    try:
        client_max_step = float(client_max_step_env)
    except (TypeError, ValueError):
        # "none" などは制限なしとして扱う
        client_max_step = None

    # counselor (labeler) / action classifier / client LLM
    phase_llm = build_llm_from_config(phase_cfg, api_key)
    action_llm = build_llm_from_config(action_cfg, api_key)
    client_llm_state = build_llm_from_config(client_state_cfg, api_key)
    client_llm_reply = build_llm_from_config(client_reply_cfg, api_key)
    llm_for_eval = client_llm_reply

    # LLMクライアント（会話相手）
    client = SimpleClientLLM(
        llm=client_llm_reply,
        llm_state=client_llm_state,
        llm_reply=client_llm_reply,
        style=client_style,
        scenario=scenario,
        max_state_step=client_max_step,
    )
    _apply_trait_expression_to_client(client, client_profile)

    # LLMでフェーズ判定（8フェーズ想定。mi_counselor_agent.Phase に依存）
    phase_clf = LLMPhaseClassifier(llm=phase_llm, temperature=0.0, max_history_turns=8)

    # LLMで「カウンセラー発話の行動ラベル」を推定
    action_clf = LLMActionClassifier(llm=action_llm, temperature=0.0, max_history_turns=10)

    cfg = PlannerConfig()  # 特徴量抽出用（確率制御は人間が喋るので使いません）
    state = DialogueState()
    session_meta = {
        "session_mode": "human_counselor",
        "openai_model": phase_cfg.get("model", ""),
        "action_model": action_cfg.get("model", ""),
        "client_model_state": client_state_cfg.get("model", ""),
        "client_model_reply": client_reply_cfg.get("model", ""),
        "client_reasoning_effort": client_reply_cfg.get("reasoning_effort", ""),
        "client_verbosity": client_reply_cfg.get("verbosity", ""),
        "script_name": script_name,
        "client_style": client_style,
        "client_code": client_code,
        "client_pattern": derived_meta.get("pattern_code", ""),
        "client_pattern_label": derived_meta.get("pattern_label", ""),
        "client_primary_focus": derived_meta.get("primary_focus_code", ""),
        "client_primary_focus_label": derived_meta.get("primary_focus_label", ""),
        "client_interpersonal_style": derived_meta.get("interpersonal_style_code", ""),
        "client_interpersonal_style_label": derived_meta.get("interpersonal_style_label", ""),
        "client_profiles_path": str(client_profiles_path),
        "planner_config": asdict(cfg),
    }
    env = ManualConversationEnvironment(session_meta=session_meta)

    # 直近対話（mi_counselor_agent の想定に合わせて user/assistant で持つ）
    history_pairs: List[Tuple[str, str]] = []

    # 初期クライアント発話（デフォルト。必要なら環境変数で上書き）
    # 初期クライアント発話（優先順位: 1) FIRST_CLIENT_UTTERANCE 2) presenting_concern 3) 既定）
    first_client_utterance = (
        os.getenv("FIRST_CLIENT_UTTERANCE")
        or str(client_profile.get("presenting_concern") or "").strip()
        or "相談させてください。"
    )

    env.log.append(ConversationTurn(speaker="client", text=first_client_utterance, meta=None))
    history_pairs.append(("user", first_client_utterance))
    current_client_text = first_client_utterance

    print("人間カウンセラー × LLMクライアント（自動ラベル付け）を開始します。")
    print("Counselor: にあなたの返答を入力してください。'exit' で終了します。")
    print("============================================================")

    while True:
        # ---- 1) フェーズ判定（クライアント発話から）
        phase, phase_debug = phase_clf.classify(history=history_pairs, state=state, user_text=current_client_text)
        state.phase = phase

        # ---- 2) 特徴量（クライアント発話から）
        features = extract_features(current_client_text, state, cfg)

        # WAITING_PERMISSION で明確に拒否なら解除（安全側に倒す）
        if state.info_mode == InfoMode.WAITING_PERMISSION and features.has_permission is False:
            state.info_mode = InfoMode.NONE

        # ---- 3) 人間カウンセラーの入力
        print(f"Client: {current_client_text}")
        try:
            counselor_text = input("Counselor: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n入力が閉じられたため終了します。")
            break

        if counselor_text.lower() == "exit":
            break

        # ---- 4) 行動ラベル判定（カウンセラー発話から）
        action, add_affirm, action_debug = action_clf.classify(
            phase=phase,
            last_client_text=current_client_text,
            counselor_text=counselor_text,
            history=history_pairs,
        )

        # ---- 5) ログ（カウンセラーターン）
        meta_debug = {
            # CSVで出したいもの（session_log_tools.save_log_csv が参照）
            "reflect_streak": state.reflect_streak,
            "r_since_q": state.r_since_q,
            # 追加情報
            "turn_index": state.turn_index,
            "turns_since_summary": state.turns_since_summary,
            "turns_since_affirm": state.turns_since_affirm,
            "info_mode": state.info_mode.value,
            "features": asdict(features),
            "phase_llm": phase_debug,
            "action_llm": action_debug,
        }

        env.log.append(
            ConversationTurn(
                speaker="counselor",
                text=counselor_text,
                meta={
                    "phase": phase.value,
                    "main_action": action.value,
                    "add_affirm": bool(add_affirm),
                    "debug": meta_debug,
                },
            )
        )
        history_pairs.append(("assistant", counselor_text))

        # ---- 6) state 更新（反射ストリーク/質問間隔など）
        next_state = apply_action_to_state(state=state, features=features, action=action, add_affirm=add_affirm)
        next_state.last_user_text = current_client_text
        state = next_state

        # ---- 7) 次のクライアント発話（LLM）
        next_client_text = client.respond(counselor_text, env.log)

        # ★ 追加：クライアント内部状態をメタ情報として保存
        client_meta: Dict[str, Any] = {}
        client_debug = None
        if hasattr(client, "get_internal_state"):
            try:
                client_state = client.get_internal_state()
                client_meta["client_internal_state"] = client_state
            except Exception:
                pass

        # デバッグ目的でクライアント内部ログをコンソール表示（数値のみ）
        if hasattr(client, "get_last_debug_info"):
            try:
                client_debug = client.get_last_debug_info()
                state_reason = client_debug.get("internal_state_reason") or {}
                meta_extra = client_debug.get("meta") or {}
                parse_status = meta_extra.get("parse_status") or client_debug.get("parse_status")
                new_state = client_debug.get("new_state")

                if isinstance(new_state, dict):
                    printable_state = {k: v for k, v in new_state.items() if not str(k).startswith("trait_")}
                    print("  [client state]", json.dumps(printable_state, ensure_ascii=False))
                if parse_status and parse_status != "ok":
                    print(f"  [client state parse_status] {parse_status}")

                # ログには判断根拠も保持
                if state_reason:
                    client_meta["client_internal_state_reason"] = state_reason
                if meta_extra:
                    client_meta["client_meta"] = meta_extra
                # パース状況がわかるように追加
                if parse_status:
                    client_meta["parse_status"] = parse_status
                if "raw_reply" in (client_debug or {}):
                    client_meta["client_raw"] = client_debug.get("raw_reply")
                elif "raw_state" in (client_debug or {}):
                    client_meta["client_raw"] = client_debug.get("raw_state")
            except Exception:
                client_debug = None

        env.log.append(ConversationTurn(speaker="client", text=next_client_text, meta=(client_meta or None)))
        history_pairs.append(("user", next_client_text))
        current_client_text = next_client_text

        print(f"  [auto-label] phase={phase.value} / action={action.value} / add_affirm={bool(add_affirm)}")
        print("------------------------------------------------------------")

    print("\n==== SESSION DONE ====")

    # ログを日時入りファイル名で保存
    if env.log:
        finalize_session(env, llm_for_eval, log_prefix=log_prefix)


if __name__ == "__main__":
    main()
