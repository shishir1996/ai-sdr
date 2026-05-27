import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice import CallCampaign, CallQueue, CallRecord, VoiceAgent
from app.models.lead import Lead


async def create_campaign(
    db: AsyncSession,
    org_id: str,
    name: str,
    voice_agent_id: str = "",
    sdr_profile_id: str = "",
    **kwargs,
) -> CallCampaign:
    campaign = CallCampaign(
        org_id=org_id,
        name=name,
        voice_agent_id=voice_agent_id or None,
        sdr_profile_id=sdr_profile_id or None,
        **{k: v for k, v in kwargs.items() if hasattr(CallCampaign, k)},
    )
    db.add(campaign)
    await db.flush()
    return campaign


async def enqueue_leads(
    db: AsyncSession,
    org_id: str,
    campaign_id: str,
    lead_ids: list[str],
    voice_agent_id: str = "",
    max_retries: int = 2,
) -> list[CallQueue]:
    result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids), Lead.org_id == org_id))
    leads = result.scalars().all()
    queued = []
    for lead in leads:
        if not lead.phone:
            continue
        existing = await db.execute(
            select(CallQueue).where(
                CallQueue.org_id == org_id,
                CallQueue.lead_id == lead.id,
                CallQueue.campaign_id == campaign_id,
                CallQueue.status.in_(["pending", "queued"]),
            )
        )
        if existing.scalar_one_or_none():
            continue
        entry = CallQueue(
            org_id=org_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            voice_agent_id=voice_agent_id or None,
            phone_number=lead.phone,
            max_retries=max_retries,
            idempotency_key=str(uuid.uuid4()),
        )
        db.add(entry)
        queued.append(entry)
    await db.flush()
    return queued


async def process_queue(
    db: AsyncSession,
    org_id: str,
    api_key: str,
    batch_size: int = 5,
) -> list[dict]:
    from app.services.voice.vapi_service import start_call

    result = await db.execute(
        select(CallQueue)
        .where(
            CallQueue.org_id == org_id,
            CallQueue.status == "pending",
            and_(
                CallQueue.scheduled_at.is_(None) | (CallQueue.scheduled_at <= datetime.now(timezone.utc))
            ),
        )
        .order_by(CallQueue.priority.desc(), CallQueue.created_at.asc())
        .limit(batch_size)
    )
    queue_items = result.scalars().all()
    if not queue_items:
        return []

    campaign_ids = set(q.campaign_id for q in queue_items if q.campaign_id)
    campaigns = {}
    if campaign_ids:
        camp_result = await db.execute(
            select(CallCampaign).where(CallCampaign.id.in_(list(campaign_ids)))
        )
        for c in camp_result.scalars().all():
            campaigns[c.id] = c

    agent_ids = set(q.voice_agent_id for q in queue_items if q.voice_agent_id)
    agents = {}
    if agent_ids:
        agent_result = await db.execute(
            select(VoiceAgent).where(VoiceAgent.id.in_(list(agent_ids)))
        )
        for a in agent_result.scalars().all():
            agents[a.id] = a

    results = []
    for item in queue_items:
        agent = agents.get(item.voice_agent_id) if item.voice_agent_id else None
        if not agent or not agent.vapi_assistant_id:
            item.status = "failed"
            item.last_error = "No voice agent configured"
            results.append({"queue_id": item.id, "status": "failed", "error": "No voice agent"})
            continue

        lead_result = await db.execute(select(Lead).where(Lead.id == item.lead_id))
        lead = lead_result.scalar_one_or_none()

        call_result = await start_call(
            api_key=api_key,
            phone_number=item.phone_number,
            assistant_id=agent.vapi_assistant_id,
            customer_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() if lead else "",
            customer_data={
                "name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                "company": lead.company or "",
            } if lead else {},
            idempotency_key=item.idempotency_key,
        )

        if "error" in call_result:
            item.retry_count += 1
            item.last_error = call_result.get("error", "")
            if item.retry_count >= item.max_retries:
                item.status = "failed"
            results.append({"queue_id": item.id, "status": "failed", "error": call_result.get("error")})
            await db.flush()
            continue

        call_id = call_result.get("callId") or call_result.get("id", "")
        item.status = "processing"
        record = CallRecord(
            org_id=org_id,
            lead_id=item.lead_id,
            campaign_id=item.campaign_id,
            voice_agent_id=item.voice_agent_id,
            vapi_call_id=call_id,
            phone_number=item.phone_number,
            status="initiated",
            called_at=datetime.now(timezone.utc),
        )
        db.add(record)
        results.append({"queue_id": item.id, "call_id": call_id, "status": "initiated"})
        await db.flush()

    return results


async def get_campaign_stats(db: AsyncSession, org_id: str, campaign_id: str) -> dict:
    total = await db.execute(
        select(CallRecord).where(CallRecord.org_id == org_id, CallRecord.campaign_id == campaign_id)
    )
    records = total.scalars().all()
    total_calls = len(records)
    connected = sum(1 for r in records if r.status == "completed")
    failed = sum(1 for r in records if r.status in ("failed", "error"))
    voicemail = sum(1 for r in records if r.voicemail_detected)
    positive = sum(1 for r in records if r.outcome in ("interested", "meeting_booked", "qualified"))
    total_cost = sum(r.cost or 0 for r in records)
    return {
        "total_calls": total_calls,
        "connected": connected,
        "failed": failed,
        "voicemail": voicemail,
        "positive_outcomes": positive,
        "total_cost": round(total_cost, 4),
        "connect_rate": round(connected / total_calls * 100, 1) if total_calls else 0,
    }
