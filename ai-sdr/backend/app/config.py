from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    APP_NAME: str = "AI SDR"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    IS_PRODUCTION: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./aisdr.db"
    DATABASE_URL_SYNC: str = "sqlite:///./aisdr.db"

    # Supabase (production)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # Redis / Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_TOKEN: str = ""
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # AI Providers
    TOGETHER_API_KEY: str = ""
    TOGETHER_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-v4-flash-free"
    DEFAULT_AI_MODEL: str = "deepseek-v4-flash-free"
    AI_TOKEN_BUDGET_MONTHLY: int = 100000000

    # Gmail
    GMAIL_CREDENTIALS_FILE: str = "credentials.json"
    GMAIL_TOKEN_FILE: str = "gmail_token.json"

    # VAPI
    VAPI_API_KEY: str = ""
    VAPI_BASE_URL: str = "https://api.vapi.ai"

    # Apollo
    APOLLO_API_KEY: str = ""

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "aisdr-uploads"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Email defaults
    DEFAULT_SMTP_HOST: str = ""
    DEFAULT_SMTP_PORT: int = 587
    DEFAULT_SMTP_USERNAME: str = ""
    DEFAULT_SMTP_PASSWORD: str = ""
    DEFAULT_SMTP_SENDER_EMAIL: str = ""
    DEFAULT_SMTP_SENDER_NAME: str = ""

    # Tracking
    TRACKING_DOMAIN: str = ""

    # Sentry
    SENTRY_DSN: str = ""


def _choose_env_file() -> str:
    """Pick the right env file based on environment."""
    # Railway or production: prefer .env.production, fall back to .env
    if os.getenv("RAILWAY_SERVICE_ID") or os.getenv("IS_PRODUCTION") == "true":
        prod_env = os.path.join(os.path.dirname(__file__), "..", ".env.production")
        if os.path.exists(prod_env):
            return prod_env
    # Local dev
    local_env = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(local_env):
        return local_env
    return ""


@lru_cache()
def get_settings() -> Settings:
    env_file = _choose_env_file()
    kwargs = {}
    if env_file:
        kwargs["_env_file"] = env_file
    s = Settings(**kwargs)
    # Debug: log raw env var value
    _raw_db = os.environ.get("DATABASE_URL")
    import logging as _log
    _log.getLogger(__name__).info("=== [DEBUG] os.environ DATABASE_URL=%s ===", _raw_db)
    _log.getLogger(__name__).info("=== [DEBUG] RAILWAY_SERVICE_ID=%s ===", os.environ.get("RAILWAY_SERVICE_ID"))
    _log.getLogger(__name__).info("=== [DEBUG] pydantic DATABASE_URL=%s ===", s.DATABASE_URL)
    # Railway injects DATABASE_URL and other env vars at the OS level.
    # Explicitly apply them to override defaults in case pydantic-settings
    # doesn't pick them up (observed on Railway deploys).
    _DB_KEY = "DATABASE_URL"
    if _DB_KEY in os.environ:
        object.__setattr__(s, _DB_KEY, os.environ[_DB_KEY])
    _DB_SYNC_KEY = "DATABASE_URL_SYNC"
    if _DB_SYNC_KEY in os.environ:
        object.__setattr__(s, _DB_SYNC_KEY, os.environ[_DB_SYNC_KEY])
    # Also force-apply SUPABASE_* and SECRET_KEY so auth works reliably
    for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY",
                "SECRET_KEY", "FRONTEND_URL", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        if key in os.environ:
            object.__setattr__(s, key, os.environ[key])
    return s
