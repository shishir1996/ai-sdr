from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.models.campaign import Campaign, CampaignStep, EmailMessage, CallLog
from app.models.deal import Deal, DealStage
from app.models.agent import AgentLog, LeadState
from app.utils.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.org_id
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Lead counts
    total_leads = await db.scalar(select(func.count(Lead.id)).where(Lead.org_id == org_id))
    leads_today = await db.scalar(
        select(func.count(Lead.id)).where(Lead.org_id == org_id, Lead.created_at >= today_start)
    )

    # Lead qualification stages
    lead_events_result = await db.execute(
        select(LeadState.state, func.count(LeadState.id))
        .where(LeadState.org_id == org_id)
        .group_by(LeadState.state)
    )
    lead_stages = {row[0]: row[1] for row in lead_events_result}

    # Email stats
    total_emails = await db.scalar(select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id))
    emails_sent = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.status == "sent")
    )
    emails_opened = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.opened_at.isnot(None))
    )
    emails_replied = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.replied_at.isnot(None))
    )
    emails_bounced = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.bounced_at.isnot(None))
    )
    emails_clicked = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.clicked_at.isnot(None))
    )

    sent = emails_sent or 1
    open_rate = round((emails_opened or 0) / sent * 100, 1)
    reply_rate = round((emails_replied or 0) / sent * 100, 1)
    bounce_rate = round((emails_bounced or 0) / sent * 100, 1)
    click_rate = round((emails_clicked or 0) / sent * 100, 1)

    # Email timeline (last 7 days)
    seven_days_ago = now - timedelta(days=7)
    daily_emails_result = await db.execute(
        select(
            func.date(EmailMessage.sent_at),
            func.count(EmailMessage.id),
            func.count(EmailMessage.opened_at),
            func.count(EmailMessage.replied_at),
        )
        .where(EmailMessage.org_id == org_id, EmailMessage.sent_at >= seven_days_ago)
        .group_by(func.date(EmailMessage.sent_at))
        .order_by(func.date(EmailMessage.sent_at))
    )
    email_timeline = [
        {"date": str(row[0]), "sent": row[1], "opened": row[2], "replied": row[3]}
        for row in daily_emails_result
    ]

    # Call stats
    total_calls = await db.scalar(select(func.count(CallLog.id)).where(CallLog.org_id == org_id))
    calls_made = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.org_id == org_id, CallLog.status == "completed")
    )
    calls_connected = await db.scalar(
        select(func.count(CallLog.id)).where(
            CallLog.org_id == org_id, CallLog.status == "completed", CallLog.outcome.isnot(None)
        )
    )
    avg_call_duration = await db.scalar(
        select(func.avg(CallLog.duration_seconds)).where(
            CallLog.org_id == org_id, CallLog.duration_seconds.isnot(None)
        )
    )

    # Call outcomes
    call_outcomes_result = await db.execute(
        select(CallLog.outcome, func.count(CallLog.id))
        .where(CallLog.org_id == org_id, CallLog.outcome.isnot(None))
        .group_by(CallLog.outcome)
    )
    call_outcomes = {row[0]: row[1] for row in call_outcomes_result}

    # Deal stats
    total_deals = await db.scalar(select(func.count(Deal.id)).where(Deal.org_id == org_id))
    won_deals = await db.scalar(
        select(func.count(Deal.id)).where(Deal.org_id == org_id, Deal.status == "won")
    )
    won_deals_value = await db.scalar(
        select(func.coalesce(func.sum(Deal.value), 0)).where(Deal.org_id == org_id, Deal.status == "won")
    )
    deals_by_source_result = await db.execute(
        select(Deal.source, func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0))
        .where(Deal.org_id == org_id, Deal.status == "won")
        .group_by(Deal.source)
    )
    deals_by_source = [
        {"source": row[0] or "unknown", "count": row[1], "value": float(row[2])}
        for row in deals_by_source_result
    ]

    # Campaign stats
    total_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.org_id == org_id))
    active_campaigns = await db.scalar(
        select(func.count(Campaign.id)).where(Campaign.org_id == org_id, Campaign.status == "active")
    )
    campaign_result = await db.execute(
        select(Campaign.id, Campaign.name, Campaign.status, Campaign.created_at)
        .where(Campaign.org_id == org_id)
        .order_by(Campaign.created_at.desc())
        .limit(10)
    )
    campaigns_list = [
        {
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
        }
        for row in campaign_result
    ]

    # SDR activity
    sdr_actions_result = await db.execute(
        select(AgentLog.action, func.count(AgentLog.id))
        .where(AgentLog.org_id == org_id)
        .group_by(AgentLog.action)
    )
    sdr_actions = {row[0]: row[1] for row in sdr_actions_result}

    sdr_actions_today = await db.scalar(
        select(func.count(AgentLog.id)).where(AgentLog.org_id == org_id, AgentLog.created_at >= today_start)
    )

    sdr_actions_7d = await db.scalar(
        select(func.count(AgentLog.id)).where(AgentLog.org_id == org_id, AgentLog.created_at >= seven_days_ago)
    )

    # Positive reply leads (leads that replied with positive intent)
    positive_replies = await db.scalar(
        select(func.count(EmailMessage.id)).where(
            EmailMessage.org_id == org_id,
            EmailMessage.replied_at.isnot(None),
            EmailMessage.status == "sent",
        )
    )

    # Leads with meetings booked
    meetings_booked = lead_stages.get("meeting_scheduled", 0)

    # Forecast: projected deals (open deals * probability)
    forecast_result = await db.execute(
        select(
            func.coalesce(func.sum(Deal.value * DealStage.probability / 100.0), 0)
        )
        .select_from(Deal)
        .join(DealStage, Deal.stage_id == DealStage.id)
        .where(Deal.org_id == org_id, Deal.status == "open")
    )
    forecast_value = float(next(forecast_result)[0] or 0)

    return {
        "total_leads": total_leads or 0,
        "leads_today": leads_today or 0,
        "lead_stages": {k: v for k, v in lead_stages.items()},
        "emails_sent": emails_sent or 0,
        "emails_opened": emails_opened or 0,
        "emails_replied": emails_replied or 0,
        "emails_bounced": emails_bounced or 0,
        "emails_clicked": emails_clicked or 0,
        "open_rate": open_rate,
        "reply_rate": reply_rate,
        "bounce_rate": bounce_rate,
        "click_rate": click_rate,
        "email_timeline": email_timeline,
        "total_calls": total_calls or 0,
        "calls_made": calls_made or 0,
        "calls_connected": calls_connected or 0,
        "avg_call_duration": round(float(avg_call_duration or 0), 1),
        "call_outcomes": call_outcomes,
        "total_campaigns": total_campaigns or 0,
        "active_campaigns": active_campaigns or 0,
        "campaigns": campaigns_list,
        "total_deals": total_deals or 0,
        "won_deals": won_deals or 0,
        "won_deals_value": float(won_deals_value or 0),
        "deals_by_source": deals_by_source,
        "sdr_actions": sdr_actions,
        "sdr_actions_today": sdr_actions_today or 0,
        "sdr_actions_7d": sdr_actions_7d or 0,
        "positive_replies": positive_replies or 0,
        "meetings_booked": meetings_booked,
        "forecast_value": forecast_value,
    }


@router.get("/leads-by-source")
async def leads_by_source(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.org_id == user.org_id)
        .group_by(Lead.source)
    )
    return [{"source": row[0] or "unknown", "count": row[1]} for row in result]


@router.get("/deals-by-stage")
async def deals_by_stage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DealStage.name, func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0))
        .select_from(Deal)
        .join(DealStage, Deal.stage_id == DealStage.id)
        .where(Deal.org_id == user.org_id)
        .group_by(DealStage.name)
    )
    return [{"stage": row[0], "count": row[1], "value": float(row[2])} for row in result]


@router.get("/email-stats")
async def email_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.org_id
    total = await db.scalar(select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id))
    sent = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.status == "sent")
    )
    opened = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.opened_at.isnot(None))
    )
    replied = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.replied_at.isnot(None))
    )
    bounced = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.bounced_at.isnot(None))
    )
    clicked = await db.scalar(
        select(func.count(EmailMessage.id)).where(EmailMessage.org_id == org_id, EmailMessage.clicked_at.isnot(None))
    )

    sent_count = sent or 1
    return {
        "total": total or 0,
        "sent": sent or 0,
        "opened": opened or 0,
        "replied": replied or 0,
        "bounced": bounced or 0,
        "clicked": clicked or 0,
        "open_rate": round((opened or 0) / sent_count * 100, 1),
        "reply_rate": round((replied or 0) / sent_count * 100, 1),
        "bounce_rate": round((bounced or 0) / sent_count * 100, 1),
        "click_rate": round((clicked or 0) / sent_count * 100, 1),
    }


@router.get("/email-details")
async def email_details(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 100,
):
    result = await db.execute(
        select(EmailMessage)
        .where(EmailMessage.org_id == user.org_id)
        .order_by(EmailMessage.created_at.desc())
        .limit(limit)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "to_email": m.to_email,
            "subject": m.subject,
            "status": m.status,
            "opened_at": m.opened_at.isoformat() if m.opened_at else None,
            "replied_at": m.replied_at.isoformat() if m.replied_at else None,
            "clicked_at": m.clicked_at.isoformat() if m.clicked_at else None,
            "bounced_at": m.bounced_at.isoformat() if m.bounced_at else None,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "lead_id": m.lead_id,
        }
        for m in msgs
    ]


@router.get("/call-details")
async def call_details(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 100,
):
    result = await db.execute(
        select(CallLog)
        .where(CallLog.org_id == user.org_id)
        .order_by(CallLog.created_at.desc())
        .limit(limit)
    )
    calls = result.scalars().all()
    return [
        {
            "id": c.id,
            "lead_id": c.lead_id,
            "status": c.status,
            "duration_seconds": c.duration_seconds,
            "outcome": c.outcome,
            "called_at": c.called_at.isoformat() if c.called_at else None,
            "recording_url": c.recording_url,
        }
        for c in calls
    ]


@router.get("/forecast")
async def forecast(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.org_id
    now = datetime.now(timezone.utc)

    # Monthly breakdown
    six_months_ago = now - timedelta(days=180)

    # Won deals by month
    monthly_won = await db.execute(
        select(
            func.to_char(Deal.won_at, 'YYYY-MM'),
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.value), 0),
        )
        .where(Deal.org_id == org_id, Deal.status == "won", Deal.won_at >= six_months_ago)
        .group_by(func.to_char(Deal.won_at, 'YYYY-MM'))
        .order_by(func.to_char(Deal.won_at, 'YYYY-MM'))
    )

    # Open deals pipeline
    pipeline_result = await db.execute(
        select(
            DealStage.name,
            DealStage.probability,
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.value), 0),
        )
        .select_from(Deal)
        .join(DealStage, Deal.stage_id == DealStage.id)
        .where(Deal.org_id == org_id, Deal.status == "open")
        .group_by(DealStage.name, DealStage.probability)
    )

    total_forecast = 0
    pipeline = []
    for row in pipeline_result:
        weighted = float(row[3]) * row[1] / 100.0
        total_forecast += weighted
        pipeline.append({
            "stage": row[0],
            "probability": row[1],
            "count": row[2],
            "value": float(row[3]),
            "weighted_value": round(weighted, 2),
        })

    return {
        "monthly_won": [
            {"month": row[0], "count": row[1], "value": float(row[2])}
            for row in monthly_won
        ],
        "pipeline": pipeline,
        "total_forecast": round(total_forecast, 2),
    }


@router.get("/lead-qualification")
async def lead_qualification(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.org_id
    result = await db.execute(
        select(LeadState)
        .where(LeadState.org_id == org_id)
        .order_by(LeadState.updated_at.desc())
        .limit(50)
    )
    states = result.scalars().all()

    lead_ids = [s.lead_id for s in states]
    leads = {}
    if lead_ids:
        leads_result = await db.execute(
            select(Lead).where(Lead.id.in_(lead_ids))
        )
        for l in leads_result.scalars().all():
            leads[l.id] = l

    return [
        {
            "lead_id": s.lead_id,
            "name": f"{leads.get(s.lead_id, Lead()).first_name or ''} {leads.get(s.lead_id, Lead()).last_name or ''}".strip(),
            "email": leads.get(s.lead_id, Lead()).email or "",
            "title": leads.get(s.lead_id, Lead()).title or "",
            "company": leads.get(s.lead_id, Lead()).company or "",
            "source": leads.get(s.lead_id, Lead()).source or "",
            "state": s.state,
            "is_paused": s.is_paused,
            "contact_count": s.contact_count or 0,
            "channels_used": list(s.channels_used) if s.channels_used else [],
            "engagement_score": s.engagement_score or 0,
            "last_contacted_at": s.last_contacted_at.isoformat() if s.last_contacted_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in states
    ]
