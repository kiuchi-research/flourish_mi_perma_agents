from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from openai import OpenAI


def _extract_output_text_from_response(response: Any) -> str:
    """
    responses.create の返り値からテキストを抽出。
    SDKが提供する output_text があればそれを優先し、無ければ output を走査して連結する。
    """
    out_text = getattr(response, "output_text", None)
    if isinstance(out_text, str):
        return out_text

    chunks: List[str] = []
    output = getattr(response, "output", None)
    if output:
        for item in output:
            content = getattr(item, "content", None)
            if not content:
                continue
            for c in content:
                t = getattr(c, "text", None)
                if isinstance(t, str):
                    chunks.append(t)
    return "".join(chunks)


def _should_use_json_mode(messages: List[Dict[str, str]]) -> bool:
    """本文に 'json' が含まれていれば JSON モードに寄せる簡易判定。"""
    try:
        for m in messages:
            content = str(m.get("content", "") or "").lower()
            if "json" in content:
                return True
    except Exception:
        return False
    return False


def _model_disallows_temperature(model: str) -> bool:
    """
    GPT-5-mini / GPT-5-nano 等では temperature を送らない方が安全。
    （スナップショット名も考慮して prefix 判定）
    """
    m = (model or "").strip()
    return m == "gpt-5" or m.startswith("gpt-5-mini") or m.startswith("gpt-5-nano")


class OpenAIChatCompletionsLLM:
    """v1 OpenAI Python SDK の chat.completions を使う単純な LLMClient。"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, messages: List[Dict[str, str]], *, temperature: float = 0.2, **kwargs: Any) -> str:
        extra: Dict[str, Any] = dict(kwargs) if kwargs else {}
        extra.pop("messages", None)
        extra.pop("response_format", None)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **extra,
        )
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        try:
            return "".join(getattr(part, "text", "") for part in content or [])
        except Exception:
            return ""


class OpenAIResponsesLLM:
    """
    OpenAI Responses API 用の LLMClient。
    - system_handling="as_input"（既定）: system ロールも input に含める（現行互換）
      "instructions": system ロールを instructions に集約
    - json_mode: auto / always / never
    - temperature_policy: auto（gpt-5* は送らない）/ always / never
    - 余計な kwargs は安全側で捨てる
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "gpt-5-mini",
        reasoning_effort: Optional[str] = "medium",
        verbosity: Optional[str] = "low",
        store: bool = False,
        safety_identifier: Optional[str] = None,
        system_handling: Literal["instructions", "as_input"] = "as_input",
        json_mode: Literal["auto", "always", "never"] = "auto",
        temperature_policy: Literal["auto", "always", "never"] = "auto",
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity
        self.store = store
        self.safety_identifier = safety_identifier
        self.system_handling = system_handling
        self.json_mode = json_mode
        self.temperature_policy = temperature_policy

    def _split_messages(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        instruction_parts: List[str] = []
        input_items: List[Dict[str, Any]] = []

        if self.system_handling == "instructions":
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    instruction_parts.append(str(content))
                else:
                    input_items.append({"role": role, "content": content})
            return {
                "instructions": "\n\n".join(instruction_parts) if instruction_parts else None,
                "input": input_items if input_items else "",
            }

        # as_input: そのまま渡す
        return {"instructions": None, "input": messages}

    def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        extra: Dict[str, Any] = dict(kwargs) if kwargs else {}
        # Responses API 互換のために不要/危険な引数を除去
        extra.pop("seed", None)
        extra.pop("messages", None)
        extra.pop("response_format", None)

        if "max_tokens" in extra and "max_output_tokens" not in extra:
            extra["max_output_tokens"] = extra.pop("max_tokens")

        req: Dict[str, Any] = {
            "model": self.model,
            "store": self.store,
        }
        req.update(self._split_messages(messages))

        # JSON モード判定
        text_format: Dict[str, Any] = {"type": "text"}
        if self.json_mode == "always" or (self.json_mode == "auto" and _should_use_json_mode(messages)):
            text_format = {"type": "json_object"}
        req["text"] = {"format": text_format}
        if self.verbosity:
            req["text"]["verbosity"] = self.verbosity

        # reasoning effort
        if self.reasoning_effort:
            req["reasoning"] = {"effort": self.reasoning_effort}

        # safety_identifier
        if self.safety_identifier:
            req["safety_identifier"] = self.safety_identifier

        # temperature
        send_temperature = False
        if self.temperature_policy == "always":
            send_temperature = True
        elif self.temperature_policy == "auto" and not _model_disallows_temperature(self.model):
            send_temperature = True

        if send_temperature:
            req["temperature"] = float(temperature)

        # 残りのオプションをマージ（model/input/store/text を上書きしない）
        for k, v in extra.items():
            if k in ("model", "input", "store", "text"):
                continue
            req[k] = v

        response = self.client.responses.create(**req)
        return _extract_output_text_from_response(response)
