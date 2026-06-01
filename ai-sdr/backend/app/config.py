from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    APP_NAME: str = "AI SDR"
    APP_VERSION: str = "1.0.1"
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
    for _key in (
        "DATABASE_URL", "DATABASE_URL_SYNC",
        "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY",
        "SECRET_KEY", "FRONTEND_URL", "IS_PRODUCTION",
        "OPENAI_API_KEY", "OPENROUTER_API_KEY",
    ):
        _val = os.environ.get(_key)
        if _val is not None:
            kwargs[_key] = _val
    # If Railway auto-injects DATABASE_URL (postgresql://... sync URL),
    # auto-convert to async for the async engine
    db_url = kwargs.get("DATABASE_URL", "")
    if db_url.startswith("postgresql://"):
        kwargs["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Derive DATABASE_URL_SYNC from DATABASE_URL if not provided
    if "DATABASE_URL_SYNC" not in kwargs:
        async_url = kwargs.get("DATABASE_URL", "")
        if "postgresql+asyncpg://" in async_url:
            kwargs["DATABASE_URL_SYNC"] = async_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return Settings(**kwargs)
