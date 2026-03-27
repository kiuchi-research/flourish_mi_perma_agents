from __future__ import annotations

"""
クライアント側エージェント（シミュレーション用）

- conversation_environment.py から切り出したい場合のための独立モジュールです。
- 人間カウンセラー × LLMクライアント（ラベル付け用）
- LLMカウンセラー × LLMクライアント（自己対話シミュレーション）

の両方で共通に使えます。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Literal, Optional, Tuple
import json
import re

from mi_counselor_agent import LLMClient


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
        - raw: 生レスポンス
        - reply: 実際に使った返答
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
    # 返答＋内部状態更新
    # ------------------------------
    def respond(self, counselor_text: str, history: List[Any]) -> str:
        """
        - これまでの履歴＋現在の内部状態を LLM に渡す
        - LLM から
            { "reply": ..., "internal_state": {...}, "internal_state_reason": {...}, ... }
          という JSON を生成させる
        - reply を返しつつ、internal_state を更新する
        - 追加フィールド（internal_state_reason や自己ラベル）はデバッグ情報として保持する
        """
        # いま時点の内部状態
        state_dict = self.internal_state.to_dict()
        trait_dict = self.internal_state.to_traits_dict()
        old_state_full = self.internal_state.to_full_dict()

        # システムプロンプト：ペルソナ＋内部状態＋出力形式の指定
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
            "\n"
            "※ like_counselor と tension_counselor は、直近のカウンセラー発話の態度に応じて変化させてください。\n"
            "  例: 共感・尊重→ like↑ / tension↓、批判・見下し・命令口調→ like↓ / tension↑\n"
            "※ 数値は小数第2位まででOKです（例: 5.25）。\n\n"
            f"現時点のスコア: {json.dumps(state_dict, ensure_ascii=False)}\n\n"
            "【スコアの出やすさの特性（-1:出にくい, 0:標準, +1:出やすい）】\n"
            f"{json.dumps(trait_dict, ensure_ascii=False)}\n\n"
            "【出力に関する厳守事項】\n"
            "- internal_state には上記6項目すべてを必ず数値で含めてください（like_counselor と tension_counselor も含む）。\n"
            "- 変化がない場合は直前の値をそのまま入れてください。null や欠落は禁止です。\n\n"
            "これまでの会話と現在のスコアを踏まえて、"
            "直近のカウンセラーの発話に対するあなたの次の発話と、"
            "その発話後に更新されたスコアを出力してください。\n"
            "出力は必ず次の JSON 形式「だけ」で返してください:\n"
            "{\n"
            '  "reply": "<クライアントとしての次の発話>",\n'
            '  "internal_state": {\n'
            '    "pos_affect": 0〜10の数値,\n'
            '    "neg_affect": 0〜10の数値,\n'
            '    "importance_change": 0〜10の数値,\n'
            '    "confidence_change": 0〜10の数値,\n'
            '    "like_counselor": 0〜10の数値,\n'
            '    "tension_counselor": 0〜10の数値\n'
            "  },\n"
            '  "internal_state_reason": {\n'
            '    "pos_affect": "スコア変化の理由（省略可）",\n'
            '    "neg_affect": "スコア変化の理由（省略可）",\n'
            '    "importance_change": "スコア変化の理由（省略可）",\n'
            '    "confidence_change": "スコア変化の理由（省略可）",\n'
            '    "like_counselor": "スコア変化の理由（省略可）",\n'
            '    "tension_counselor": "スコア変化の理由（省略可）"\n'
            "  },\n"
            '  "client_change_talk_type": "変化言語の自己ラベル（無ければ空文字やnull）",\n'
            '  "client_sustain_talk_type": "持続言語の自己ラベル（無ければ空文字やnull）"\n'
            "}\n"
            "説明文や前置きは付けず、JSONのみを返してください。\n"
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # history は ConversationTurn を想定（speaker/text 属性）。型が違っても duck typing で動きます。
        for turn in history[-self.max_history_turns :]:
            speaker = getattr(turn, "speaker", "")
            text = getattr(turn, "text", "")
            if not isinstance(text, str):
                continue
            role = "user" if speaker == "counselor" else "assistant"
            messages.append({"role": role, "content": text})

        # 直近の counselor_text を明示的に加える（ただし、すでに同一内容が末尾にあるなら二重に入れない）
        if not (
            history
            and getattr(history[-1], "speaker", None) == "counselor"
            and getattr(history[-1], "text", "").strip() == counselor_text.strip()
        ):
            messages.append({"role": "user", "content": counselor_text})

        # シードが渡せる実装なら使う（渡せない場合は通常通り実行）
        try:
            raw = self.llm.generate(
                messages,
                temperature=float(self.temperature),
                seed=None if self.seed is None else int(self.seed),
            )
        except (TypeError, ValueError):
            raw = self.llm.generate(messages, temperature=float(self.temperature))

        reply, new_state_dict, state_reason, meta = self._parse_reply_and_state(str(raw))

        # ★ like/tension が動かない場合の保険（変化がないときだけ補正）
        new_state_dict = self._apply_relationship_heuristic(new_state_dict, counselor_text, meta)

        # 内部状態を更新
        self.internal_state = ClientInternalState.from_dict(new_state_dict, base=self.internal_state)

        # デバッグ情報を保持（最後に呼び出し側が参照できるようにする）
        self._last_debug_info = {
            "raw": str(raw),
            "reply": str(reply),
            "old_state": old_state_full,
            "new_state": self.internal_state.to_full_dict(),
            "internal_state_reason": state_reason,
            "meta": meta,
        }

        return str(reply).strip()

    def _parse_reply_and_state(self, raw: str) -> tuple[str, Dict[str, float], Dict[str, str], Dict[str, Any]]:
        """
        LLM からの出力をパースして
        - reply（発話）
        - internal_state（辞書形式）
        - internal_state_reason（各スコアの理由、任意）
        - meta（自己ラベルなどの付加情報）
        を取り出す。

        JSONでなかった場合は、raw全体を発話とみなし、内部状態は変えずに返します。
        ただし、テキスト中に { ... } 形式の JSON オブジェクトが含まれている場合は、
        その部分だけを抜き出して再度 JSON パースを試みます。
        """
        text = str(raw).strip()

        parse_status = "ok"

        # まずは素直に全体を JSON として解釈する
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 全体が JSON でない場合、"{ ... }" の最初のオブジェクトを抜き出して再トライ
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not m:
                return text, self.internal_state.to_full_dict(), {}, {"parse_status": "fallback_no_brace"}

            json_text = m.group(0)
            try:
                data = json.loads(json_text)
                parse_status = "fallback_brace"
            except json.JSONDecodeError:
                return text, self.internal_state.to_full_dict(), {}, {"parse_status": "fallback_json_error"}

        if not isinstance(data, dict):
            return text, self.internal_state.to_full_dict(), {}, {"parse_status": "fallback_non_dict"}

        # reply の取り出し
        reply = str(data.get("reply", "")).strip() or text

        # internal_state の取り出しとマージ
        state_in = data.get("internal_state") or {}
        merged_state = self.internal_state.to_dict()
        merged_full = self.internal_state.to_full_dict()

        # LLM がキー名を誤った場合の簡易救済（特に like/tension）
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

                # 直接キーが無い場合、エイリアスを探す
                if v is None:
                    for ak in state_aliases.get(key, []):
                        if ak in state_in:
                            v = state_in.get(ak)
                            alias_used[key] = ak
                            break

                if v is None:
                    continue

                try:
                    merged_state[key] = float(v)
                    provided_keys.append(key)
                    updated_any = True
                    has_state_input = True
                except (TypeError, ValueError):
                    continue

        state_reason_in = data.get("internal_state_reason") or {}
        state_reason: Dict[str, str] = {}
        if isinstance(state_reason_in, dict):
            for k, v in state_reason_in.items():
                if v is None:
                    continue
                state_reason[str(k)] = str(v)

        meta: Dict[str, Any] = {}
        meta["parse_status"] = parse_status
        meta["state_keys_provided"] = provided_keys
        if alias_used:
            meta["state_alias_used"] = alias_used

        for k in ("client_change_talk_type", "client_sustain_talk_type"):
            if k in data:
                meta[k] = data.get(k)
        if not has_state_input and meta["parse_status"] == "ok":
            meta["parse_status"] = "missing_internal_state"

        # 値を 0〜10 にクリップし、
        # 特性（trait_expression_*）に応じて変化方向を歪めつつ、
        # 必要なら変化量を制限
        max_step = self.max_state_step
        current = self.internal_state.to_dict()

        # 小数桁（保持）
        try:
            nd = int(self.state_decimal_places)
        except (TypeError, ValueError):
            nd = 2

        scale = float(getattr(self, "delta_scale", 1.0))

        # デバッグ用：現在の感度設定（指標ごとの変わりやすさ）
        meta["sensitivity"] = {
            "pos_affect": self._round_state(self._get_sensitivity("pos_affect")),
            "neg_affect": self._round_state(self._get_sensitivity("neg_affect")),
            "importance_change": self._round_state(self._get_sensitivity("importance_change")),
            "confidence_change": self._round_state(self._get_sensitivity("confidence_change")),
            "like_counselor": self._round_state(self._get_sensitivity("like_counselor")),
            "tension_counselor": self._round_state(self._get_sensitivity("tension_counselor")),
        }

        for k, v in list(merged_state.items()):
            try:
                target = float(v)
            except (TypeError, ValueError):
                continue

            # 0〜10にクリップ
            target = self._clip_0_10(target)

            # 現在値
            try:
                before = float(current.get(k, target))
            except (TypeError, ValueError):
                before = target

            # 特性に応じて「上がりやすさ／下がりやすさ」を反映したターゲット値へ変換
            adjusted = self.internal_state.adjust_by_expression(k, before, target)

            # 変化量をスケーリング
            sensitivity = self._get_sensitivity(k)

            # 変化量をスケーリング（全体スケール × 指標ごとの感度）
            delta = (adjusted - before) * scale * sensitivity

            # 変化量を制限
            if max_step is not None:
                try:
                    ms = float(max_step)
                except (TypeError, ValueError):
                    ms = None
                if ms is not None:
                    if delta > ms:
                        delta = ms
                    elif delta < -ms:
                        delta = -ms

            new_value = before + delta

            # 再度クリップして 0〜10 に収める
            new_value = self._clip_0_10(new_value)

            # ★ 小数第2位までに丸めて保持
            new_value = round(float(new_value), nd)

            merged_state[k] = new_value

        merged_full.update(merged_state)

        if not updated_any and meta.get("parse_status") == "ok":
            meta["parse_status"] = "state_not_updated"

        return reply, merged_full, state_reason, meta
