import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.agent import SDRProfile, LeadState, AgentLog
from app.models.lead import Lead
from app.utils.auth import get_current_user

router = APIRouter(prefix="/sdr", tags=["sdr"])


def serialize_sdr(profile: SDRProfile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name or "AI SDR",
        "region": profile.region or "",
        "sell_type": profile.sell_type,
        "product_name": profile.product_name,
        "product_description": profile.product_description,
        "payment_link": profile.payment_link,
        "service_description": profile.service_description,
        "calendar_link": profile.calendar_link,
        "target_titles": profile.target_titles or "",
        "target_industries": profile.target_industries or "",
        "target_locations": profile.target_locations or "",
        "target_company_size_min": profile.target_company_size_min,
        "target_company_size_max": profile.target_company_size_max,
        "lead_sources": profile.lead_sources or "",
        "sdr_personality": profile.sdr_personality or "",
        "outreach_tone": profile.outreach_tone or "professional",
        "max_daily_emails": profile.max_daily_emails or 20,
        "max_daily_calls": profile.max_daily_calls or 10,
        "max_daily_linkedin": profile.max_daily_linkedin or 15,
        "max_daily_likes": profile.max_daily_likes or 20,
        "max_daily_comments": profile.max_daily_comments or 10,
        "linkedin_connect_enabled": bool(profile.linkedin_connect_enabled),
        "linkedin_dm_enabled": bool(profile.linkedin_dm_enabled),
        "linkedin_like_enabled": bool(profile.linkedin_like_enabled),
        "linkedin_comment_enabled": bool(profile.linkedin_comment_enabled),
        "linkedin_engagement_feed": profile.linkedin_engagement_feed or "",
        "web_scrape_targets": profile.web_scrape_targets or "",
        "auto_scrape_enabled": bool(profile.auto_scrape_enabled),
        "scrape_business_category": profile.scrape_business_category or "",
        "scrape_country": profile.scrape_country or "",
        "scrape_directory_urls": profile.scrape_directory_urls or "",
        "campaign_sequence": profile.campaign_sequence or "",
        "is_active": bool(profile.is_active),
        "leads_target": profile.leads_target or 100,
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
    }


@router.get("/profiles")
async def list_sdr_profiles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id).order_by(SDRProfile.created_at.desc())
    )
    return [serialize_sdr(p) for p in result.scalars().all()]


class SDRCreate(BaseModel):
    name: str = "AI SDR"
    region: str = ""
    sell_type: str = "product"
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    payment_link: Optional[str] = None
    service_description: Optional[str] = None
    calendar_link: Optional[str] = None
    target_titles: str = ""
    target_industries: str = ""
    target_locations: str = ""
    target_company_size_min: Optional[int] = None
    target_company_size_max: Optional[int] = None
    lead_sources: str = ""
    sdr_personality: str = ""
    outreach_tone: str = "professional"
    max_daily_emails: int = 20
    max_daily_calls: int = 10
    max_daily_linkedin: int = 15
    max_daily_likes: int = 20
    max_daily_comments: int = 10
    linkedin_connect_enabled: bool = True
    linkedin_dm_enabled: bool = True
    linkedin_like_enabled: bool = False
    linkedin_comment_enabled: bool = False
    linkedin_engagement_feed: str = ""
    web_scrape_targets: str = ""
    auto_scrape_enabled: bool = False
    scrape_business_category: str = ""
    scrape_country: str = ""
    scrape_directory_urls: str = ""
    campaign_sequence: str = ""
    leads_target: int = 100


@router.post("/profiles")
async def create_sdr_profile(
    body: SDRCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = SDRProfile(org_id=user.org_id, **body.model_dump())
    db.add(profile)
    await db.flush()
    return serialize_sdr(profile)


@router.get("/profiles/{profile_id}")
async def get_sdr_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    return serialize_sdr(profile)


@router.put("/profiles/{profile_id}")
async def update_sdr_profile(
    profile_id: str,
    body: SDRCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    for key, val in body.model_dump().items():
        setattr(profile, key, val)
    await db.flush()
    return serialize_sdr(profile)


@router.delete("/profiles/{profile_id}")
async def delete_sdr_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    await db.delete(profile)
    return {"status": "deleted"}


@router.post("/profiles/{profile_id}/activate")
async def activate_sdr(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.is_active = True
    await db.flush()

    from app.services.sdr.orchestrator import start_sdr_cycle
    import asyncio
    asyncio.create_task(start_sdr_cycle(user.org_id, sdr_profile_id=profile_id))

    return {"status": "activated", "sdr_id": profile_id, "name": profile.name}


@router.post("/profiles/{profile_id}/deactivate")
async def deactivate_sdr(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.is_active = False
    await db.flush()
    return {"status": "deactivated"}


@router.get("/activity")
async def get_agent_activity(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
    limit: int = 50,
):
    query = select(AgentLog).where(AgentLog.org_id == user.org_id)
    if sdr_profile_id:
        query = query.where(AgentLog.sdr_profile_id == sdr_profile_id)
    query = query.order_by(AgentLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "sdr_profile_id": log.sdr_profile_id,
            "lead_id": log.lead_id,
            "action": log.action,
            "channel": log.channel,
            "reasoning": log.reasoning,
            "result": log.result,
            "status": log.status,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/leads")
async def get_all_lead_states(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
):
    query = select(LeadState).where(LeadState.org_id == user.org_id)
    if sdr_profile_id:
        query = query.where(LeadState.sdr_profile_id == sdr_profile_id)
    query = query.order_by(LeadState.updated_at.desc())
    result = await db.execute(query)
    states = result.scalars().all()
    leads_by_id = {}
    lead_ids = [s.lead_id for s in states]
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        for lead in leads_result.scalars().all():
            leads_by_id[lead.id] = lead

    return [
        {
            "lead_id": s.lead_id,
            "sdr_profile_id": s.sdr_profile_id,
            "lead_name": f"{leads_by_id.get(s.lead_id, Lead()).first_name or ''} {leads_by_id.get(s.lead_id, Lead()).last_name or ''}".strip(),
            "lead_email": leads_by_id.get(s.lead_id, Lead()).email or "",
            "lead_company": leads_by_id.get(s.lead_id, Lead()).company or "",
            "lead_source": leads_by_id.get(s.lead_id, Lead()).source or "",
            "state": s.state,
            "is_paused": s.is_paused,
            "contact_count": s.contact_count or 0,
            "channels_used": list(s.channels_used) if s.channels_used else [],
            "last_contacted_at": s.last_contacted_at.isoformat() if s.last_contacted_at else None,
        }
        for s in states
    ]


@router.get("/rate-limits")
async def get_rate_limits(user: User = Depends(get_current_user)):
    from app.services.sdr.rate_limiter import rate_limiter
    return rate_limiter.get_usage(user.org_id)


@router.post("/rate-limits/reset")
async def reset_rate_limits(user: User = Depends(get_current_user)):
    from app.services.sdr.rate_limiter import rate_limiter
    rate_limiter.reset_org(user.org_id)
    return {"status": "reset"}


@router.post("/leads/{lead_id}/pause")
async def pause_lead(lead_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id, LeadState.lead_id == lead_id))
    ls = result.scalar_one_or_none()
    if not ls:
        raise HTTPException(status_code=404, detail="Lead state not found")
    ls.is_paused = True
    await db.flush()
    return {"status": "paused"}


@router.post("/leads/{lead_id}/resume")
async def resume_lead(lead_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id, LeadState.lead_id == lead_id))
    ls = result.scalar_one_or_none()
    if not ls:
        raise HTTPException(status_code=404, detail="Lead state not found")
    ls.is_paused = False
    await db.flush()
    return {"status": "resumed"}


@router.post("/leads/{lead_id}/stop")
async def stop_lead(lead_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id, LeadState.lead_id == lead_id))
    ls = result.scalar_one_or_none()
    if not ls:
        raise HTTPException(status_code=404, detail="Lead state not found")
    ls.state = "archived"
    ls.is_paused = False
    await db.flush()
    return {"status": "stopped"}
