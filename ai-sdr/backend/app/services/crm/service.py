import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.lead import Lead
from app.models.deal import Deal, DealStage, Pipeline
from app.models.campaign import Campaign
from app.models.agent import LeadState

logger = logging.getLogger(__name__)


async def get_crm_summary(db: AsyncSession, org_id: str) -> dict:
    total_leads = await db.scalar(
        select(func.count(Lead.id)).where(Lead.org_id == org_id)
    ) or 0
    total_deals = await db.scalar(
        select(func.count(Deal.id)).where(Deal.org_id == org_id)
    ) or 0
    total_campaigns = await db.scalar(
        select(func.count(Campaign.id)).where(Campaign.org_id == org_id)
    ) or 0

    leads_by_status = await db.execute(
        select(Lead.status, func.count(Lead.id))
        .where(Lead.org_id == org_id)
        .group_by(Lead.status)
    )

    leads_by_source = await db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.org_id == org_id)
        .group_by(Lead.source)
    )

    return {
        "total_leads": total_leads,
        "total_deals": total_deals,
        "total_campaigns": total_campaigns,
        "leads_by_status": dict(leads_by_status.fetchall()),
        "leads_by_source": dict(leads_by_source.fetchall()),
    }


async def get_lead_pipeline(db: AsyncSession, org_id: str, limit: int = 50) -> list[dict]:
    result = await db.execute(
        select(Lead, LeadState)
        .outerjoin(LeadState, LeadState.lead_id == Lead.id)
        .where(Lead.org_id == org_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "lead_id": lead.id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company": lead.company,
            "email": lead.email,
            "title": lead.title,
            "industry": lead.industry,
            "source": lead.source,
            "status": lead.status,
            "score": lead.score,
            "state": state.state if state else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        }
        for lead, state in rows
    ]


async def get_recent_activities(db: AsyncSession, org_id: str, limit: int = 20) -> list[dict]:
    from app.models.agent_activity import AgentActivity
    result = await db.execute(
        select(AgentActivity)
        .where(AgentActivity.org_id == org_id)
        .order_by(AgentActivity.created_at.desc())
        .limit(limit)
    )
    activities = result.scalars().all()
    return [
        {
            "id": a.id,
            "stage": a.stage,
            "status": a.status,
            "summary": a.summary,
            "reasoning": a.reasoning,
            "channel": a.channel,
            "sdr_profile_id": a.sdr_profile_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]
