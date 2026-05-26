from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_admin
from app.services.feature_flag.service import get_all_feature_flags, set_feature_flag, seed_feature_flags

router = APIRouter(prefix="/admin", tags=["admin"])


class FeatureFlagUpdate(BaseModel):
    enabled: bool


@router.get("/feature-flags")
async def list_feature_flags(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    flags = await get_all_feature_flags(db)
    return [{"key": f.key, "enabled": f.enabled, "description": f.description} for f in flags]


@router.put("/feature-flags/{key}")
async def update_feature_flag(
    key: str,
    body: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    flag = await set_feature_flag(db, key, body.enabled)
    return {"key": flag.key, "enabled": flag.enabled}


@router.post("/feature-flags/seed")
async def seed_flags(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await seed_feature_flags(db)
    return {"status": "seeded"}
