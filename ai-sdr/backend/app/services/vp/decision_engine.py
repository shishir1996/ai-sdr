import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.vp_sales import VPSalesProfile, ResearchAgent, ResearchResult, VPActionLog
from app.models.agent import SDRProfile
from app.models.lead import Lead
from app.services.ai.provider import generate_text
from app.services.lead_sources.service import get_enabled_sources
from app.services.research.agent_service import create_research_agent, execute_research, convert_to_lead

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
    agent_count = await db.scalar(
        select(func.count(ResearchAgent.id)).where(ResearchAgent.org_id == org_id)
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
        "total_agents": agent_count or 0,
        "total_sdrs": sdr_count or 0,
        "active_sdrs": active_sdrs or 0,
        "enabled_sources": enabled,
        "has_product_info": bool(vp.product_name or vp.product_description or vp.service_description),
        "has_target_country": bool(vp.target_country),
        "has_icp": bool(vp.icp_description),
        "outreach_active": bool(vp.outreach_active),
    }


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


async def _generate_queries(vp: VPSalesProfile) -> list[str]:
    country = vp.target_country or ""
    biz_types_str = vp.target_business_types or vp.icp_description or ""
    biz_types = [b.strip().lower() for b in biz_types_str.replace(",", "\n").split("\n") if b.strip()]
    if not biz_types:
        biz_types = ["restaurant", "salon", "small business"]

    product = vp.product_name or ""

    queries = []
    for bt in biz_types[:3]:
        if country:
            queries.append(f"{bt} owner {country} email contact")
            queries.append(f"{bt} {country} phone number directory")
            queries.append(f"{bt} {country} business listing contact info")
        else:
            queries.append(f"{bt} owner email address")
            queries.append(f"{bt} business directory phone")
            queries.append(f"{bt} owners list contact")

    if product:
        queries.append(f"{product} potential customers {country}".strip())

    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:6]


async def _create_auto_agent(db: AsyncSession, org_id: str, vp: VPSalesProfile, queries: list[str]) -> dict:
    agent = await create_research_agent(
        db=db, org_id=org_id, vp_id=vp.id,
        name=f"Auto-Agent - {vp.product_name or 'Prospecting'}",
        search_queries="\n".join(queries),
        target_industry=vp.icp_description or "",
        target_country=vp.target_country or "",
        target_audience=vp.target_audience or "",
        max_leads=100,
    )
    await log_vp_action(db, org_id, vp.id, "agent_created",
                        f"Created research agent '{agent.name}' with {len(queries)} business-owner queries",
                        {"queries": queries})
    leads_found = await execute_research(db, agent.id)
    await log_vp_action(db, org_id, vp.id, "research_completed",
                        f"Agent '{agent.name}' discovered {leads_found} leads across {len(queries)} queries",
                        {"leads_found": leads_found, "queries_count": len(queries)})
    return {"agent": agent, "leads_found": leads_found}


async def _convert_all_research(db: AsyncSession, org_id: str, vp_id: str) -> int:
    result = await db.execute(
        select(ResearchResult).where(
            ResearchResult.org_id == org_id,
            ResearchResult.converted_to_lead == False,
        )
    )
    converted = 0
    for row in result.scalars().all():
        lead_id = await convert_to_lead(db, org_id, row.id)
        if lead_id:
            converted += 1
    if converted:
        await log_vp_action(db, org_id, vp_id, "leads_converted",
                            f"Converted {converted} research results to CRM leads", {"count": converted})
    return converted


async def _assign_leads_to_sdr(db: AsyncSession, org_id: str, sdr_id: str) -> int:
    from app.models.agent import LeadState
    result = await db.execute(
        select(Lead).where(Lead.org_id == org_id)
    )
    leads = list(result.scalars().all())
    assigned = 0
    for lead in leads:
        existing = await db.execute(
            select(LeadState).where(
                LeadState.org_id == org_id,
                LeadState.lead_id == lead.id,
                LeadState.sdr_profile_id == sdr_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        ls = LeadState(
            org_id=org_id, lead_id=lead.id, sdr_profile_id=sdr_id,
            state="new", priority=50,
        )
        db.add(ls)
        assigned += 1
    if assigned:
        await db.flush()
    return assigned


async def _create_auto_campaign(db: AsyncSession, org_id: str, sdr_id: str, vp: VPSalesProfile) -> str:
    from app.models.campaign import Campaign, CampaignStep
    campaign = Campaign(
        org_id=org_id, sdr_profile_id=sdr_id,
        name=f"{vp.product_name or 'Outreach'} Campaign",
        description=f"Auto-generated campaign for {vp.product_name or 'prospecting'}. Target: {vp.target_country or 'global'}",
        status="active", ai_generated=True,
    )
    db.add(campaign)
    await db.flush()

    step1 = CampaignStep(
        campaign_id=campaign.id, step_order=1, channel="email", delay_days=0,
    )
    step2 = CampaignStep(
        campaign_id=campaign.id, step_order=2, channel="email", delay_days=3,
    )
    step3 = CampaignStep(
        campaign_id=campaign.id, step_order=3, channel="call", delay_days=7,
    )
    db.add_all([step1, step2, step3])
    await db.flush()

    await log_vp_action(db, org_id, vp.id, "campaign_created",
                        f"Campaign '{campaign.name}' created for SDR {sdr_id[:8]}",
                        {"campaign_id": campaign.id, "sdr_id": sdr_id, "steps": 3})
    return campaign.id


async def _run_lead_generation(db: AsyncSession, org_id: str, vp: VPSalesProfile) -> list[str]:
    steps = []
    all_queries = await _generate_queries(vp)
    if not all_queries:
        all_queries = ["small business owners directory contact", "restaurant owners email list", "salon owners phone directory"]

    chunk_size = max(2, len(all_queries) // 3)
    for i in range(0, min(len(all_queries), 6), chunk_size):
        queries_chunk = all_queries[i:i + chunk_size]
        try:
            r = await _create_auto_agent(db, org_id, vp, queries_chunk)
            if r["leads_found"]:
                steps.append(f"Agent '{r['agent'].name}' found {r['leads_found']} leads")
        except Exception as e:
            logger.warning("Agent creation failed: %s", e)
            steps.append(f"Research attempt failed: {e}")

    if steps:
        converted = await _convert_all_research(db, org_id, vp.id)
        if converted:
            steps.append(f"{converted} leads converted to CRM")
    else:
        await log_vp_action(db, org_id, vp.id, "research_skip",
                            "No leads found from any search source. Try enabling more sources in Lead Sources page.", {})
        steps.append("No leads found — enable more lead sources")
    return steps


async def _launch_ai_sales_team(db: AsyncSession, org_id: str, vp: VPSalesProfile) -> list[str]:
    steps = []
    sdr_name = f"SDR - {vp.product_name or 'Outreach'}"
    try:
        sdr = SDRProfile(
            org_id=org_id, name=sdr_name, sell_type="product",
            product_name=vp.product_name or "",
            product_description=vp.product_description or "",
            service_description=vp.service_description or "",
            target_country=vp.target_country or "",
            target_industries=vp.icp_description or "",
            is_active=True,
        )
        db.add(sdr)
        await db.flush()
        sdr_id = sdr.id

        assigned = await _assign_leads_to_sdr(db, org_id, sdr_id)
        await log_vp_action(db, org_id, vp.id, "sdr_created",
                            f"SDR '{sdr_name}' created and activated with {assigned} leads",
                            {"sdr_id": sdr_id, "leads_assigned": assigned})
        steps.append(f"SDR '{sdr_name}' created with {assigned} leads")

        campaign_id = await _create_auto_campaign(db, org_id, sdr_id, vp)
        steps.append("Campaign created with 3-step sequence (email → email → call)")
    except Exception as e:
        logger.warning("Sales team launch failed: %s", e)
        steps.append(f"Sales team launch failed: {e}")
    return steps


async def decide_and_execute(db: AsyncSession, org_id: str, vp: VPSalesProfile) -> dict:
    if not vp.product_name and not vp.target_country:
        await log_vp_action(db, org_id, vp.id, "setup_needed",
                            "VP profile incomplete. Add product and target country.", {})
        return {"action": "setup_needed", "reasoning": "Fill in product and target country in VP profile", "actions_executed": []}

    situation = await assess_lead_situation(db, org_id, vp)
    all_steps = []

    lead_steps = await _run_lead_generation(db, org_id, vp)
    all_steps.extend(lead_steps)

    if vp.outreach_active:
        outreach_steps = await _launch_ai_sales_team(db, org_id, vp)
        all_steps.extend(outreach_steps)

    final = await assess_lead_situation(db, org_id, vp)
    if not all_steps:
        await log_vp_action(db, org_id, vp.id, "monitor",
                            "All systems operational. Monitoring.", {})
        all_steps.append("All systems running — monitoring only")

    return {
        "action": "pipeline_executed",
        "reasoning": "; ".join(all_steps),
        "actions_executed": all_steps,
        "leads_before": situation["total_leads"],
        "leads_after": final["total_leads"],
        "sdrs_before": situation["total_sdrs"],
        "sdrs_after": final["total_sdrs"],
    }


async def _ai_decision(situation: dict, vp: VPSalesProfile) -> dict:
    prompt = (
        f"You are a VP of Sales for a company. Assess the current situation and decide the next action.\n\n"
        f"Current situation:\n"
        f"- Total leads in CRM: {situation['total_leads']}\n"
        f"- Unconverted research findings: {situation['unconverted_research']}\n"
        f"- Research agents: {situation['total_agents']}\n"
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
        f"Return ONLY valid JSON with:\n"
        f"- action: the selected action\n"
        f"- reasoning: explanation\n"
        f"- suggested_queries: [3 search query strings] if create_research_agent\n"
        f"- sdr_recommendation: {{name, focus}} if create_sdr\n"
    )
    models_to_try = ["deepseek-v4-flash-free", "openrouter-auto", "deepseek-v3"]
    last_error = None
    for model_id in models_to_try:
        try:
            result = await generate_text("", prompt, model_id=model_id)
            return json.loads(result.strip())
        except Exception as e:
            last_error = e
    raise last_error or Exception("All AI models failed")


def _rule_based_decision(situation: dict) -> dict:
    s = situation
    if s["unconverted_research"] > 0:
        return {"action": "convert_research_to_leads", "reasoning": f"{s['unconverted_research']} research findings ready to convert to leads."}
    if s["total_leads"] == 0:
        return {"action": "create_research_agent", "reasoning": "No leads in pipeline. Start research to find prospects.", "suggested_queries": []}
    if s["total_leads"] > 5 and s["active_sdrs"] == 0:
        return {"action": "create_sdr", "reasoning": f"{s['total_leads']} leads available but no active SDRs.", "sdr_recommendation": {"name": "SDR - Auto", "focus": "Lead follow-up"}}
    if s["total_sdrs"] > s["active_sdrs"]:
        return {"action": "monitor", "reasoning": f"{s['active_sdrs']}/{s['total_sdrs']} SDRs active."}
    return {"action": "monitor", "reasoning": "All systems running. Monitoring."}


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

    meetings_result = await db.execute(
        select(func.count()).select_from(Lead)
        .where(
            Lead.org_id == org_id,
            Lead.status == "meeting_scheduled",
        )
    )
    meetings_generated = meetings_result.scalar() or 0

    decisions = await get_vp_decisions(db, org_id, vp_id)

    vp = await db.get(VPSalesProfile, vp_id)

    return {
        "active_agents": len([a for a in all_agents if a.status == "running"]),
        "total_agents": len(all_agents),
        "leads_collected": total_research_leads,
        "crm_leads": await db.scalar(
            select(func.count(Lead.id)).where(Lead.org_id == org_id)
        ) or 0,
        "unconverted_research": await db.scalar(
            select(func.count(ResearchResult.id)).where(
                ResearchResult.org_id == org_id,
                ResearchResult.converted_to_lead == False,
            )
        ) or 0,
        "sdrs_created": len(all_sdrs),
        "active_sdrs": len(active_sdrs),
        "meetings_generated": meetings_generated,
        "sources_used": await get_enabled_sources(db, org_id),
        "outreach_active": bool(vp and vp.outreach_active),
        "recent_decisions": decisions,
    }
