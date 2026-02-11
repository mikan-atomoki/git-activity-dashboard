"""Application configuration loaded from environment variables via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values are loaded from environment variables and/or a .env file located
    in the same directory as this module.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/git_dashboard"
    )

    # --- Authentication / JWT ---
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Encryption (GitHub personal access tokens) ---
    ENCRYPTION_KEY: str

    # --- External APIs ---
    GEMINI_API_KEY: str

    # --- Localisation / Scheduling ---
    DEFAULT_TIMEZONE: str = "Asia/Tokyo"
    SYNC_INTERVAL_HOURS: int = 6


settings = Settings()  # type: ignore[call-arg]
