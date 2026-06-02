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


@router.get("/debug/db-test")
async def debug_db_test():
    from app.database import async_session_factory
    from app.models.user import User
    from sqlalchemy import select, text
    import traceback

    results = {}
    errors = {}

    try:
        async with async_session_factory() as db:
            try:
                result = await db.execute(text("SELECT 1"))
                results["select_1"] = result.scalar()
            except Exception as e:
                errors["select_1"] = traceback.format_exc()

            try:
                result = await db.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
                results["table_count"] = result.scalar()
            except Exception as e:
                errors["table_count"] = traceback.format_exc()

            try:
                result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
                tables = [row[0] for row in result.fetchall()]
                results["tables"] = tables
            except Exception as e:
                errors["tables"] = traceback.format_exc()

            try:
                result = await db.execute(select(User).where(User.email == "test@test.com"))
                results["user_query"] = "ok (no user found)"
            except Exception as e:
                errors["user_query"] = traceback.format_exc()
    except Exception as e:
        errors["session"] = traceback.format_exc()

    return {"results": results, "errors": errors}
