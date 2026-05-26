from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.feature_flag import FeatureFlag, OrgFeatureFlag


DEFAULT_FEATURE_FLAGS = {
    "email_outreach_enabled": True,
    "calls_enabled": False,
    "lead_extraction_apollo_enabled": True,
    "lead_extraction_web_enabled": True,
    "lead_extraction_csv_enabled": True,
    "ai_lead_scoring_enabled": True,
    "ai_email_drafting_enabled": True,
    "ai_call_script_enabled": True,
}


async def get_feature_flag(db: AsyncSession, key: str) -> bool:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    if flag is None:
        return DEFAULT_FEATURE_FLAGS.get(key, False)
    return flag.enabled


async def get_org_feature_override(db: AsyncSession, org_id: str, key: str) -> Optional[bool]:
    result = await db.execute(
        select(OrgFeatureFlag).where(
            OrgFeatureFlag.org_id == org_id,
            OrgFeatureFlag.flag_key == key,
        )
    )
    override = result.scalar_one_or_none()
    if override is not None:
        return override.enabled
    return None


async def is_feature_enabled(db: AsyncSession, key: str, org_id: Optional[str] = None) -> bool:
    if org_id:
        override = await get_org_feature_override(db, org_id, key)
        if override is not None:
            return override
    return await get_feature_flag(db, key)


async def set_feature_flag(db: AsyncSession, key: str, enabled: bool):
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    if flag:
        flag.enabled = enabled
    else:
        flag = FeatureFlag(key=key, enabled=enabled)
        db.add(flag)
    await db.flush()
    return flag


async def set_org_feature_override(db: AsyncSession, org_id: str, key: str, enabled: bool):
    result = await db.execute(
        select(OrgFeatureFlag).where(
            OrgFeatureFlag.org_id == org_id,
            OrgFeatureFlag.flag_key == key,
        )
    )
    override = result.scalar_one_or_none()
    if override:
        override.enabled = enabled
    else:
        override = OrgFeatureFlag(org_id=org_id, flag_key=key, enabled=enabled)
        db.add(override)
    await db.flush()
    return override


async def get_all_feature_flags(db: AsyncSession) -> list[FeatureFlag]:
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    return result.scalars().all()


async def seed_feature_flags(db: AsyncSession):
    for key, default in DEFAULT_FEATURE_FLAGS.items():
        result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
        if not result.scalar_one_or_none():
            db.add(FeatureFlag(key=key, enabled=default))
    await db.flush()
