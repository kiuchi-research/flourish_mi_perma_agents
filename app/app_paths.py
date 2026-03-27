from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
APP_CONFIG_DIR = APP_DIR / "config"


def _first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        candidate = path.expanduser()
        if candidate.exists():
            return candidate
    return None


def resolve_env_path() -> Path:
    """
    app ローカルの .env を優先し、未配置なら従来のルート .env を使う。
    """
    return _first_existing((APP_DIR / ".env", PROJECT_ROOT / ".env")) or (APP_DIR / ".env")


def resolve_config_path(filename: str) -> Path:
    """
    app/config から設定ファイルを解決する。
    """
    return _first_existing((APP_CONFIG_DIR / filename,)) or (APP_CONFIG_DIR / filename)


def resolve_project_path(path: str | Path) -> Path:
    """
    相対パスは app/ を優先し、未一致ならプロジェクトルート基準で解決する。
    """
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return _first_existing((APP_DIR / candidate, PROJECT_ROOT / candidate)) or (APP_DIR / candidate)
