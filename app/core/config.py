from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration — every value comes from an env var,
    never a hardcoded literal in application code (twelve-factor: config
    lives in the environment, not in the codebase).

    .env is for local dev only and is gitignored; .env.example documents
    every key that must be set, with no real secrets in it.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    APP_NAME: str = "MediStock"

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    WEBHOOK_SECRET: str = "test-webhook-secret-key"
    WEBHOOK_SIGNING_SECRET: str = "test-webhook-secret-key"
    SUPPLIER_BASIC_AUTH_USER: str = "supplier"
    SUPPLIER_BASIC_AUTH_PASSWORD: str = "change-me"


@lru_cache
def get_settings() -> Settings:
    """Cached so env vars are parsed once per process, not on every
    single dependency injection. Tests that need different settings
    call get_settings.cache_clear() first.
    """
    return Settings()
