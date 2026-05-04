"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NETVALIDATE_",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_key: str = Field(default="dev-key-change-me", description="API key for X-API-Key header")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Database
    db_url: str = Field(default="sqlite+aiosqlite:///./data/netvalidate.db")

    # Profiles
    profiles_dir: str = Field(default="./examples/profiles")

    # Logging
    log_level: str = Field(default="INFO")

    # Validation defaults
    job_timeout_seconds: int = Field(default=300)
    max_concurrent_jobs: int = Field(default=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
