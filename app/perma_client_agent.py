from __future__ import annotations

"""
クライアント側エージェント（シミュレーション用）

- conversation_environment.py から切り出したい場合のための独立モジュールです。
- 人間カウンセラー × LLMクライアント（ラベル付け用）
- LLMカウンセラー × LLMクライアント（自己対話シミュレーション）

の両方で共通に使えます。
"""

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Protocol, Tuple

import yaml

from mi_counselor_agent import LLMClient


DEFAULT_FIRST_CLIENT_UTTERANCE = "相談させてください。"


# ==============================
# client_profiles.yaml ローダー（SimpleClientLLM用に統合）
# ==============================


@dataclass
class ClientProfileBundle:
    profile: Dict[str, Any]
    derived_meta: Dict[str, str]
    scenario: str
    style: str
    first_utterance: str
    max_state_step: Optional[float]
    profiles_path: Path
    clients_cfg: Dict[str, Any]
    first_utterance_mode: str = "profile"
    first_utterance_debug: Optional[Dict[str, Any]] = None


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _find_client_profiles_path() -> Path:
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
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _get_client_profile(cfg: Dict[str, Any], client_code: str) -> Dict[str, Any]:
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


def _derive_client_meta(profile: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, str]:
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

    return {
        "pattern_code": pattern_code,
        "pattern_label": pattern_label,
        "primary_focus_code": primary_focus_code,
        "primary_focus_label": primary_focus_label,
        "interpersonal_style_code": interpersonal_style_code,
        "interpersonal_style_label": interpersonal_label,
        "interpersonal_style_brief": interpersonal_brief,
    }


def _resolve_client_llm_style(*, env_style: str, interpersonal_style_code: str) -> str:
    s = (env_style or "auto").strip().lower()
    if s in ("cooperative", "ambivalent", "resistant"):
        return s

    code = (interpersonal_style_code or "").strip()
    mapping = {
        "S1": "cooperative",
        "S2": "resistant",
        "S3": "cooperative",
    }
    return mapping.get(code, "cooperative")


def _format_perma_baseline(baseline_perma: Any, cfg: Dict[str, Any]) -> List[str]:
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
            if abs(v - int(v)) < 1e-9:
                v_str = str(int(v))
            else:
                v_str = str(v)
        except Exception:
            v_str = _safe_str(baseline_perma.get(k))
        lines.append(f"- {name} [{k}]: {v_str}")

    for k, v in baseline_perma.items():
        if str(k) in order:
            continue
        name = _safe_str(perma_defs.get(str(k))) or str(k)
        lines.append(f"- {name} [{k}]: {v}")

    return lines


def _format_trait_expression(trait_expression: Any) -> List[str]:
    if not isinstance(trait_expression, dict):
        return []

    desc = {-1: "出にくい", 0: "標準", 1: "出やすい"}
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
    lines: List[str] = []
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

    pc = _safe_str(profile.get("presenting_concern"))
    if pc:
        lines.append("")
        lines.append("【主訴】")
        lines.append(pc)

    baseline_perma = profile.get("baseline_perma")
    perma_lines = _format_perma_baseline(baseline_perma, cfg)
    if perma_lines:
        lines.append("")
        lines.append("【事前PERMA想定（0〜10）】")
        lines.extend(perma_lines)

    strengths = profile.get("strengths_resources")
    if isinstance(strengths, list) and strengths:
        lines.append("")
        lines.append("【強み/資源】")
        for s in strengths:
            st = _safe_str(s)
            if st:
                lines.append(f"- {st}")

    mc = _safe_str(profile.get("maintaining_cycle"))
    if mc:
        lines.append("")
        lines.append("【維持サイクル】")
        lines.append(mc)

    sg = _safe_str(profile.get("session_goal"))
    if sg:
        lines.append("")
        lines.append("【このセッションの目標】")
        lines.append(sg)

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

    te = profile.get("trait_expression")
    te_lines = _format_trait_expression(te)
    if te_lines:
        lines.append("")
        lines.append("【発話としての出やすさ特性（-1/0/+1）】")
        lines.extend(te_lines)

    return "\n".join(lines).strip()


def _apply_trait_expression_to_client(client: Any, profile: Dict[str, Any]) -> None:
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
            continue


def _parse_max_state_step(env_value: str) -> Optional[float]:
    try:
        return float(env_value)
    except (TypeError, ValueError):
        return None


def _choose_first_client_utterance(
    profile: Dict[str, Any],
    first_client_utterance_env: Optional[str],
    default_first_utterance: str,
) -> str:
    """
    初期発話は、環境変数 > プロファイル独自フィールド(first_utterance) > 既定値 の順で決める。
    presenting_concern は「主訴の説明」であり、初回発話としては使わない。
    """
    if first_client_utterance_env:
        return first_client_utterance_env

    profile_first = _safe_str(profile.get("first_utterance"))
    if profile_first:
        return profile_first

    return default_first_utterance


def _postprocess_first_utterance_text(text: str) -> str:
    """
    LLMが返した初期発話を1行のテキストに整形する。
    - 空行を除去し、最初の行のみ採用
    - 先頭/末尾の引用符や括弧をトリム
    """
    lines = [ln.strip() for ln in str(text).splitlines() if ln and ln.strip()]
    if not lines:
        return ""
    t = lines[0]
    t = t.strip("「」『』\"'（）()[]{} ")
    return t.strip()


def _maybe_generate_first_utterance_with_llm(
    bundle: ClientProfileBundle,
    llm: LLMClient,
) -> Tuple[str, Dict[str, Any]]:
    """
    初期発話は常に LLM で生成する（環境変数 FIRST_CLIENT_UTTERANCE があればそちらを優先）。
    """
    explicit_env = os.getenv("FIRST_CLIENT_UTTERANCE")
    if explicit_env:
        return explicit_env, {"mode": "env"}

    temperature = 0.7
    try:
        t_env = os.getenv("FIRST_CLIENT_UTTERANCE_TEMPERATURE")
        if t_env:
            temperature = float(t_env)
    except Exception:
        pass

    presenting = _safe_str(bundle.profile.get("presenting_concern"))

    system = (
        "あなたは相談のクライアントです。次の設定に沿って、初回にカウンセラーへ伝える"
        "自然な1〜2文だけを日本語で返してください。短く端的に、困りごとや今の気持ちを"
        "述べてください。箇条書きや説明文は書かないでください。"
    )
    user = (
        f"{bundle.scenario}\n"
        + (f"\n【主訴の要点】{presenting}\n" if presenting else "\n")
        + "上記を踏まえ、初回にカウンセラーへ伝える自然な1〜2文だけを返してください。"
    )

    try:
        raw = llm.generate(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
        )
        candidate = _postprocess_first_utterance_text(raw)
    except Exception as e:
        return bundle.first_utterance, {"mode": "llm", "error": str(e)}

    if candidate:
        return candidate, {"mode": "llm", "temperature": temperature, "raw": str(raw)}

    return bundle.first_utterance, {"mode": "llm", "raw": str(raw), "fallback": "empty"}


def _load_client_profile_bundle(
    client_code: str,
    *,
    env_style: str = "auto",
    first_client_utterance_env: Optional[str] = None,
    max_state_step_env: str = "none",
    profiles_path: Optional[Path] = None,
    default_first_utterance: str = DEFAULT_FIRST_CLIENT_UTTERANCE,
) -> ClientProfileBundle:
    path = profiles_path or _find_client_profiles_path()
    clients_cfg = _load_client_profiles_yaml(path)
    profile = _get_client_profile(clients_cfg, client_code)
    derived_meta = _derive_client_meta(profile, clients_cfg)
    scenario = _build_client_scenario_text(client_code, profile, clients_cfg, derived_meta)
    style = _resolve_client_llm_style(
        env_style=env_style,
        interpersonal_style_code=_safe_str(profile.get("interpersonal_style")),
    )
    max_state_step = _parse_max_state_step(max_state_step_env)
    first_utterance = _choose_first_client_utterance(
        profile,
        first_client_utterance_env=first_client_utterance_env,
        default_first_utterance=default_first_utterance,
    )

    return ClientProfileBundle(
        profile=profile,
        derived_meta=derived_meta,
        scenario=scenario,
        style=style,
        first_utterance=first_utterance,
        max_state_step=max_state_step,
        profiles_path=path,
        clients_cfg=clients_cfg,
    )


class ClientAgent(Protocol):
    """
    クライアント側エージェントのインタフェース。

    respond:
      - counselor_text: 直近のカウンセラー発話（今回の入力）
      - history: ConversationTurn っぽいオブジェクトのリスト（speaker/text 属性があればOK）
      - return: 次のクライアント発話（str）
    """

    def respond(self, counselor_text: str, history: List[Any]) -> str:
        ...


# ==============================
# クライアント内部状態
# ==============================

@dataclass
class ClientInternalState:
    """
    クライアントの「内部ログ」として持つ6つの指標（すべて 0〜10 の連続値）。

    - pos_affect: ポジティブ感情の強さ
    - neg_affect: ネガティブ感情の強さ
    - importance_change: 変化・目標達成の重要度の認識
    - confidence_change: 変化・目標達成の自信度の認識
    - like_counselor: カウンセラーへの好感
    - tension_counselor: カウンセラーへの不和感・緊張

    特性（trait_*）は各スコアの「出にくさ／出やすさ」を表す係数です。
    -1: 出にくい（低めで安定しやすい）
     0: 標準
    +1: 出やすい（高めで安定しやすい）
    """

    # ------------------------------
    # 状態（0〜10）
    # ------------------------------
    pos_affect: float = 5.0
    neg_affect: float = 5.0
    importance_change: float = 5.0
    confidence_change: float = 5.0
    like_counselor: float = 5.0
    tension_counselor: float = 0.0

    # ------------------------------
    # 特性：各スコアの「出やすさ」
    # -1 = 出にくい
    #  0 = 標準
    # +1 = 出やすい
    # ------------------------------
    trait_expression_pos: float = 0.0
    trait_expression_neg: float = 0.0
    trait_expression_importance: float = 0.0
    trait_expression_confidence: float = 0.0
    trait_expression_like: float = 0.0
    trait_expression_tension: float = 0.0

    STATE_KEYS = (
        "pos_affect",
        "neg_affect",
        "importance_change",
        "confidence_change",
        "like_counselor",
        "tension_counselor",
    )

    TRAIT_KEYS = (
        "trait_expression_pos",
        "trait_expression_neg",
        "trait_expression_importance",
        "trait_expression_confidence",
        "trait_expression_like",
        "trait_expression_tension",
    )

    def to_dict(self) -> Dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.STATE_KEYS}

    def to_traits_dict(self) -> Dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.TRAIT_KEYS}

    def to_full_dict(self) -> Dict[str, float]:
        data = self.to_dict()
        data.update(self.to_traits_dict())
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base: Optional["ClientInternalState"] = None) -> "ClientInternalState":
        """
        JSON などから復元するためのヘルパー。
        想定外のキーや値は無視しつつ、既定値をベースに上書きします。
        """
        base_state = base if isinstance(base, cls) else cls()
        # まずベース値で初期化（状態＋特性）
        base_kwargs = {k: getattr(base_state, k) for k in cls.STATE_KEYS + cls.TRAIT_KEYS}
        base = cls(**base_kwargs)  # type: ignore[arg-type]
        if not isinstance(data, dict):
            return base

        for key in cls.STATE_KEYS + cls.TRAIT_KEYS:
            v = data.get(key)
            if v is None:
                continue
            try:
                setattr(base, key, float(v))
            except (TypeError, ValueError):
                # 数値に変換できないときは無視
                continue

        return base

    # ------------------------------
    # 出やすさ（trait_expression_*）の取得
    # ------------------------------
    def get_expression(self, state_key: str) -> float:
        """
        各スコアに対応する「出やすさ」を返す。
        -1.0 〜 +1.0 の範囲にクリップして扱う。
        """
        mapping = {
            "pos_affect": "trait_expression_pos",
            "neg_affect": "trait_expression_neg",
            "importance_change": "trait_expression_importance",
            "confidence_change": "trait_expression_confidence",
            "like_counselor": "trait_expression_like",
            "tension_counselor": "trait_expression_tension",
        }
        trait_key = mapping.get(state_key)
        if trait_key is None:
            return 0.0

        try:
            val = float(getattr(self, trait_key, 0.0))
        except (TypeError, ValueError):
            val = 0.0

        # -1〜+1 にクリップ
        if val < -1.0:
            val = -1.0
        elif val > 1.0:
            val = 1.0
        return val

    def adjust_by_expression(self, state_key: str, before: float, target: float) -> float:
        """
        LLM が提案した target を、そのスコアの「出やすさ」に応じて歪める。

        - expr = -1（出にくい）
            上昇（target > before）   → 小さく（0.5倍）なりやすい
            下降（target < before）   → 大きく（1.5倍）なりやすい

        - expr = +1（出やすい）
            上昇                       → 大きく（1.5倍）なりやすい
            下降                       → 小さく（0.5倍）なりやすい

        expr = 0（標準）のときはそのまま。
        """
        expr = self.get_expression(state_key)
        delta = target - before

        # 変化がない、または標準ならそのまま
        if delta == 0.0 or expr == 0.0:
            return target

        # 出やすさの強さ（0〜1）。0.5 くらいだと「そこそこ効く」感じ
        alpha = 0.5

        if delta > 0:
            # 上方向の変化：expr > 0 で増幅、expr < 0 で抑制
            mult = 1.0 + alpha * expr
        else:
            # 下方向の変化：expr > 0 で抑制、expr < 0 で増幅
            mult = 1.0 - alpha * expr

        return before + delta * mult


@dataclass
class SimpleClientLLM(ClientAgent):
    """
    LLMを使ったシンプルなクライアントエージェント。

    - 「悩みを持つクライアント」として自然に返答する役
    - 実験・シミュレーション用途
    """
    llm: LLMClient
    llm_state: Optional[LLMClient] = None  # 内部状態更新用（未指定なら llm を使用）
    llm_reply: Optional[LLMClient] = None  # 応答生成用（未指定なら llm を使用）
    style: Literal["cooperative", "ambivalent", "resistant"] = "cooperative"
    persona: Optional[str] = None
    scenario: Optional[str] = None
    temperature: float = 0.4
    seed: Optional[int] = None
    # 状態変化の1ターン上限（Noneなら制限なし）
    max_state_step: Optional[float] = None
    max_history_turns: int = 20

    # ★ 変化量の全体スケーリング係数（1.0より大きいと変化が大きくなる）
    delta_scale: float = 1.8

    # ★ 指標ごとの『変わりやすさ』（1.0=基準、0.0=変化しない）
    #   - pos/neg: 変わりやすい
    #   - importance/confidence/tension: 変わりにくい
    #   - like: 中程度
    sensitivity_pos: float = 1.0
    sensitivity_neg: float = 1.0
    sensitivity_importance: float = 0.8
    sensitivity_confidence: float = 0.8
    sensitivity_like: float = 1.0
    sensitivity_tension: float = 0.8

    # ★ 内部状態を丸めて保持する桁数（小数第2位まで）
    state_decimal_places: int = 2

    # ★ like/tension が動かないときの保険（変化がないときだけ小さく補正）
    relationship_heuristic: bool = True
    relationship_heuristic_only_if_unchanged: bool = True

    # ★ クライアントの内部状態（ターンごとに更新）
    internal_state: ClientInternalState = field(default_factory=ClientInternalState)
    _last_debug_info: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.persona is None:
            self.persona = self._build_persona(self.style, self.scenario)
        else:
            self.persona = str(self.persona)

        if self.scenario is not None:
            self.scenario = str(self.scenario)

        # state/reply が未指定なら共通LLMを使う
        if self.llm_state is None:
            self.llm_state = self.llm
        if self.llm_reply is None:
            self.llm_reply = self.llm

    @classmethod
    def from_profile(
        cls,
        *,
        client_code: str,
        llm: LLMClient,
        llm_state: Optional[LLMClient] = None,
        llm_reply: Optional[LLMClient] = None,
        env_style: str = "auto",
        first_client_utterance_env: Optional[str] = None,
        max_state_step_env: str = "none",
        default_first_utterance: str = DEFAULT_FIRST_CLIENT_UTTERANCE,
        profiles_path: Optional[Path] = None,
        **kwargs: Any,
    ) -> Tuple["SimpleClientLLM", ClientProfileBundle]:
        """
        client_profiles.yaml からクライアント設定を読み込み、SimpleClientLLM とメタ情報を返す。
        """
        bundle = _load_client_profile_bundle(
            client_code=client_code,
            env_style=env_style,
            first_client_utterance_env=first_client_utterance_env,
            max_state_step_env=max_state_step_env,
            profiles_path=profiles_path,
            default_first_utterance=default_first_utterance,
        )

        primary_llm = llm_reply or llm
        generated_first, first_meta = _maybe_generate_first_utterance_with_llm(bundle, llm=primary_llm)
        bundle.first_utterance = generated_first
        bundle.first_utterance_mode = first_meta.get("mode", "llm")
        bundle.first_utterance_debug = first_meta
        client = cls(
            llm=primary_llm,
            llm_state=llm_state or llm,
            llm_reply=llm_reply or llm,
            style=bundle.style,
            scenario=bundle.scenario,
            max_state_step=bundle.max_state_step,
            **kwargs,
        )
        _apply_trait_expression_to_client(client, bundle.profile)
        return client, bundle

    def reset(self) -> None:
        """
        セッションリセット時に呼ばれることを想定。
        内部状態も初期値に戻します。
        """
        self.internal_state = ClientInternalState()

    def get_internal_state(self) -> Dict[str, float]:
        """
        ConversationEnvironment からログ用に呼ぶためのアクセサ。
        """
        return self.internal_state.to_dict()

    def get_last_debug_info(self) -> Dict[str, Any]:
        """
        直近の LLM 応答に関するデバッグ情報を返す。
        - raw_state: 状態更新LLMの生レスポンス
        - raw_reply: 応答LLMの生レスポンス
        - reply: 実際に使った返答（raw_replyをstripしたもの）
        - old_state / new_state: 変化前後の状態（特性含む）
        - internal_state_reason: スコア変化の理由（LLMが返した場合）
        - meta: 付加的な自己ラベル等
        """
        return dict(self._last_debug_info)

    @staticmethod
    def _build_persona(style: str, scenario: Optional[str] = None) -> str:
        presets = {
            "cooperative": (
                "あなたは、生活や行動のことで少し困りごとを抱えているクライアントです。\n"
                "自分の気持ちや状況を、できる範囲で正直に、丁寧な口調で話してください。\n"
                "カウンセラーと対立するのではなく、自分の本音や迷いを表現してよい場です。\n"
            ),
            "ambivalent": (
                "あなたは、変わりたい気持ちと『どうせ無理かも』という迷いが混ざったクライアントです。\n"
                "前向きな気持ちと不安やためらいの両方を、丁寧な口調で率直に言葉にしてください。\n"
                "反射には自然に反応しつつ、時には尻込みしたり、決めきれない様子も出してかまいません。\n"
            ),
            "resistant": (
                "あなたは、少し構え気味で、変化に疑問や不信感を持つクライアントです。\n"
                "丁寧さは保ちつつも『でも』『どうせ』『前も失敗した』など、抵抗や懐疑がにじむ返答を織り交ぜてください。\n"
                "ただし攻撃的にはならず、本音ベースでの反応に留めてください。\n"
            ),
        }
        base_persona = presets.get(style, presets["cooperative"])
        if scenario:
            base_persona += "\n【シナリオ】\n" + str(scenario).strip() + "\n"
        return base_persona

    @staticmethod
    def _clip_0_10(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 10.0:
            return 10.0
        return x

    def _round_state(self, x: float) -> float:
        try:
            nd = int(self.state_decimal_places)
        except (TypeError, ValueError):
            nd = 2
        return round(float(x), nd)

    def _get_sensitivity(self, state_key: str) -> float:
        """
        指標ごとの『変わりやすさ』係数を返す。
        - 1.0: 基準
        - 0.0: 変化しない
        - >1.0: より変わりやすい

        ※ 負の値は逆方向の変化になってしまうため 0.0 に丸めます。
        """
        mapping = {
            "pos_affect": "sensitivity_pos",
            "neg_affect": "sensitivity_neg",
            "importance_change": "sensitivity_importance",
            "confidence_change": "sensitivity_confidence",
            "like_counselor": "sensitivity_like",
            "tension_counselor": "sensitivity_tension",
        }
        attr = mapping.get(state_key)
        if not attr:
            return 1.0
        try:
            val = float(getattr(self, attr))
        except (TypeError, ValueError):
            val = 1.0
        if val < 0.0:
            val = 0.0
        return val

    @staticmethod
    def _calc_relationship_deltas(counselor_text: str) -> Tuple[float, float, List[str]]:
        """
        counselor_text の口調・内容から、like/tension の微小な変化を推定する。
        （LLM が like/tension を動かさないときの保険）

        返り値:
          (delta_like, delta_tension, hits)
        """
        t = str(counselor_text or "").strip()
        if not t:
            return 0.0, 0.0, []

        rules: List[Tuple[str, float, float, str]] = [
            # 共感・受容（like↑ tension↓）
            ("大変", +0.60, -0.30, "empathy"),
            ("つら", +0.60, -0.30, "empathy"),
            ("しんど", +0.60, -0.30, "empathy"),
            ("そうなんですね", +0.40, -0.20, "reflect"),
            ("なんですね", +0.20, -0.10, "reflect"),
            ("わかります", +0.70, -0.30, "empathy"),
            ("理解できます", +0.70, -0.30, "empathy"),
            ("ありがとうございます", +0.40, -0.20, "respect"),
            ("良いですね", +0.70, -0.30, "affirm"),
            ("素晴らしい", +0.90, -0.40, "affirm"),
            ("工夫", +0.50, -0.20, "affirm"),
            ("頑張", +0.50, -0.20, "affirm"),
            # 否定・批判・見下し（like↓ tension↑）
            ("努力が足り", -1.40, +1.00, "blame"),
            ("言い訳", -1.10, +0.80, "blame"),
            ("迷惑", -1.60, +1.20, "hostile"),
            ("グダグダ", -1.20, +0.90, "dismiss"),
            ("無理", -0.80, +0.60, "dismiss"),
            ("理解できません", -1.30, +1.00, "reject"),
            ("理解できない", -1.30, +1.00, "reject"),
            ("バカ", -2.00, +2.00, "insult"),
            ("甘えるな", -1.60, +1.40, "insult"),
            # 命令・押しつけ（軽めに tension↑）
            ("すべき", -0.60, +0.40, "directive"),
            ("しかない", -0.40, +0.30, "directive"),
            ("しなさい", -0.80, +0.60, "directive"),
        ]

        dl = 0.0
        dt = 0.0
        hits: List[str] = []
        for phrase, r_dl, r_dt, tag in rules:
            if phrase in t:
                dl += r_dl
                dt += r_dt
                hits.append(tag + ":" + phrase)

        # 記号で少し補正（強い言い方になりやすい）
        if "!" in t or "！" in t:
            dt += 0.20
            hits.append("punct:!")
        # 「？」は中立〜圧がある場合もあるので極小だけ
        if "?" in t or "？" in t:
            dt += 0.05
            hits.append("punct:?")

        return dl, dt, hits

    def _apply_relationship_heuristic(
        self,
        new_state_dict: Dict[str, float],
        counselor_text: str,
        meta: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        like/tension が「全く動かない」状況への保険。
        LLM が動かした場合は尊重し、動いていない場合にだけ小さく補正する。
        """
        if not self.relationship_heuristic:
            return new_state_dict

        # 現在値（更新前）
        try:
            old_like = float(self.internal_state.like_counselor)
        except (TypeError, ValueError):
            old_like = 5.0
        try:
            old_tension = float(self.internal_state.tension_counselor)
        except (TypeError, ValueError):
            old_tension = 0.0

        # LLM 反映後（parse済み）値
        like_val = new_state_dict.get("like_counselor", old_like)
        tension_val = new_state_dict.get("tension_counselor", old_tension)
        try:
            like_val = float(like_val)
        except (TypeError, ValueError):
            like_val = old_like
        try:
            tension_val = float(tension_val)
        except (TypeError, ValueError):
            tension_val = old_tension

        # 変化判定（LLM が動かしたなら尊重）
        eps = 1e-9
        like_changed = abs(like_val - old_like) > eps
        tension_changed = abs(tension_val - old_tension) > eps

        # only_if_unchanged の場合、動いた方は補正しない
        if self.relationship_heuristic_only_if_unchanged:
            apply_like = not like_changed
            apply_tension = not tension_changed
        else:
            apply_like = True
            apply_tension = True

        if not apply_like and not apply_tension:
            return new_state_dict

        dl_raw, dt_raw, hits = self._calc_relationship_deltas(counselor_text)
        scale = float(getattr(self, "delta_scale", 1.0))

        dl = 0.0
        dt = 0.0

        if apply_like:
            target_like = like_val + dl_raw
            adjusted_like = self.internal_state.adjust_by_expression("like_counselor", like_val, target_like)
            sens_like = self._get_sensitivity("like_counselor")
            dl = (adjusted_like - like_val) * scale * sens_like

        if apply_tension:
            target_tension = tension_val + dt_raw
            adjusted_tension = self.internal_state.adjust_by_expression("tension_counselor", tension_val, target_tension)
            sens_tension = self._get_sensitivity("tension_counselor")
            dt = (adjusted_tension - tension_val) * scale * sens_tension

        # 1ターン上限を尊重
        max_step = self.max_state_step
        if max_step is not None:
            try:
                ms = float(max_step)
            except (TypeError, ValueError):
                ms = None
            if ms is not None:
                if apply_like:
                    if dl > ms:
                        dl = ms
                    elif dl < -ms:
                        dl = -ms
                if apply_tension:
                    if dt > ms:
                        dt = ms
                    elif dt < -ms:
                        dt = -ms

        if apply_like:
            like_val = self._clip_0_10(like_val + dl)
            like_val = self._round_state(like_val)
            new_state_dict["like_counselor"] = like_val

        if apply_tension:
            tension_val = self._clip_0_10(tension_val + dt)
            tension_val = self._round_state(tension_val)
            new_state_dict["tension_counselor"] = tension_val

        meta["relationship_heuristic"] = {
            "applied_like": bool(apply_like),
            "applied_tension": bool(apply_tension),
            "sensitivity_like": self._round_state(self._get_sensitivity("like_counselor")),
            "sensitivity_tension": self._round_state(self._get_sensitivity("tension_counselor")),
            "delta_like": self._round_state(dl),
            "delta_tension": self._round_state(dt),
            "hits": hits,
        }
        return new_state_dict

    # ------------------------------
    # 返答＋内部状態更新（2段階）
    # ------------------------------
    def respond(self, counselor_text: str, history: List[Any]) -> str:
        """
        1) 内部状態を更新（state用LLM）
        2) 更新後の状態を踏まえて応答を生成（reply用LLM）
        """
        state_dict = self.internal_state.to_dict()
        trait_dict = self.internal_state.to_traits_dict()
        old_state_full = self.internal_state.to_full_dict()

        # ---- 1) 内部状態更新 ----
        state_messages = self._build_state_messages(
            counselor_text=counselor_text,
            history=history,
            state_dict=state_dict,
            trait_dict=trait_dict,
        )
        try:
            raw_state = self.llm_state.generate(
                state_messages,
                temperature=float(self.temperature),
                seed=None if self.seed is None else int(self.seed),
            )
        except (TypeError, ValueError):
            raw_state = self.llm_state.generate(state_messages, temperature=float(self.temperature))

        new_state_dict, state_reason, state_meta = self._parse_state_update(str(raw_state))

        # like/tension が動かない場合の保険（変化がないときだけ補正）
        new_state_dict = self._apply_relationship_heuristic(new_state_dict, counselor_text, state_meta)

        # 内部状態を更新
        self.internal_state = ClientInternalState.from_dict(new_state_dict, base=self.internal_state)

        # ---- 2) 応答生成（更新後の状態を参照）----
        reply_messages = self._build_reply_messages(
            counselor_text=counselor_text,
            history=history,
            state_reason=state_reason,
            state_meta=state_meta,
        )
        try:
            raw_reply = self.llm_reply.generate(
                reply_messages,
                temperature=float(self.temperature),
                seed=None if self.seed is None else int(self.seed),
            )
        except (TypeError, ValueError):
            raw_reply = self.llm_reply.generate(reply_messages, temperature=float(self.temperature))

        raw_reply_str = str(raw_reply)
        reply = self._extract_reply_text(raw_reply_str)
        raw_reply_all = [raw_reply_str]
        if not reply:
            repair_messages = list(reply_messages)
            repair_messages.append(
                {
                    "role": "system",
                    "content": (
                        "直前の出力が空か、JSON/オブジェクトだけでした。"
                        "クライアントとして1〜3文の自然なテキストのみを返してください。"
                        "箇条書きは可ですが、{} や []、キー名だけのJSONは禁止です。"
                    ),
                }
            )
            try:
                raw_reply_retry = self.llm_reply.generate(
                    repair_messages,
                    temperature=float(self.temperature),
                    seed=None if self.seed is None else int(self.seed),
                )
            except (TypeError, ValueError):
                raw_reply_retry = self.llm_reply.generate(repair_messages, temperature=float(self.temperature))
            raw_reply_retry_str = str(raw_reply_retry)
            raw_reply_all.append(raw_reply_retry_str)
            reply = self._extract_reply_text(raw_reply_retry_str)

        if not reply:
            raise ValueError(f"llm_reply returned empty or invalid text: {raw_reply_all}")

        # デバッグ情報を保持
        self._last_debug_info = {
            "raw_state": str(raw_state),
            "raw_reply": raw_reply_all,
            "reply": reply,
            "old_state": old_state_full,
            "new_state": self.internal_state.to_full_dict(),
            "internal_state_reason": state_reason,
            "meta": state_meta,
        }

        return reply

    def _extract_reply_text(self, raw: str) -> Optional[str]:
        """
        llm_reply が JSON 形式（例: {"text": "..."}）で返した場合に text フィールドを取り出す。
        空のオブジェクト {} のときは None を返す。
        """
        t = (raw or "").strip()
        if not t:
            return None
        # JSONらしきときだけパースを試みる（非JSONならそのまま返す）
        if t.startswith("{") or t.startswith("["):
            try:
                data = json.loads(t)
            except Exception:
                return None
            if isinstance(data, dict):
                if not data:
                    return None
                if "text" in data:
                    val = data.get("text")
                    return str(val) if val is not None else ""
                # よくあるエイリアス
                for key in ("reply", "content", "message"):
                    if key in data:
                        return str(data.get(key) or "")
                # dictだがテキストキーがなければNone
                return None
            if isinstance(data, list) and data:
                # 先頭要素が文字列ならそれを使う
                if isinstance(data[0], str):
                    return data[0]
                if isinstance(data[0], dict) and "text" in data[0]:
                    return str(data[0].get("text") or "")
            return None
        # JSONでない場合は生テキストをそのまま返す
        return t

    def _parse_state_update(self, raw: str) -> tuple[Dict[str, float], Dict[str, str], Dict[str, Any]]:
        """
        内部状態更新用の LLM 出力をパースする。
        JSONでなかった場合は現状態を返す。
        """
        text = str(raw).strip()
        parse_status = "ok"

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not m:
                return self.internal_state.to_full_dict(), {}, {"parse_status": "fallback_no_brace"}
            try:
                data = json.loads(m.group(0))
                parse_status = "fallback_brace"
            except json.JSONDecodeError:
                return self.internal_state.to_full_dict(), {}, {"parse_status": "fallback_json_error"}

        if not isinstance(data, dict):
            return self.internal_state.to_full_dict(), {}, {"parse_status": "fallback_non_dict"}

        state_in = data.get("internal_state") or {}
        merged_state = self.internal_state.to_dict()

        state_aliases: Dict[str, List[str]] = {
            "pos_affect": ["pos", "positive_affect", "positive"],
            "neg_affect": ["neg", "negative_affect", "negative"],
            "importance_change": ["importance", "importance_score"],
            "confidence_change": ["confidence", "self_efficacy", "confidence_score"],
            "like_counselor": ["like", "rapport", "likeCounselor", "counselor_like"],
            "tension_counselor": ["tension", "reactance", "discord", "tensionCounselor", "counselor_tension"],
        }

        provided_keys: List[str] = []
        alias_used: Dict[str, str] = {}
        has_state_input = False
        updated_any = False

        if isinstance(state_in, dict):
            for key in merged_state.keys():
                v = state_in.get(key)
                if v is None:
                    for ak in state_aliases.get(key, []):
                        if ak in state_in:
                            v = state_in.get(ak)
                            alias_used[key] = ak
                            break

                if v is None:
                    continue

                has_state_input = True
                provided_keys.append(key)

                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue

                if math.isinf(fv) or math.isnan(fv):
                    continue

                max_step = self.max_state_step
                before = merged_state.get(key, 5.0)
                if max_step is not None:
                    try:
                        ms = float(max_step)
                        delta = fv - float(before)
                        if delta > ms:
                            fv = float(before) + ms
                        elif delta < -ms:
                            fv = float(before) - ms
                    except (TypeError, ValueError):
                        pass

                fv = self._round_state(self._clip_0_10(fv))
                merged_state[key] = fv
                updated_any = True

        # 特性・感度に基づく補正＋ステップ制限（has_state_input のときだけ実施）
        current_state = self.internal_state.to_dict()
        try:
            nd = int(self.state_decimal_places)
        except (TypeError, ValueError):
            nd = 2
        scale = float(getattr(self, "delta_scale", 1.0))
        max_step = self.max_state_step

        sensitivity_debug: Dict[str, float] = {}
        for k in merged_state.keys():
            sensitivity_debug[k] = self._round_state(self._get_sensitivity(k))
        meta_sensitivity = {k: v for k, v in sensitivity_debug.items()}

        if has_state_input:
            for k, target in list(merged_state.items()):
                try:
                    target = float(target)
                except (TypeError, ValueError):
                    continue

                target = self._clip_0_10(target)

                try:
                    before = float(current_state.get(k, target))
                except (TypeError, ValueError):
                    before = target

                adjusted = self.internal_state.adjust_by_expression(k, before, target)
                sensitivity = self._get_sensitivity(k)
                delta = (adjusted - before) * scale * sensitivity

                if max_step is not None:
                    try:
                        ms = float(max_step)
                        if delta > ms:
                            delta = ms
                        elif delta < -ms:
                            delta = -ms
                    except (TypeError, ValueError):
                        pass

                new_value = before + delta
                new_value = self._clip_0_10(new_value)
                new_value = round(float(new_value), nd)
                merged_state[k] = new_value

        if not has_state_input:
            merged_state = self.internal_state.to_dict()

        reasons_in = data.get("internal_state_reason") or {}
        reasons: Dict[str, str] = {}
        if isinstance(reasons_in, dict):
            for k, v in reasons_in.items():
                try:
                    reasons[str(k)] = str(v)
                except Exception:
                    continue

        meta: Dict[str, Any] = {
            "parse_status": parse_status,
            "has_state_input": has_state_input,
            "updated_any": updated_any,
            "provided_keys": provided_keys,
            "sensitivity": meta_sensitivity,
        }
        if alias_used:
            meta["alias_used"] = alias_used

        change_type = data.get("client_change_talk_type")
        sustain_type = data.get("client_sustain_talk_type")
        if change_type is not None:
            meta["client_change_talk_type"] = str(change_type)
        if sustain_type is not None:
            meta["client_sustain_talk_type"] = str(sustain_type)

        return merged_state, reasons, meta

    def _build_state_messages(
        self,
        *,
        counselor_text: str,
        history: List[Any],
        state_dict: Dict[str, float],
        trait_dict: Dict[str, float],
    ) -> List[Dict[str, str]]:
        """内部状態更新用のプロンプトを組み立てる。"""
        system_prompt = (
            (self.persona or "")
            + "\n\n"
            "【あなたの内部状態スコアについて】\n"
            "あなたには、次の6つの内部状態スコアがあります。すべて 0〜10 の範囲です。\n"
            "- pos_affect: ポジティブな気分の強さ\n"
            "- neg_affect: ネガティブな気分の強さ\n"
            "- importance_change: 変化・目標達成の重要度の感じ方\n"
            "- confidence_change: 変化・目標達成の自信度\n"
            "- like_counselor: カウンセラーへの好感（共感的だと上がり、批判的だと下がりやすい）\n"
            "- tension_counselor: カウンセラーへの不和感・緊張（批判/圧が強いと上がり、受容的だと下がりやすい）\n"
            "※ like_counselor と tension_counselor は、直近のカウンセラー発話の態度に応じて変化させてください。\n"
            "  例: 共感・尊重→ like↑ / tension↓、批判・見下し・命令口調→ like↓ / tension↑\n"
            "※ 数値は小数第2位まででOKです（例: 5.25）。\n\n"
            "【更新方法】\n"
            "- 直近の対話履歴（クライアント/カウンセラー両方）を踏まえ、各スコアを現実的に更新してください。\n"
            "- 対話の流れに矛盾しないよう、前のクライアント発話で語られた感情・価値観・迷いも考慮してください。\n"
            "- カウンセラーの直近発話に対する反応（好感/緊張）も反映してください。\n\n"
            f"現時点のスコア: {json.dumps(state_dict, ensure_ascii=False)}\n\n"
            "【スコアの出やすさの特性（-1:出にくい, 0:標準, +1:出やすい）】\n"
            f"{json.dumps(trait_dict, ensure_ascii=False)}\n\n"
            "【出力に関する厳守事項】\n"
            "- internal_state には上記6項目すべてを必ず数値で含めてください（like_counselor と tension_counselor も含む）。\n"
            "- 変化がない場合は直前の値をそのまま入れてください。null や欠落は禁止です。\n"
            "- reply は書かず、状態JSONだけを返してください。\n\n"
            "出力フォーマット（JSON のみ）:\n"
            "{\n"
            '  "internal_state": { ... },\n'
            '  "internal_state_reason": { ... 任意 ... },\n'
            '  "client_change_talk_type": "変化言語ラベル（任意）",\n'
            '  "client_sustain_talk_type": "持続言語ラベル（任意）"\n'
            "}\n"
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for turn in history[-self.max_history_turns :]:
            speaker = getattr(turn, "speaker", "")
            text = getattr(turn, "text", "")
            if not isinstance(text, str):
                continue
            role = "user" if speaker == "counselor" else "assistant"
            messages.append({"role": role, "content": text})

        if not (
            history
            and getattr(history[-1], "speaker", None) == "counselor"
            and getattr(history[-1], "text", "").strip() == counselor_text.strip()
        ):
            messages.append({"role": "user", "content": counselor_text})

        return messages

    def _build_reply_messages(
        self,
        *,
        counselor_text: str,
        history: List[Any],
        state_reason: Dict[str, str],
        state_meta: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        応答生成用のプロンプトを組み立てる。
        更新後の内部状態と理由を参考情報として与え、自然な返答だけを出させる。
        """
        state_dict = self.internal_state.to_full_dict()
        state_text = " / ".join([f"{k}={v}" for k, v in state_dict.items()])
        reasons_text = " / ".join([f"{k}:{v}" for k, v in (state_reason or {}).items()]) or "なし"
        change_label = state_meta.get("client_change_talk_type", "")
        sustain_label = state_meta.get("client_sustain_talk_type", "")

        system_prompt = (
            (self.persona or "")
            + "\n\n"
            "- 上記ペルソナとして、クライアントの返答を基本1文、長くても3文で自然に生成してください。\n"
            "- 内部状態や理由、ラベルは出力に明示せず、人物像の背景情報としてのみ解釈してください。\n"
            "- 単に「はい」と答えるだけのこともあれば、直前のカウンセラー発話にまず一言リアクションしつつ、自分の状況に即した応答をすることもあります。新しい具体化・揺れ・問い返しなどを少し加えて返すこともあります。\n"
            "- 立て続けに質問をすることもあれば、質問ばかり繰り返さずに、相手の発言を踏まえて思ったことや感じたことを表明するだけのこともあります。\n"
            "- presenting_concern を丸ごと再掲せず、流れに沿った短い返答にしてください。\n"
            "- 【禁止】JSON/コード/記号だけの出力（{} や [] など）はしない。テキストのみ。空行や空オブジェクトも返さない。\n"
            "-  更新後の内部状態(参考): "
            + state_text
            + "\n内部状態変化の理由(参考): "
            + reasons_text
            + f"\n変化言語ラベル: {change_label} / 持続言語ラベル: {sustain_label}\n"
            "例: 「朝がつらいときは、準備に時間が足りなくて焦ります。」\n"
            "- 前提としてクライアントは悩んでいる。どうしていいかわからない。\n"
            "- 助言に対して、まずは 自分の状況に合うか を確認する。\n"
            "- 同意する前に、不安/障壁/コスト を1つ挙げる。\n"
            "- 行動案を自分から作らず、質問で返すか難しさの説明をする。\n"
            "- 納得できない時は、丁寧に保留する。\n"
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for turn in history[-self.max_history_turns :]:
            speaker = getattr(turn, "speaker", "")
            text = getattr(turn, "text", "")
            if not isinstance(text, str):
                continue
            role = "user" if speaker == "counselor" else "assistant"
            messages.append({"role": role, "content": text})

        if not (
            history
            and getattr(history[-1], "speaker", None) == "counselor"
            and getattr(history[-1], "text", "").strip() == counselor_text.strip()
        ):
            messages.append({"role": "user", "content": counselor_text})

        return messages
