from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vp_sales import LeadSourceControl


SOURCE_KEYS = [
    "google_search", "bing_search", "web_research", "business_directories",
    "company_websites", "google_maps_scraping", "apollo", "lusha",
    "rocketreach", "zoominfo", "linkedin_data", "news_sites",
    "startup_directories", "industry_listings",
]


async def get_source_control(db: AsyncSession, org_id: str) -> LeadSourceControl:
    result = await db.execute(
        select(LeadSourceControl).where(LeadSourceControl.org_id == org_id)
    )
    ctrl = result.scalar_one_or_none()
    if not ctrl:
        ctrl = LeadSourceControl(org_id=org_id)
        db.add(ctrl)
        await db.flush()
    return ctrl


async def update_source_control(db: AsyncSession, org_id: str, updates: dict) -> LeadSourceControl:
    ctrl = await get_source_control(db, org_id)
    for key, value in updates.items():
        if key in SOURCE_KEYS and hasattr(ctrl, key):
            setattr(ctrl, key, bool(value))
    await db.flush()
    return ctrl


async def is_source_enabled(db: AsyncSession, org_id: str, source_key: str) -> bool:
    ctrl = await get_source_control(db, org_id)
    return getattr(ctrl, source_key, False) if hasattr(ctrl, source_key) else False


async def get_enabled_sources(db: AsyncSession, org_id: str) -> list[str]:
    ctrl = await get_source_control(db, org_id)
    return [k for k in SOURCE_KEYS if getattr(ctrl, k, False)]


async def check_integration_available(db: AsyncSession, org_id: str, provider: str) -> bool:
    from app.services.integrations.service import get_active_integration
    integration = await get_active_integration(db, org_id, provider)
    return integration is not None
