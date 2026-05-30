import json
import logging
import itertools
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

_timestamp_counter = itertools.count(start=1)

from app.models.agent_activity import (
    AgentActivity, SDRReasoningLog, CampaignEvent,
    LeadTimeline, SequenceExecutionLog, SDRStatus,
    ACTIVITY_STAGES, SDR_STATUSES,
)
from app.models.lead import Lead

logger = logging.getLogger(__name__)


def _now():
    offset = next(_timestamp_counter)
    return datetime.now(timezone.utc) + timedelta(microseconds=offset)


async def log_activity(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: str,
    stage: str,
    status: str = "completed",
    *,
    lead_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    summary: Optional[str] = None,
    reasoning: Optional[str] = None,
    details: Optional[dict] = None,
    channel: Optional[str] = None,
    next_planned_action: Optional[str] = None,
    confidence_score: Optional[int] = None,
    is_expandable: bool = False,
) -> AgentActivity:
    activity = AgentActivity(
        org_id=org_id,
        sdr_profile_id=sdr_profile_id,
        lead_id=lead_id,
        campaign_id=campaign_id,
        stage=stage,
        status=status,
        summary=summary or "",
        reasoning=reasoning or "",
        details=details,
        channel=channel,
        next_planned_action=next_planned_action,
        confidence_score=confidence_score,
        is_expandable=is_expandable,
        created_at=_now(),
    )
    db.add(activity)
    await db.flush()
    return activity


async def log_reasoning(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: str,
    decision_type: str,
    *,
    lead_id: Optional[str] = None,
    human_readable_reasoning: Optional[str] = None,
    detailed_reasoning: Optional[dict] = None,
    ai_confidence_score: Optional[int] = None,
    alternatives_considered: Optional[list] = None,
    context_summary: Optional[str] = None,
    channel_selected: Optional[str] = None,
    timing_explanation: Optional[str] = None,
    personalization_strategy: Optional[str] = None,
    industry_context: Optional[str] = None,
    country_context: Optional[str] = None,
) -> SDRReasoningLog:
    log = SDRReasoningLog(
        org_id=org_id,
        sdr_profile_id=sdr_profile_id,
        lead_id=lead_id,
        decision_type=decision_type,
        human_readable_reasoning=human_readable_reasoning,
        detailed_reasoning=detailed_reasoning,
        ai_confidence_score=ai_confidence_score,
        alternatives_considered=alternatives_considered,
        context_summary=context_summary,
        channel_selected=channel_selected,
        timing_explanation=timing_explanation,
        personalization_strategy=personalization_strategy,
        industry_context=industry_context,
        country_context=country_context,
    )
    db.add(log)
    await db.flush()
    return log


async def log_campaign_event(
    db: AsyncSession,
    org_id: str,
    campaign_id: str,
    event_type: str,
    *,
    sdr_profile_id: Optional[str] = None,
    summary: Optional[str] = None,
    reasoning: Optional[str] = None,
    details: Optional[dict] = None,
    progress_before: Optional[int] = None,
    progress_after: Optional[int] = None,
) -> CampaignEvent:
    event = CampaignEvent(
        org_id=org_id,
        campaign_id=campaign_id,
        sdr_profile_id=sdr_profile_id,
        event_type=event_type,
        summary=summary or "",
        reasoning=reasoning or "",
        details=details,
        progress_before=progress_before,
        progress_after=progress_after,
    )
    db.add(event)
    await db.flush()
    return event


async def log_lead_timeline(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    event_type: str,
    *,
    sdr_profile_id: Optional[str] = None,
    summary: Optional[str] = None,
    reasoning: Optional[str] = None,
    message_preview: Optional[str] = None,
    channel: Optional[str] = None,
    response_received: Optional[str] = None,
    sdr_status_before: Optional[str] = None,
    sdr_status_after: Optional[str] = None,
) -> LeadTimeline:
    entry = LeadTimeline(
        org_id=org_id,
        lead_id=lead_id,
        sdr_profile_id=sdr_profile_id,
        event_type=event_type,
        summary=summary or "",
        reasoning=reasoning or "",
        message_preview=message_preview,
        channel=channel,
        response_received=response_received,
        sdr_status_before=sdr_status_before,
        sdr_status_after=sdr_status_after,
    )
    db.add(entry)
    await db.flush()
    return entry


async def log_sequence_execution(
    db: AsyncSession,
    org_id: str,
    campaign_id: str,
    step_order: int,
    channel: str,
    delay_days: int = 0,
    *,
    lead_id: Optional[str] = None,
    sdr_profile_id: Optional[str] = None,
    status: str = "pending",
    result: Optional[str] = None,
    reasoning: Optional[str] = None,
) -> SequenceExecutionLog:
    log = SequenceExecutionLog(
        org_id=org_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        sdr_profile_id=sdr_profile_id,
        step_order=step_order,
        channel=channel,
        delay_days=delay_days,
        status=status,
        executed_at=_now() if status == "completed" else None,
        result=result,
        reasoning=reasoning,
    )
    db.add(log)
    await db.flush()
    return log


async def update_sdr_status(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: str,
    status: str,
    *,
    current_action: Optional[str] = None,
    current_lead_id: Optional[str] = None,
    current_campaign_id: Optional[str] = None,
    reasoning_summary: Optional[str] = None,
    next_planned_action: Optional[str] = None,
    increment_leads: bool = False,
    increment_campaigns: bool = False,
    increment_emails: bool = False,
    increment_linkedin: bool = False,
    increment_replies: bool = False,
    increment_meetings: bool = False,
) -> SDRStatus:
    result = await db.execute(
        select(SDRStatus).where(
            SDRStatus.org_id == org_id,
            SDRStatus.sdr_profile_id == sdr_profile_id,
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        s = SDRStatus(
            org_id=org_id,
            sdr_profile_id=sdr_profile_id,
            current_status=status,
        )
        db.add(s)

    s.current_status = status
    s.heartbeat_at = _now()
    s.last_active_at = _now()

    if current_action is not None:
        s.current_action = current_action
    if current_lead_id is not None:
        s.current_lead_id = current_lead_id
    if current_campaign_id is not None:
        s.current_campaign_id = current_campaign_id
    if reasoning_summary is not None:
        s.reasoning_summary = reasoning_summary
    if next_planned_action is not None:
        s.next_planned_action = next_planned_action

    if increment_leads:
        s.leads_processed = (s.leads_processed or 0) + 1
    if increment_campaigns:
        s.campaigns_created = (s.campaigns_created or 0) + 1
    if increment_emails:
        s.emails_drafted = (s.emails_drafted or 0) + 1
    if increment_linkedin:
        s.linkedin_invites_sent = (s.linkedin_invites_sent or 0) + 1
    if increment_replies:
        s.replies_detected = (s.replies_detected or 0) + 1
    if increment_meetings:
        s.meetings_booked = (s.meetings_booked or 0) + 1

    await db.flush()
    return s


async def get_activity_feed(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = select(AgentActivity).where(AgentActivity.org_id == org_id)
    if sdr_profile_id:
        query = query.where(AgentActivity.sdr_profile_id == sdr_profile_id)
    if stage:
        query = query.where(AgentActivity.stage == stage)
    query = query.order_by(AgentActivity.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    activities = result.scalars().all()

    lead_ids = [a.lead_id for a in activities if a.lead_id]
    leads = {}
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        for lead in leads_result.scalars().all():
            leads[lead.id] = lead

    return [
        {
            "id": a.id,
            "sdr_profile_id": a.sdr_profile_id,
            "lead_id": a.lead_id,
            "campaign_id": a.campaign_id,
            "stage": a.stage,
            "status": a.status,
            "summary": a.summary,
            "reasoning": a.reasoning,
            "details": a.details,
            "channel": a.channel,
            "next_planned_action": a.next_planned_action,
            "confidence_score": a.confidence_score,
            "is_expandable": a.is_expandable,
            "lead_name": (
                f"{leads[a.lead_id].first_name or ''} {leads[a.lead_id].last_name or ''}".strip()
                if a.lead_id and a.lead_id in leads else None
            ),
            "lead_email": leads[a.lead_id].email if a.lead_id and a.lead_id in leads else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]


async def get_sdr_status_info(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: str,
) -> Optional[dict]:
    result = await db.execute(
        select(SDRStatus).where(
            SDRStatus.org_id == org_id,
            SDRStatus.sdr_profile_id == sdr_profile_id,
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        return None
    return {
        "current_status": s.current_status,
        "current_action": s.current_action,
        "current_lead_id": s.current_lead_id,
        "current_campaign_id": s.current_campaign_id,
        "reasoning_summary": s.reasoning_summary,
        "next_planned_action": s.next_planned_action,
        "heartbeat_at": s.heartbeat_at.isoformat() if s.heartbeat_at else None,
        "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
        "leads_processed": s.leads_processed or 0,
        "campaigns_created": s.campaigns_created or 0,
        "emails_drafted": s.emails_drafted or 0,
        "linkedin_invites_sent": s.linkedin_invites_sent or 0,
        "replies_detected": s.replies_detected or 0,
        "meetings_booked": s.meetings_booked or 0,
    }


async def get_lead_timeline(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    limit: int = 50,
) -> list[dict]:
    result = await db.execute(
        select(LeadTimeline).where(
            LeadTimeline.org_id == org_id,
            LeadTimeline.lead_id == lead_id,
        ).order_by(LeadTimeline.created_at.desc()).limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "summary": e.summary,
            "reasoning": e.reasoning,
            "message_preview": e.message_preview,
            "channel": e.channel,
            "response_received": e.response_received,
            "sdr_status_before": e.sdr_status_before,
            "sdr_status_after": e.sdr_status_after,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


async def get_reasoning_logs(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    query = select(SDRReasoningLog).where(SDRReasoningLog.org_id == org_id)
    if sdr_profile_id:
        query = query.where(SDRReasoningLog.sdr_profile_id == sdr_profile_id)
    if lead_id:
        query = query.where(SDRReasoningLog.lead_id == lead_id)
    query = query.order_by(SDRReasoningLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "sdr_profile_id": log.sdr_profile_id,
            "lead_id": log.lead_id,
            "decision_type": log.decision_type,
            "human_readable_reasoning": log.human_readable_reasoning,
            "detailed_reasoning": log.detailed_reasoning,
            "ai_confidence_score": log.ai_confidence_score,
            "alternatives_considered": log.alternatives_considered,
            "context_summary": log.context_summary,
            "channel_selected": log.channel_selected,
            "timing_explanation": log.timing_explanation,
            "personalization_strategy": log.personalization_strategy,
            "industry_context": log.industry_context,
            "country_context": log.country_context,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


async def get_activity_stages_summary(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: Optional[str] = None,
) -> list[dict]:
    query = select(
        AgentActivity.stage,
        func.count(AgentActivity.id).label("count"),
        func.max(AgentActivity.created_at).label("latest"),
    ).where(AgentActivity.org_id == org_id)
    if sdr_profile_id:
        query = query.where(AgentActivity.sdr_profile_id == sdr_profile_id)
    query = query.group_by(AgentActivity.stage).order_by(func.max(AgentActivity.created_at).desc())
    result = await db.execute(query)
    rows = result.fetchall()
    return [
        {"stage": row.stage, "count": row.count, "latest": row.latest.isoformat() if row.latest else None}
        for row in rows
    ]
