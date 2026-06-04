import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.vp_sales import VPSalesProfile, ResearchAgent, ResearchResult, VPActionLog
from app.models.vp_orchestration import Mission, MissionTask
from app.models.agent import SDRProfile
from app.models.lead import Lead
from app.services.lead_sources.service import get_enabled_sources
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
            select(func.count(ResearchAgent.id)).where(ResearchAgent.org_id == org_id)
        ) or 0,
        "sources": await get_enabled_sources(db, org_id),
    }


async def log_vp_action(db: AsyncSession, org_id: str, vp_id: str, action_type: str, reasoning: str, details: Optional[dict] = None):
    db.add(VPActionLog(org_id=org_id, vp_id=vp_id, action_type=action_type, reasoning=reasoning, details=details or {}))
    await db.flush()


async def _vp_decide(db: AsyncSession, org_id: str, vp: VPSalesProfile, situation: dict) -> dict:
    """VP thinks about the situation using AI and decides next action. Falls back to rules if AI fails."""

    try:
        prompt = (
            f"You are the VP of Sales for a company selling: {vp.product_name or 'Unknown Product'}.\n"
            f"Product description: {vp.product_description or 'N/A'}\n"
            f"Service: {vp.service_description or 'N/A'}\n"
            f"Target audience/ICP: {vp.icp_description or vp.target_audience or 'N/A'}\n"
            f"Target country: {vp.target_country or 'N/A'}\n"
            f"Target business types: {vp.target_business_types or 'N/A'}\n"
            f"Target titles: {vp.target_titles or 'N/A'}\n"
            f"Business goals: {vp.business_goals or 'N/A'}\n"
            f"Sales objectives: {vp.sales_objectives or 'N/A'}\n\n"
            f"Current situation:\n"
            f"- CRM leads: {situation['leads']}\n"
            f"- Research findings not yet in CRM: {situation['unconverted_research']}\n"
            f"- Research agents: {situation['research_agents']}\n"
            f"- SDRs deployed: {situation['sdrs']} (active: {situation['active_sdrs']})\n"
            f"- Active missions: {situation['active_missions']}\n"
            f"- Enabled data sources: {', '.join(situation['sources']) or 'none'}\n"
            f"- Outreach active: {vp.outreach_active}\n\n"
            f"Decide the single best next action. Available actions:\n"
            f"1. 'research' — launch a search to find real business owners with contact info\n"
            f"2. 'convert' — move unconverted research findings into CRM leads\n"
            f"3. 'deploy_sdr' — create and deploy an SDR (sales development rep)\n"
            f"4. 'campaign' — start an outreach campaign via existing SDR\n"
            f"5. 'wait' — hold, let current missions complete\n"
            f"6. 'setup' — VP profile needs more configuration\n"
            f"7. 'monitor' — everything is good, keep watching\n\n"
            f"Return ONLY valid JSON with: action, reasoning, and if action is 'research' include:\n"
            f"  mission: {{ name, objective (detailed what to find and where), kpi }}\n"
            f"If action is 'deploy_sdr' include: sdr_name\n"
            f"If action is 'campaign' include: mission: {{ name, objective, kpi }}\n"
            f"Be specific about what to research, where, and why."
        )
        vp_prompt = f"You are the VP of Sales. Think carefully about pipeline status and revenue goals."
        result = await generate_text(vp_prompt, prompt, max_tokens=1024, temperature=0.3)
        decision = json.loads(result)
        if decision.get("action") in ("research", "convert", "deploy_sdr", "campaign", "wait", "setup", "monitor"):
            return decision
    except Exception:
        logger.info("AI VP decision failed, using rule fallback", exc_info=True)

    # ---- Rule-based fallback ----
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
                             progress_session: Optional[str] = None) -> dict:
    situation = await assess_situation(db, org_id)
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
    agents = await db.execute(select(ResearchAgent).where(ResearchAgent.org_id == org_id))
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
