from functools import lru_cache
import os
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


ENV_ALIASES = {
    "llm_base_url": ("LLM_BASE_URL", "OLLAMA_BASE_URL"),
}


def is_wsl_environment() -> bool:
    if os.getenv("WSL_DISTRO_NAME") or os.getenv("WSL_INTEROP"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def get_wsl_host_ip() -> str:
    default_ip = "127.0.0.1"
    if not is_wsl_environment():
        return default_ip
    try:
        route_output = subprocess.check_output(
            ["ip", "route", "show", "default"], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        if "via" in route_output:
            return route_output.split("via", 1)[1].split()[0]
    except Exception:
        pass
    return default_ip


def default_llm_base_url() -> str:
    return f"http://{get_wsl_host_ip()}:11434"


class Settings(BaseModel):
    app_name: str = "Bản Đồ Tin"
    database_path: Path = Path("app/data/ban_do_tin.db")
    seed_data_path: Path = Path("app/data/demo_seed.json")
    static_dir: Path = Path("app/static")
    demo_mode: bool = True

    # Lazy LLM enrichment (Ollama). Enrichment runs only when a user opens an
    # event detail, is cached permanently, and degrades gracefully if disabled
    # or unreachable. Set llm_enabled=false to always use deterministic output.
    llm_enabled: bool = True
    llm_base_url: str = Field(default_factory=default_llm_base_url)
    llm_model: str = "qwen3.5:9b"
    llm_timeout: float = 30.0


def _get_env_value(key: str) -> str | None:
    for env_key in ENV_ALIASES.get(key, (key.upper(),)):
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
    return None


@lru_cache
def get_settings() -> Settings:
    values: dict[str, Any] = {}
    for key, field in Settings.model_fields.items():
        env_value = _get_env_value(key)
        if env_value is None:
            continue
        if field.annotation is bool:
            values[key] = env_value.lower() in {"1", "true", "yes", "on"}
        elif field.annotation is float:
            values[key] = float(env_value)
        elif field.annotation is Path:
            values[key] = Path(env_value)
        else:
            values[key] = env_value
    return Settings(**values)
