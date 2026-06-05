import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.vp_sales import VPSalesProfile, ResearchResult, VPActionLog
from app.models.vp_sales import ResearchAgent as ResearchAgentModel
from app.models.vp_orchestration import Mission, MissionTask, AgentMemory, AgentPerformance
from app.models.agent import SDRProfile, LeadState
from app.models.lead import Lead
from app.models.campaign import Campaign, CampaignStep
from app.models.agent_activity import CampaignEvent
from app.services.lead_sources.service import get_enabled_sources
from app.services.research.search_service import clear_search_progress
from app.services.research.agent_service import convert_to_lead
from app.services.mission.mission_service import (
    create_mission, decompose_mission, evaluate_mission_reports,
    get_vp_missions,
)
from app.services.agents.research_agent import ResearchAgent
from app.services.agents.outreach_agent import OutreachAgent
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


async def get_vp_decisions(db: AsyncSession, org_id: str, vp_id: str) -> list[dict]:
    result = await db.execute(
        select(VPActionLog).where(
            VPActionLog.org_id == org_id,
            VPActionLog.vp_id == vp_id,
        ).order_by(VPActionLog.created_at.desc()).limit(20)
    )
    return [
        {
            "id": log.id,
            "action_type": log.action_type,
            "reasoning": log.reasoning,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in result.scalars().all()
    ]


async def assess_situation(db: AsyncSession, org_id: str) -> dict:
    return {
        "leads": await db.scalar(select(func.count(Lead.id)).where(Lead.org_id == org_id)) or 0,
        "unconverted_research": await db.scalar(
            select(func.count(ResearchResult.id)).where(
                ResearchResult.org_id == org_id, ResearchResult.converted_to_lead == False,
            )
        ) or 0,
        "sdrs": await db.scalar(
            select(func.count(SDRProfile.id)).where(
                SDRProfile.org_id == org_id, SDRProfile.deleted_at.is_(None),
            )
        ) or 0,
        "active_sdrs": await db.scalar(
            select(func.count(SDRProfile.id)).where(
                SDRProfile.org_id == org_id, SDRProfile.is_active == True,
                SDRProfile.deleted_at.is_(None),
            )
        ) or 0,
        "active_missions": await db.scalar(
            select(func.count(Mission.id)).where(
                Mission.org_id == org_id, Mission.status.in_(["in_progress", "draft"]),
            )
        ) or 0,
        "research_agents": await db.scalar(
            select(func.count(ResearchAgentModel.id)).where(ResearchAgentModel.org_id == org_id)
        ) or 0,
        "sources": await get_enabled_sources(db, org_id),
    }


async def log_vp_action(db: AsyncSession, org_id: str, vp_id: str, action_type: str, reasoning: str, details: Optional[dict] = None):
    db.add(VPActionLog(org_id=org_id, vp_id=vp_id, action_type=action_type, reasoning=reasoning, details=details or {}))
    await db.flush()


async def _vp_decide(db: AsyncSession, org_id: str, vp: VPSalesProfile, situation: dict) -> dict:
    """VP decides next action using rules (for correctness) + AI (for enrichment)."""

    decision = await _vp_decide_rules(vp, situation)

    # Try to enrich decision with AI (better mission objectives, reasoning)
    if decision["action"] in ("research", "campaign", "deploy_sdr"):
        try:
            enriched = await _vp_enrich_decision(vp, situation, decision)
            if enriched.get("action") == decision["action"]:
                decision = enriched
        except Exception:
            pass

    return decision


async def _vp_enrich_decision(vp: VPSalesProfile, situation: dict, base_decision: dict) -> dict:
    """Use AI to enrich a rule-based decision with better reasoning and mission details."""
    action = base_decision["action"]
    prompt = (
        f"You are the VP of Sales. Company sells: {vp.product_name or 'Unknown Product'}. "
        f"Target: {vp.target_country or 'global'}. "
        f"ICP: {vp.icp_description or vp.target_audience or 'business owners'}. "
        f"Business types: {vp.target_business_types or 'various'}.\n"
        f"Business goals: {vp.business_goals or 'Generate revenue'}\n\n"
        f"The decision has been made to: {action}.\n"
        f"Current pipeline: {situation['leads']} leads, {situation['sdrs']} SDRs.\n\n"
    )
    if action == "research":
        prompt += (
            f"Generate a focused research mission. Return ONLY JSON with:\n"
            f"- reasoning: why this research matters\n"
            f"- mission: {{ name, objective: specific what to find and where, kpi }}\n"
        )
    elif action == "deploy_sdr":
        prompt += (
            f"Return ONLY JSON with:\n"
            f"- reasoning: why deploy now\n"
            f"- sdr_name: a professional SDR name for this product\n"
        )
    elif action == "campaign":
        prompt += (
            f"Return ONLY JSON with:\n"
            f"- reasoning: why campaign now\n"
            f"- mission: {{ name, objective, kpi }}\n"
        )
    else:
        return base_decision

    result = await generate_text("", prompt, max_tokens=1024, temperature=0.1)
    enriched = json.loads(result)
    enriched["action"] = action
    return enriched


async def _vp_decide_rules(vp: VPSalesProfile, situation: dict) -> dict:
    """Rule-based decision engine. Always picks the right action."""
    if situation["active_missions"] > 0:
        return {"action": "wait", "reasoning": f"{situation['active_missions']} mission(s) running."}

    if not vp.product_name and not vp.target_country:
        return {"action": "setup", "reasoning": "Need product and target country in VP profile."}

    if situation["leads"] < 10:
        biz = vp.target_business_types or vp.icp_description or "businesses"
        country = vp.target_country or "global"
        return {
            "action": "research",
            "reasoning": f"Only {situation['leads']} leads. Launching research to find {biz} in {country}.",
            "mission": {
                "name": f"Find {country} {biz}",
                "objective": f"Find real {biz} owners in {country} with email and phone. Target: {vp.product_name or ''} ICP.",
                "kpi": "At least 20 leads with verified contact info",
            },
        }

    if situation["unconverted_research"] > 0:
        return {"action": "convert", "reasoning": f"{situation['unconverted_research']} results ready for CRM."}

    if situation["sdrs"] == 0:
        return {
            "action": "deploy_sdr",
            "reasoning": f"{situation['leads']} leads ready. Deploying SDR for outreach.",
            "sdr_name": f"SDR - {vp.product_name or 'Sales'}",
        }

    if vp.outreach_active and situation["active_sdrs"] > 0:
        return {
            "action": "campaign",
            "reasoning": "SDR deployed. Creating outreach campaign.",
            "mission": {
                "name": f"Campaign - {vp.product_name or 'Outreach'}",
                "objective": f"Execute outreach for {vp.product_name or 'services'} in {vp.target_country or 'global'}.",
                "kpi": "Generate meetings from campaign",
            },
        }

    return {"action": "monitor", "reasoning": "All systems running. Watching pipeline."}


async def _execute_research_mission(db: AsyncSession, org_id: str, vp_id: str,
                                     mission_data: dict,
                                     progress_session: Optional[str] = None) -> list[str]:
    steps = []
    mission = await create_mission(db, org_id, vp_id, mission_data["name"], mission_data["objective"], mission_data.get("kpi"))
    steps.append(f"Mission: {mission.name}")

    tasks = await decompose_mission(db, org_id, vp_id, mission)
    steps.append(f"→ {len(tasks)} task(s) created")

    for task in tasks:
        try:
            agent = ResearchAgent(db, org_id)
            agent.agent_id = task.id
            agent.progress_session = progress_session
            report = await agent.run(task)

            findings = report.get("findings", [])
            if findings:
                saved = await agent.save_to_crm(findings)
                steps.append(f"Research Agent found {saved} leads")

                converted = 0
                results = await db.execute(
                    select(ResearchResult).where(
                        ResearchResult.org_id == org_id,
                        ResearchResult.converted_to_lead == False,
                    )
                )
                for rr in results.scalars().all():
                    if await convert_to_lead(db, org_id, rr.id):
                        converted += 1
                if converted:
                    steps.append(f"→ {converted} converted to CRM leads")
            else:
                steps.append("Research Agent found 0 leads — try broader queries")
        except Exception as e:
            logger.warning("Research task failed: %s", e)
            steps.append(f"Research failed: {str(e)[:60]}")

    evaluation = await evaluate_mission_reports(db, org_id, vp_id, mission)
    steps.append(f"VP review: {evaluation['verdict']} ({evaluation['completed']}/{evaluation['total_tasks']})")
    return steps


async def _deploy_sdr(db: AsyncSession, org_id: str, vp: VPSalesProfile, name: str) -> list[str]:
    steps = []
    try:
        sdr = SDRProfile(
            org_id=org_id, name=name, sell_type="product",
            product_name=vp.product_name or "",
            product_description=vp.product_description or "",
            service_description=vp.service_description or "",
            target_country=vp.target_country or "",
            target_industries=vp.icp_description or "",
            is_active=True,
        )
        db.add(sdr)
        await db.flush()

        # Assign all leads to SDR
        from app.models.agent import LeadState
        leads = await db.execute(select(Lead).where(Lead.org_id == org_id))
        assigned = 0
        for lead in leads.scalars().all():
            existing = await db.execute(
                select(LeadState).where(
                    LeadState.org_id == org_id,
                    LeadState.lead_id == lead.id,
                    LeadState.sdr_profile_id == sdr.id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(LeadState(org_id=org_id, lead_id=lead.id, sdr_profile_id=sdr.id, state="new", priority=50))
                assigned += 1
        if assigned:
            await db.flush()

        steps.append(f"SDR '{name}' deployed with {assigned} leads")

        # Create campaign
        from app.models.campaign import Campaign, CampaignStep
        campaign = Campaign(
            org_id=org_id, sdr_profile_id=sdr.id,
            name=f"{vp.product_name or 'Outreach'} Campaign",
            status="active", ai_generated=True,
        )
        db.add(campaign)
        await db.flush()
        for i, (ch, delay) in enumerate([("email", 0), ("email", 3), ("call", 7)]):
            db.add(CampaignStep(campaign_id=campaign.id, step_order=i + 1, channel=ch, delay_days=delay))
        await db.flush()
        steps.append("→ 3-step campaign created (email → email → call)")
    except Exception as e:
        logger.warning("SDR deploy failed: %s", e)
        steps.append(f"SDR deploy failed: {e}")
    return steps


async def _create_outreach_mission(db: AsyncSession, org_id: str, vp_id: str, mission_data: dict) -> list[str]:
    steps = []
    mission = await create_mission(db, org_id, vp_id, mission_data["name"], mission_data["objective"], mission_data.get("kpi"))
    steps.append(f"Mission: {mission.name}")

    tasks = await decompose_mission(db, org_id, vp_id, mission)
    for task in tasks:
        try:
            agent = OutreachAgent(db, org_id)
            agent.agent_id = task.id
            report = await agent.run(task)
            steps.append(f"SDR Agent: {report.get('work_completed', 'planned')}")
        except Exception as e:
            steps.append(f"SDR planning failed: {e}")

    evaluation = await evaluate_mission_reports(db, org_id, vp_id, mission)
    steps.append(f"VP review: {evaluation['verdict']}")
    return steps


async def decide_and_execute(db: AsyncSession, org_id: str, vp: VPSalesProfile,
                             progress_session: Optional[str] = None,
                             force_research: bool = False) -> dict:
    if force_research:
        # First wipe all old data so VP starts clean
        tables = [
            ResearchResult, ResearchAgentModel, VPActionLog,
            AgentMemory, AgentPerformance,
            MissionTask, Mission,
            LeadState, SDRProfile,
            CampaignEvent, CampaignStep, Campaign,
            Lead,
        ]
        for table in tables:
            result = await db.execute(select(table).where(table.org_id == org_id))
            for row in result.scalars().all():
                await db.delete(row)
        await db.flush()
        clear_search_progress(org_id)

    situation = await assess_situation(db, org_id)

    if force_research:
        biz = vp.target_business_types or vp.icp_description or "businesses"
        country = vp.target_country or "global"
        decision = {
            "action": "research",
            "reasoning": f"Force research: finding {biz} in {country}.",
            "mission": {
                "name": f"Find {country} {biz}",
                "objective": f"Find real {biz} owners in {country} with email and phone. Target: {vp.product_name or ''} ICP.",
                "kpi": "At least 20 leads with verified contact info",
            },
        }
        situation = {"leads": 0, "unconverted_research": 0, "sdrs": 0, "active_sdrs": 0, "active_missions": 0, "research_agents": 0, "sources": []}
    else:
        decision = await _vp_decide(db, org_id, vp, situation)

    await log_vp_action(db, org_id, vp.id, decision["action"], decision["reasoning"])

    steps = []
    action = decision["action"]

    if action == "research":
        steps = await _execute_research_mission(db, org_id, vp.id, decision["mission"],
                                                 progress_session=progress_session)
    elif action == "convert":
        result = await db.execute(
            select(ResearchResult).where(
                ResearchResult.org_id == org_id, ResearchResult.converted_to_lead == False,
            )
        )
        c = 0
        for rr in result.scalars().all():
            if await convert_to_lead(db, org_id, rr.id):
                c += 1
        steps.append(f"Converted {c} research results to CRM leads")
    elif action == "deploy_sdr":
        steps = await _deploy_sdr(db, org_id, vp, decision["sdr_name"])
    elif action == "campaign":
        steps = await _create_outreach_mission(db, org_id, vp.id, decision["mission"])
    else:
        steps.append("VP monitoring — no action needed")

    final = await assess_situation(db, org_id)

    return {
        "action": action,
        "reasoning": decision["reasoning"],
        "actions": steps,
        "leads_before": situation["leads"],
        "leads_after": final["leads"],
        "sdrs_before": situation["sdrs"],
        "sdrs_after": final["sdrs"],
    }


async def get_vp_dashboard(db: AsyncSession, org_id: str, vp_id: str) -> dict:
    vp = await db.get(VPSalesProfile, vp_id)
    situation = await assess_situation(db, org_id)
    decisions = await get_vp_decisions(db, org_id, vp_id)

    # Get research leads count
    agents = await db.execute(select(ResearchAgentModel).where(ResearchAgentModel.org_id == org_id))
    total_research = sum(a.leads_discovered or 0 for a in agents.scalars().all())

    # Get meetings
    meetings = await db.scalar(
        select(func.count()).select_from(Lead).where(
            Lead.org_id == org_id, Lead.status == "meeting_scheduled",
        )
    ) or 0

    # Get missions
    missions = await get_vp_missions(db, org_id)

    return {
        "leads": situation["leads"],
        "unconverted_research": situation["unconverted_research"],
        "research_agents": situation["research_agents"],
        "total_research_leads": total_research,
        "sdrs": situation["sdrs"],
        "active_sdrs": situation["active_sdrs"],
        "meetings": meetings,
        "active_missions": situation["active_missions"],
        "sources": situation["sources"],
        "recent_decisions": decisions,
        "missions": missions[:5],
        "outreach_active": bool(vp and vp.outreach_active),
    }
