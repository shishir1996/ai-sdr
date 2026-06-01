import os
from fastapi import APIRouter
from app.database import engine, settings

router = APIRouter()


@router.get("/health")
async def health_check():
    url = str(engine.url)
    if "@" in url:
        url = url.split("@")[0].split("://")[0] + "://****:****@" + url.split("@")[1][:30] + "..."
    return {
        "status": "ok",
        "service": "ai-sdr",
        "database": url,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "env_has_db_url": "DATABASE_URL" in os.environ,
        "railway_service_id": os.environ.get("RAILWAY_SERVICE_ID", "NOT_SET"),
    }


@router.get("/debug/env")
async def debug_env():
    keys = sorted(os.environ.keys())
    return {
        "env_keys": keys,
        "count": len(keys),
        "DATABASE_URL_present": "DATABASE_URL" in os.environ,
        "DATABASE_URL_SYNC_present": "DATABASE_URL_SYNC" in os.environ,
        "SUPABASE_URL_present": "SUPABASE_URL" in os.environ,
        "SECRET_KEY_present": "SECRET_KEY" in os.environ,
        "RAILWAY_SERVICE_ID": os.environ.get("RAILWAY_SERVICE_ID", "NOT_SET"),
        "RAILWAY_DEPLOYMENT_ID": os.environ.get("RAILWAY_DEPLOYMENT_ID"),
        "RAILWAY_GIT_COMMIT_SHA": os.environ.get("RAILWAY_GIT_COMMIT_SHA"),
        "RAILWAY_GIT_BRANCH": os.environ.get("RAILWAY_GIT_BRANCH"),
    }
