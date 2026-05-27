from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.models.voice import CallRecord, CallCampaign, VoiceAgent, CallQueue, CallAnalytics, AiSummary
from app.utils.auth import get_current_user, get_current_admin
from app.services.integrations.service import get_api_key
from app.services.voice.call_campaign_service import (
    create_campaign, enqueue_leads, process_queue, get_campaign_stats,
)

router = APIRouter(prefix="/calls", tags=["calls"])


# ============================================================
# Campaigns
# ============================================================

class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    voice_agent_id: str = ""
    max_concurrent_calls: int = 3
    max_calls_per_day: int = 50
    retry_on_no_answer: bool = True
    max_retries: int = 2
    voicemail_detection: bool = True
    business_hours_start: str = "09:00"
    business_hours_end: str = "18:00"


@router.get("/campaigns")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CallCampaign).where(CallCampaign.org_id == user.org_id).order_by(CallCampaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    output = []
    for c in campaigns:
        stats = await get_campaign_stats(db, user.org_id, c.id)
        output.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "status": c.status,
            "voice_agent_id": c.voice_agent_id,
            "max_concurrent_calls": c.max_concurrent_calls,
            "max_calls_per_day": c.max_calls_per_day,
            "business_hours_start": c.business_hours_start,
            "business_hours_end": c.business_hours_end,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            **stats,
        })
    return output


@router.post("/campaigns")
async def create_call_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    campaign = await create_campaign(
        db, user.org_id,
        name=body.name,
        description=body.description,
        voice_agent_id=body.voice_agent_id,
        max_concurrent_calls=body.max_concurrent_calls,
        max_calls_per_day=body.max_calls_per_day,
        retry_on_no_answer=body.retry_on_no_answer,
        max_retries=body.max_retries,
        voicemail_detection=body.voicemail_detection,
        business_hours_start=body.business_hours_start,
        business_hours_end=body.business_hours_end,
    )
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
    }


@router.post("/campaigns/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(CallCampaign).where(CallCampaign.id == campaign_id, CallCampaign.org_id == user.org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "active"
    await db.flush()
    return {"status": "launched"}


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(CallCampaign).where(CallCampaign.id == campaign_id, CallCampaign.org_id == user.org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "paused"
    await db.flush()
    return {"status": "paused"}


@router.post("/campaigns/{campaign_id}/enqueue")
async def enqueue_campaign_leads(
    campaign_id: str,
    lead_ids: list[str],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(CallCampaign).where(CallCampaign.id == campaign_id, CallCampaign.org_id == user.org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    queued = await enqueue_leads(
        db, user.org_id, campaign_id, lead_ids,
        voice_agent_id=campaign.voice_agent_id or "",
    )
    return {"enqueued": len(queued)}


# ============================================================
# Call Records
# ============================================================

@router.get("")
async def list_calls(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    campaign_id: Optional[str] = None,
    search: Optional[str] = None,
):
    conditions = [CallRecord.org_id == user.org_id]
    if status:
        conditions.append(CallRecord.status == status)
    if outcome:
        conditions.append(CallRecord.outcome == outcome)
    if campaign_id:
        conditions.append(CallRecord.campaign_id == campaign_id)
    if search:
        conditions.append(
            or_(
                CallRecord.phone_number.ilike(f"%{search}%"),
                CallRecord.vapi_call_id.ilike(f"%{search}%"),
            )
        )

    query = select(CallRecord).where(and_(*conditions)).order_by(CallRecord.created_at.desc())
    total_result = await db.execute(select(CallRecord).where(and_(*conditions)))
    total = len(total_result.scalars().all())
    result = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
    records = result.scalars().all()

    lead_ids = [r.lead_id for r in records if r.lead_id]
    leads = {}
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        for l in leads_result.scalars().all():
            leads[l.id] = l

    return {
        "items": [
            {
                "id": r.id,
                "vapi_call_id": r.vapi_call_id,
                "lead_id": r.lead_id,
                "lead_name": f"{leads.get(r.lead_id, Lead()).first_name or ''} {leads.get(r.lead_id, Lead()).last_name or ''}".strip() if r.lead_id else "",
                "lead_email": leads.get(r.lead_id, Lead()).email or "" if r.lead_id else "",
                "lead_company": leads.get(r.lead_id, Lead()).company or "" if r.lead_id else "",
                "phone_number": r.phone_number,
                "status": r.status,
                "duration_seconds": r.duration_seconds,
                "cost": r.cost,
                "outcome": r.outcome,
                "sentiment": r.sentiment,
                "lead_qualified": r.lead_qualified,
                "voicemail_detected": r.voicemail_detected,
                "recording_url": r.recording_url,
                "transcript": r.transcript,
                "ai_summary": r.ai_summary,
                "next_action": r.next_action,
                "error_message": r.error_message,
                "called_at": r.called_at.isoformat() if r.called_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/analytics")
async def call_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    records = await db.execute(
        select(CallRecord).where(
            CallRecord.org_id == user.org_id,
            CallRecord.created_at >= since,
        )
    )
    calls = records.scalars().all()
    total = len(calls)
    connected = sum(1 for c in calls if c.status == "completed")
    failed = sum(1 for c in calls if c.status in ("failed", "error"))
    voicemail = sum(1 for c in calls if c.voicemail_detected)
    no_answer = sum(1 for c in calls if c.status == "no-answer")
    positive = sum(1 for c in calls if c.outcome in ("interested", "meeting_booked", "qualified"))
    total_duration = sum(c.duration_seconds or 0 for c in calls)
    total_cost = sum(c.cost or 0 for c in calls)

    outcome_counts: dict[str, int] = {}
    for c in calls:
        if c.outcome:
            outcome_counts[c.outcome] = outcome_counts.get(c.outcome, 0) + 1

    daily = await db.execute(
        select(
            func.date(CallRecord.called_at),
            func.count(CallRecord.id),
            func.sum(CallRecord.duration_seconds),
        )
        .where(CallRecord.org_id == user.org_id, CallRecord.called_at >= since)
        .group_by(func.date(CallRecord.called_at))
        .order_by(func.date(CallRecord.called_at))
    )
    daily_stats = [
        {"date": str(row[0]), "count": row[1], "duration": row[2] or 0}
        for row in daily
    ]

    return {
        "total": total,
        "connected": connected,
        "failed": failed,
        "voicemail": voicemail,
        "no_answer": no_answer,
        "positive_outcomes": positive,
        "connect_rate": round(connected / total * 100, 1) if total else 0,
        "total_duration_minutes": round(total_duration / 60, 1),
        "total_cost": round(total_cost, 4),
        "avg_cost_per_call": round(total_cost / total, 4) if total else 0,
        "outcomes": outcome_counts,
        "daily_stats": daily_stats,
    }


@router.get("/queue")
async def queue_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CallQueue).where(CallQueue.org_id == user.org_id).order_by(CallQueue.created_at.desc()).limit(50)
    )
    items = result.scalars().all()
    lead_ids = [q.lead_id for q in items]
    leads = {}
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        for l in leads_result.scalars().all():
            leads[l.id] = l

    pending = sum(1 for q in items if q.status == "pending")
    processing = sum(1 for q in items if q.status == "processing")
    failed = sum(1 for q in items if q.status == "failed")

    return {
        "pending": pending,
        "processing": processing,
        "failed": failed,
        "items": [
            {
                "id": q.id,
                "lead_name": f"{leads.get(q.lead_id, Lead()).first_name or ''} {leads.get(q.lead_id, Lead()).last_name or ''}".strip() if q.lead_id else "",
                "phone": q.phone_number,
                "status": q.status,
                "retry_count": q.retry_count,
                "max_retries": q.max_retries,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in items[:20]
        ],
    }


@router.post("/queue/process")
async def process_call_queue(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
    batch_size: int = 5,
):
    vapi_key = await get_api_key(db, user.org_id, "vapi")
    if not vapi_key:
        raise HTTPException(status_code=400, detail="Vapi not configured")

    results = await process_queue(db, user.org_id, vapi_key, batch_size=batch_size)
    return {"processed": len(results), "results": results}


@router.get("/live")
async def live_calls(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CallRecord).where(
            CallRecord.org_id == user.org_id,
            CallRecord.status.in_(["initiated", "ringing", "in-progress", "queued"]),
        ).order_by(CallRecord.created_at.desc()).limit(20)
    )
    calls = result.scalars().all()
    return [
        {
            "id": c.id,
            "phone_number": c.phone_number,
            "status": c.status,
            "duration_seconds": c.duration_seconds or 0,
            "called_at": c.called_at.isoformat() if c.called_at else None,
        }
        for c in calls
    ]
