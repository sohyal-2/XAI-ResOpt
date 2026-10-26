from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "XAI-ResOpt API"
    app_env: str = "development"
    database_url: str = "postgresql://xai_resopt:change-me-for-local-development@localhost:5432/xai_resopt"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    max_upload_size_bytes: int = 10 * 1024 * 1024
    url_fetch_timeout_seconds: float = 10.0
    github_token: str | None = None

    # AI Provider & Model Configuration
    ai_provider: str = "auto"  # "auto", "mock", "openai", "anthropic", "gemini", "ollama", "openrouter"
    ai_timeout_seconds: float = 30.0
    ai_max_retries: int = 2

    # OpenAI / Compatible Provider
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    # OpenRouter Provider
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Anthropic Provider
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_base_url: str = "https://api.anthropic.com"

    # Google Gemini Provider (accepts GEMINI_API_KEY or GOOGLE_API_KEY)
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com"

    # Local / Ollama Provider
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
            ".env",
            "../.env",
        ),
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
