"""Application settings, loaded from environment / backend/.env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory — .env and the SQLite file live here.
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BACKEND_DIR.parent / "prompts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-8"
    llm_timeout_seconds: float = 30.0

    # Auth
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_expire_minutes: int = 480
    jwt_algorithm: str = "HS256"

    # DB
    database_url: str = "sqlite:///./financeos.db"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
