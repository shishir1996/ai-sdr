from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, async_session_factory
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
from app.services.feature_flag.service import seed_feature_flags

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session_factory() as db:
        await seed_feature_flags(db)
        await db.commit()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
