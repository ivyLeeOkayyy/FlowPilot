import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict


def _load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_name: str = "flowpilot"
    app_title: str = "FlowPilot"
    app_version: str = "0.1.0"
    app_description: str = (
        "FlowPilot is a lightweight AI-assisted automation builder created as a "
        "hackathon demo."
    )
    llm_provider: str = _env("LLM_PROVIDER", "mock") or "mock"
    llm_base_url: str | None = _env("LLM_BASE_URL")
    llm_api_key: str | None = _env("LLM_API_KEY")
    llm_model: str | None = _env("LLM_MODEL")
    llm_timeout_seconds: int = _env_int("LLM_TIMEOUT_SECONDS", 30)
    deepseek_api_key: str | None = _env("DEEPSEEK_API_KEY")
    deepseek_base_url: str = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com"
    deepseek_model: str = _env("DEEPSEEK_MODEL", "deepseek-chat") or "deepseek-chat"


settings = Settings()


def llm_config_diagnostics() -> dict[str, str | int | bool]:
    return {
        "llm_provider": os.getenv("LLM_PROVIDER") or settings.llm_provider,
        "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL") or settings.deepseek_base_url,
        "deepseek_model": os.getenv("DEEPSEEK_MODEL") or settings.deepseek_model,
        "llm_timeout_seconds": int(
            os.getenv("LLM_TIMEOUT_SECONDS") or settings.llm_timeout_seconds
        ),
        "deepseek_api_key_configured": bool(
            os.getenv("DEEPSEEK_API_KEY") or settings.deepseek_api_key
        ),
    }
