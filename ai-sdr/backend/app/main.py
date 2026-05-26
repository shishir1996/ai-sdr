from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
from app.routers.analytics import router as analytics_router
from app.routers.integrations import router as integrations_router
from app.routers.sdr import router as sdr_router
from app.routers.settings_router import router as settings_router
from app.routers.scrape_profiles import router as scrape_profiles_router
from app.routers.smtp import router as smtp_router
from app.routers.audit import router as audit_router
from app.services.feature_flag.service import seed_feature_flags
from app.services.security.middleware import SecurityHeadersMiddleware, get_cors_origins

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_supabase()
    await init_db()
    async with async_session_factory() as db:
        await seed_feature_flags(db)
        await db.commit()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(settings.IS_PRODUCTION, settings.FRONTEND_URL),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
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
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(sdr_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(scrape_profiles_router, prefix="/api/v1")
app.include_router(smtp_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
