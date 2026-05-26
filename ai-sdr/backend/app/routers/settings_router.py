import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.settings import OrgSettings
from app.utils.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


class OrgSettingsUpdate(BaseModel):
    sell_type: str = "product"
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    payment_link: Optional[str] = None
    service_description: Optional[str] = None
    calendar_link: Optional[str] = None
    knowledge_base: Optional[str] = None
    scraping_enabled: bool = False
    approved_countries: str = ""
    approved_categories: str = ""


@router.get("/org")
async def get_org_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(OrgSettings).where(OrgSettings.org_id == user.org_id))
    s = result.scalar_one_or_none()
    if not s:
        return {
            "sell_type": "product",
            "product_name": None,
            "product_description": None,
            "payment_link": None,
            "service_description": None,
            "calendar_link": None,
            "knowledge_base": None,
            "scraping_enabled": False,
            "approved_countries": "",
            "approved_categories": "",
        }
    return {
        "sell_type": s.sell_type,
        "product_name": s.product_name,
        "product_description": s.product_description,
        "payment_link": s.payment_link,
        "service_description": s.service_description,
        "calendar_link": s.calendar_link,
        "knowledge_base": s.knowledge_base,
        "scraping_enabled": s.scraping_enabled if s.scraping_enabled is not None else False,
        "approved_countries": s.approved_countries or "",
        "approved_categories": s.approved_categories or "",
    }


@router.put("/org")
async def update_org_settings(
    body: OrgSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(OrgSettings).where(OrgSettings.org_id == user.org_id))
    s = result.scalar_one_or_none()
    data = body.model_dump()
    if s:
        for key, val in data.items():
            setattr(s, key, val)
    else:
        s = OrgSettings(org_id=user.org_id, **data)
        db.add(s)
    await db.flush()
    return {"status": "saved"}


@router.get("/scrape-permissions")
async def get_scrape_permissions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(OrgSettings).where(OrgSettings.org_id == user.org_id))
    s = result.scalar_one_or_none()
    if not s:
        return {
            "scraping_enabled": False,
            "approved_countries": [],
            "approved_categories": [],
        }
    countries = []
    if s.approved_countries:
        try:
            countries = json.loads(s.approved_countries)
        except Exception:
            countries = [c.strip() for c in s.approved_countries.split(",") if c.strip()]
    categories = []
    if s.approved_categories:
        try:
            categories = json.loads(s.approved_categories)
        except Exception:
            categories = [c.strip() for c in s.approved_categories.split(",") if c.strip()]
    return {
        "scraping_enabled": s.scraping_enabled if s.scraping_enabled is not None else False,
        "approved_countries": countries,
        "approved_categories": categories,
    }
