"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application environment
    env: Literal["dev", "test", "staging", "prod"] = "dev"

    # Database
    database_url: str = "postgresql+asyncpg://acucare:acucare@localhost:5432/acucare"

    # Security
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Patient magic links
    patient_magic_link_ttl_minutes: int = 30

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_storage_url: str | None = None  # Redis URL for multi-worker deployments

    # Logging
    log_level: str = "INFO"

    # Database initialization
    init_db_on_startup: bool = False

    # Safety banner configuration (shown during intake)
    safety_banner_text: str = (
        "If you are experiencing a mental health emergency or have thoughts of "
        "harming yourself or others, please call 999 or go to your nearest A&E. "
        "You can also contact the Samaritans 24/7 on 116 123 (free call)."
    )
    safety_banner_enabled: bool = True

    # Current consent version (increment when consent terms change)
    consent_version: str = "1.0"

    @property
    def database_url_sync(self) -> str:
        """Return sync database URL for Alembic."""
        return self.database_url.replace("+asyncpg", "+psycopg2").replace(
            "+aiosqlite", ""
        )

    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.env == "dev"

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.env == "prod"

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.env == "test"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
