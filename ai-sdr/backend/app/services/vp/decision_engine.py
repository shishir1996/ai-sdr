import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.vp_sales import VPSalesProfile, ResearchAgent, ResearchResult, VPActionLog
from app.models.agent import SDRProfile, LeadState
from app.models.lead import Lead
from app.services.ai.provider import generate_text
from app.services.lead_sources.service import get_enabled_sources, is_source_enabled

logger = logging.getLogger(__name__)


async def get_vp_decisions(db: AsyncSession, org_id: str, vp_id: str) -> list[dict]:
    result = await db.execute(
        select(VPActionLog)
        .where(VPActionLog.org_id == org_id, VPActionLog.vp_id == vp_id)
        .order_by(VPActionLog.created_at.desc())
        .limit(20)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action_type": log.action_type,
            "reasoning": log.reasoning,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


async def assess_lead_situation(db: AsyncSession, org_id: str, vp: VPSalesProfile) -> dict:
    lead_count = await db.scalar(
        select(func.count(Lead.id)).where(Lead.org_id == org_id)
    )
    research_count = await db.scalar(
        select(func.count(ResearchResult.id)).where(
            ResearchResult.org_id == org_id,
            ResearchResult.converted_to_lead == False,
        )
    )
    sdr_count = await db.scalar(
        select(func.count(SDRProfile.id)).where(
            SDRProfile.org_id == org_id,
            SDRProfile.deleted_at.is_(None),
        )
    )
    active_sdrs = await db.scalar(
        select(func.count(SDRProfile.id)).where(
            SDRProfile.org_id == org_id,
            SDRProfile.is_active == True,
            SDRProfile.deleted_at.is_(None),
        )
    )
    enabled = await get_enabled_sources(db, org_id)

    return {
        "total_leads": lead_count or 0,
        "unconverted_research": research_count or 0,
        "total_sdrs": sdr_count or 0,
        "active_sdrs": active_sdrs or 0,
        "enabled_sources": enabled,
        "has_product_info": bool(vp.product_name or vp.product_description or vp.service_description),
        "has_target_country": bool(vp.target_country),
        "has_icp": bool(vp.icp_description),
    }


async def decide_next_action(db: AsyncSession, org_id: str, vp: VPSalesProfile) -> dict:
    situation = await assess_lead_situation(db, org_id, vp)
    prompt = (
        f"You are a VP of Sales for a company. Assess the current situation and decide the next action.\n\n"
        f"Current situation:\n"
        f"- Total leads in CRM: {situation['total_leads']}\n"
        f"- Unconverted research findings: {situation['unconverted_research']}\n"
        f"- Total SDRs: {situation['total_sdrs']}\n"
        f"- Active SDRs: {situation['active_sdrs']}\n"
        f"- Enabled lead sources: {situation['enabled_sources']}\n"
        f"- Has product info: {situation['has_product_info']}\n"
        f"- Has target country: {situation['has_target_country']}\n"
        f"- Has ICP defined: {situation['has_icp']}\n\n"
        f"Possible actions:\n"
        f"1. create_research_agent - if leads are low and no research agents exist\n"
        f"2. convert_research_to_leads - if unconverted research exists\n"
        f"3. create_sdr - if enough leads exist and SDRs are needed\n"
        f"4. assign_campaign - if SDRs have no campaigns\n"
        f"5. monitor - if everything is running\n\n"
        f"Return a JSON object with:\n"
        f"- action: the selected action\n"
        f"- reasoning: detailed explanation of why this action\n"
        f"- suggested_queries: if action is create_research_agent, suggest 3 search queries\n"
        f"- sdr_recommendation: if action is create_sdr, suggest name and focus\n"
        f"Only return valid JSON."
    )
    try:
        result = await generate_text("", prompt)
        import json
        decision = json.loads(result.strip())
        return decision
    except Exception as e:
        logger.warning("VP decision AI failed: %s", e)
        return {"action": "monitor", "reasoning": "AI decision engine unavailable"}


async def log_vp_action(
    db: AsyncSession,
    org_id: str,
    vp_id: str,
    action_type: str,
    reasoning: str,
    details: Optional[dict] = None,
):
    log = VPActionLog(
        org_id=org_id,
        vp_id=vp_id,
        action_type=action_type,
        reasoning=reasoning,
        details=details or {},
    )
    db.add(log)
    await db.flush()


async def get_vp_dashboard(db: AsyncSession, org_id: str, vp_id: str) -> dict:
    agents = await db.execute(
        select(ResearchAgent).where(
            ResearchAgent.org_id == org_id,
            ResearchAgent.vp_id == vp_id,
        )
    )
    all_agents = list(agents.scalars().all())

    total_research_leads = sum(a.leads_discovered or 0 for a in all_agents)

    sdr_result = await db.execute(
        select(SDRProfile).where(
            SDRProfile.org_id == org_id,
            SDRProfile.deleted_at.is_(None),
        )
    )
    all_sdrs = list(sdr_result.scalars().all())
    active_sdrs = [s for s in all_sdrs if s.is_active]

    campaign_result = await db.execute(
        select(func.count()).select_from(__import__("app.models.campaign", fromlist=["Campaign"]).Campaign)
        .where(
            __import__("app.models.campaign", fromlist=["Campaign"]).Campaign.org_id == org_id,
            __import__("app.models.campaign", fromlist=["Campaign"]).Campaign.status == "active",
        )
    )
    active_campaigns = campaign_result.scalar() or 0

    meetings_result = await db.execute(
        select(func.count()).select_from(LeadState)
        .where(
            LeadState.org_id == org_id,
            LeadState.state == "meeting_scheduled",
        )
    )
    meetings_generated = meetings_result.scalar() or 0

    decisions = await get_vp_decisions(db, org_id, vp_id)

    return {
        "active_agents": len([a for a in all_agents if a.status == "running"]),
        "total_agents": len(all_agents),
        "leads_collected": total_research_leads,
        "unconverted_research": await db.scalar(
            select(func.count(ResearchResult.id)).where(
                ResearchResult.org_id == org_id,
                ResearchResult.converted_to_lead == False,
            )
        ) or 0,
        "sdrs_created": len(all_sdrs),
        "active_sdrs": len(active_sdrs),
        "campaigns_running": active_campaigns,
        "meetings_generated": meetings_generated,
        "sources_used": await get_enabled_sources(db, org_id),
        "recent_decisions": decisions,
    }
