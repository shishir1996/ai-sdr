import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.crm.service import get_crm_summary, get_lead_pipeline, get_recent_activities

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/summary")
async def crm_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_crm_summary(db, user.org_id)


@router.get("/pipeline")
async def lead_pipeline(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await get_lead_pipeline(db, user.org_id)
    return {"leads": pipeline}


@router.get("/activity")
async def recent_activity(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    activities = await get_recent_activities(db, user.org_id)
    return {"activities": activities}
