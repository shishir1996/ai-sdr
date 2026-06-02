import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.vp_sales import LeadSourceControl
from app.utils.auth import get_current_user
from app.services.lead_sources.service import (
    get_source_control, update_source_control, get_enabled_sources,
    SOURCE_KEYS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lead-sources", tags=["lead-sources"])


class SourceToggleRequest(BaseModel):
    google_search: Optional[bool] = None
    bing_search: Optional[bool] = None
    web_research: Optional[bool] = None
    business_directories: Optional[bool] = None
    company_websites: Optional[bool] = None
    google_maps_scraping: Optional[bool] = None
    apollo: Optional[bool] = None
    lusha: Optional[bool] = None
    rocketreach: Optional[bool] = None
    zoominfo: Optional[bool] = None
    linkedin_data: Optional[bool] = None
    news_sites: Optional[bool] = None
    startup_directories: Optional[bool] = None
    industry_listings: Optional[bool] = None


@router.get("/")
async def get_sources(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctrl = await get_source_control(db, user.org_id)
    return {
        "sources": {k: getattr(ctrl, k, False) for k in SOURCE_KEYS},
    }


@router.put("/")
async def update_sources(
    req: SourceToggleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = req.model_dump(exclude_none=True)
    ctrl = await update_source_control(db, user.org_id, updates)
    return {
        "message": "Lead sources updated",
        "sources": {k: getattr(ctrl, k, False) for k in SOURCE_KEYS},
    }


@router.get("/enabled")
async def list_enabled_sources(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enabled = await get_enabled_sources(db, user.org_id)
    return {"enabled_sources": enabled}


@router.get("/check/{source_key}")
async def check_source(
    source_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.lead_sources.service import is_source_enabled
    enabled = await is_source_enabled(db, user.org_id, source_key)
    return {"source": source_key, "enabled": enabled}
