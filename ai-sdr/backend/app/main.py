from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db, async_session_factory, init_supabase
from app.routers import router as health_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.leads import router as leads_router
from app.routers.campaigns import router as campaigns_router
from app.routers.deals import router as deals_router
from app.routers.emails import router as emails_router
from app.routers.email import router as email_router
from app.routers.analytics import router as analytics_router
from app.routers.integrations import router as integrations_router
from app.routers.sdr import router as sdr_router
from app.routers.settings_router import router as settings_router
from app.routers.scrape_profiles import router as scrape_profiles_router
from app.routers.smtp import router as smtp_router
from app.routers.audit import router as audit_router
from app.routers.vapi_admin import router as vapi_admin_router
from app.routers.calls import router as calls_router
from app.routers.vapi_webhook import router as vapi_webhook_router
from app.routers.payments import router as payments_router
from app.routers.calendar import router as calendar_router
from app.services.feature_flag.service import seed_feature_flags
from app.services.security.middleware import SecurityHeadersMiddleware
from app.services.redis_service import init_redis
from app.models.agent import SDRProfile
from sqlalchemy import select

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    _log = logging.getLogger(__name__)
    init_supabase()
    db_ok = await init_db()
    await init_redis()
    if db_ok:
        try:
            async with async_session_factory() as db:
                await seed_feature_flags(db)
                await db.commit()
        except Exception as e:
            _log.warning("seed_feature_flags failed (non-fatal): %s", e)
        async with async_session_factory() as db:
            result = await db.execute(
                select(SDRProfile).where(SDRProfile.is_active.is_(True))
            )
            active_profiles = result.scalars().all()
            await db.commit()
        for profile in active_profiles:
            import asyncio
            from app.services.sdr.sdr_orchestrator import start_sdr_cycle
            print(f"[startup] Restarting SDR cycle for {profile.name} (org={profile.org_id})", flush=True)
            asyncio.create_task(start_sdr_cycle(profile.org_id, sdr_profile_id=profile.id))
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    SecurityHeadersMiddleware,
    is_production=settings.IS_PRODUCTION,
    frontend_url=settings.FRONTEND_URL,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.IS_PRODUCTION:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request.headers.get("x-request-id", "")},
        )
    raise exc


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(deals_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(emails_router, prefix="/api/v1")
app.include_router(email_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(sdr_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(scrape_profiles_router, prefix="/api/v1")
app.include_router(smtp_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(vapi_admin_router, prefix="/api/v1")
app.include_router(calls_router, prefix="/api/v1")
app.include_router(vapi_webhook_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")
