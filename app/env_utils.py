from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Literal

import yaml
from dotenv import load_dotenv


DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_MODEL_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "model_settings.yaml"

# mode ごとの組み込みデフォルト
DEFAULT_MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    # ---- カウンセラー（共通） ----
    "counselor_llm": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
    },
    "counselor_phase": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
        "enabled": True,
    },
    "counselor_action": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
        "enabled": True,
    },
    # ---- クライアント（共通） ----
    "client_profile_llm": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
    },
    "client_state_llm": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
    },
    "client_reply_llm": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "never",
        "temperature_policy": "auto",
        "system_handling": "as_input",
    },
    # ---- 安全判定・応答評価（任意で有効化） ----
    # ---- 安全判定・応答評価（任意で有効化） ----
    "counselor_risk_detector": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
        "enabled": False,
        "temperature": 0.0,
        "max_history_turns": 8,
    },
    "counselor_mi_evaluator": {
        "api": "responses",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "verbosity": "low",
        "json_mode": "auto",
        "temperature_policy": "auto",
        "system_handling": "as_input",
        "enabled": False,
        "temperature": 0.0,
        "max_history_turns": 6,
        "rewrite_threshold": None,
    },
}


def load_openai_api_key(env_path: Path = DEFAULT_ENV_PATH) -> str:
    """
    .env（OPENAI_API_KEY）または環境変数から API キーを取得する共通ユーティリティ。
    """
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(".env または環境変数に OPENAI_API_KEY が設定されていません。")
    return api_key


def _load_model_settings(path: Path = DEFAULT_MODEL_CONFIG_PATH) -> Dict[str, Dict[str, Any]]:
    """YAML からモデル設定を読み込む（無ければ空 dict）。"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _merge_default_and_yaml(mode: str, cfg_from_yaml: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(DEFAULT_MODEL_CONFIG.get(mode, {}))
    override = cfg_from_yaml.get(mode)
    if isinstance(override, dict):
        base.update(override)
    return base


def get_model_config(
    mode: str,
    *,
    config_path: Path = DEFAULT_MODEL_CONFIG_PATH,
    role: Literal["counselor", "client", "none"] = "counselor",
    fallback_modes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    モードごとのモデル設定を一元管理する。
    優先順位: env > YAML > 組み込みデフォルト
    fallback_modes が指定されていて mode が YAML に存在しない場合、
    最初に見つかった代替モードの設定を採用する。
    """
    cfg_from_yaml = _load_model_settings(config_path)
    base = _merge_default_and_yaml(mode, cfg_from_yaml)

    if mode not in cfg_from_yaml and fallback_modes:
        for alt in fallback_modes:
            candidate = _merge_default_and_yaml(alt, cfg_from_yaml)
            if candidate:
                base = candidate
                break

    # 環境変数で上書き（ロール別の慣例に合わせる）
    if role == "counselor":
        base["model"] = os.getenv("OPENAI_MODEL", base.get("model", ""))
        base["reasoning_effort"] = os.getenv("OPENAI_REASONING_EFFORT", base.get("reasoning_effort", ""))
        base["verbosity"] = os.getenv("OPENAI_VERBOSITY", base.get("verbosity", ""))
    elif role == "client":
        base["model"] = os.getenv("OPENAI_CLIENT_MODEL", base.get("model", ""))
        base["reasoning_effort"] = os.getenv("OPENAI_CLIENT_REASONING_EFFORT", base.get("reasoning_effort", ""))
        base["verbosity"] = os.getenv("OPENAI_CLIENT_VERBOSITY", base.get("verbosity", ""))

    # api/json_mode/system_handling/temperature_policy は YAML or デフォルトをそのまま使う
    return base


def build_llm_from_config(model_cfg: Dict[str, Any], api_key: str) -> Any:
    """
    model_settings.yaml で定義した辞書から LLMClient を構築する共通ヘルパー。
    """
    from openai_llm import OpenAIChatCompletionsLLM, OpenAIResponsesLLM

    api_type = str(model_cfg.get("api", "responses")).strip().lower()
    if api_type == "chat":
        return OpenAIChatCompletionsLLM(api_key=api_key, model=model_cfg.get("model", ""))

    return OpenAIResponsesLLM(
        api_key=api_key,
        model=model_cfg.get("model", ""),
        reasoning_effort=model_cfg.get("reasoning_effort"),
        verbosity=model_cfg.get("verbosity"),
        json_mode=model_cfg.get("json_mode", "auto"),
        temperature_policy=model_cfg.get("temperature_policy", "auto"),
        system_handling=model_cfg.get("system_handling", "as_input"),
    )
