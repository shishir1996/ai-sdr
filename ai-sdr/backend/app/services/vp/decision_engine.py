import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.vp_sales import VPSalesProfile, ResearchAgent, ResearchResult, VPActionLog
from app.models.vp_orchestration import Mission, MissionTask, AgentPerformance
from app.models.agent import SDRProfile
from app.models.lead import Lead
from app.services.ai.provider import generate_text
from app.services.lead_sources.service import get_enabled_sources
from app.services.research.agent_service import create_research_agent, execute_research, convert_to_lead
from app.services.mission.mission_service import (
    create_mission, decompose_mission, evaluate_mission_reports,
    assign_task_to_agent, collect_task_report, get_vp_missions,
)
from app.services.agents.research_agent import ResearchAgentIntelligence
from app.services.agents.outreach_agent import OutreachAgent

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

    missions = await db.execute(
        select(func.count(Mission.id)).where(
            Mission.org_id == org_id,
            Mission.status.in_(["in_progress", "draft"]),
        )
    )
    active_missions = missions.scalar() or 0

    return {
        "total_leads": lead_count or 0,
        "unconverted_research": research_count or 0,
        "total_agents": agent_count or 0,
        "total_sdrs": sdr_count or 0,
        "active_sdrs": active_sdrs or 0,
        "active_missions": active_missions,
        "enabled_sources": enabled,
        "has_product_info": bool(vp.product_name or vp.product_description or vp.service_description),
        "has_target_country": bool(vp.target_country),
        "has_icp": bool(vp.icp_description),
        "has_business_types": bool(vp.target_business_types),
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


async def _vp_strategic_plan(situation: dict, vp: VPSalesProfile) -> dict:
    if situation["active_missions"] > 0:
        return {
            "action": "continue_missions",
            "reasoning": f"{situation['active_missions']} mission(s) in progress. Monitoring completion.",
        }

    if not situation["has_product_info"] or not situation["has_target_country"]:
        return {
            "action": "request_setup",
            "reasoning": "VP profile incomplete. Need product info and target country to plan strategy.",
        }

    if situation["total_leads"] < 10:
        objective_parts = []
        if vp.target_business_types:
            objective_parts.append(f"targeting {vp.target_business_types}")
        if vp.target_country:
            objective_parts.append(f"in {vp.target_country}")
        if vp.product_name:
            objective_parts.append(f"interested in {vp.product_name}")

        objective = f"Find business owners {' '.join(objective_parts)}. Collect names, emails, phones, and locations."
        kpi = f"Discover at least 50 qualified leads with verified contact information"

        return {
            "action": "create_mission",
            "reasoning": f"Not enough leads ({situation['total_leads']}). Launching research mission.",
            "mission": {
                "name": f"Lead Generation - {vp.target_country or 'Global'} {vp.target_business_types or 'Prospects'}",
                "objective": objective,
                "kpi_target": kpi,
            },
        }

    if situation["unconverted_research"] > 0:
        return {
            "action": "convert_leads",
            "reasoning": f"{situation['unconverted_research']} unconverted research findings ready for CRM.",
        }

    if situation["total_leads"] >= 10 and situation["active_sdrs"] == 0:
        return {
            "action": "deploy_sdr",
            "reasoning": f"{situation['total_leads']} leads in CRM ready for outreach. Deploying SDR.",
            "sdr_name": f"SDR - {vp.product_name or 'Outreach'}",
        }

    if situation["outreach_active"] and situation["active_sdrs"] > 0:
        return {
            "action": "create_campaign_mission",
            "reasoning": "SDRs deployed and outreach active. Creating campaign mission.",
            "mission": {
                "name": f"Campaign - {vp.product_name or 'Outreach'}",
                "objective": f"Create and execute outreach campaign for {vp.product_name or 'our services'} targeting {vp.target_country or 'global'} prospects. Generate meetings and qualified opportunities.",
                "kpi_target": "Generate at least 5 meetings from campaign",
            },
        }

    return {
        "action": "monitor",
        "reasoning": "All systems operational. VP monitoring performance metrics.",
    }


async def _execute_vp_plan(db: AsyncSession, org_id: str, vp: VPSalesProfile, plan: dict) -> list[str]:
    steps = []
    action = plan["action"]

    if action == "create_mission":
        mission_data = plan.get("mission", {})
        mission = await create_mission(
            db=db, org_id=org_id, vp_id=vp.id,
            name=mission_data.get("name", "Lead Generation"),
            objective=mission_data.get("objective", "Find prospects"),
            kpi_target=mission_data.get("kpi_target"),
        )
        await log_vp_action(db, org_id, vp.id, "mission_planned",
                            reasoning=plan["reasoning"],
                            details={"mission_id": mission.id, "mission_name": mission.name})
        steps.append(f"Mission '{mission.name}' created ({mission.id[:8]})")

        tasks = await decompose_mission(db, org_id, vp.id, mission,
                                        vp_reasoning=plan["reasoning"])
        steps.append(f"Mission decomposed into {len(tasks)} agent tasks")

        task_results = await _execute_agent_tasks(db, org_id, vp.id, tasks)
        steps.extend(task_results)

        evaluation = await evaluate_mission_reports(db, org_id, vp.id, mission)
        steps.append(f"VP evaluation: {evaluation['verdict'].upper()} "
                      f"({evaluation['completed']}/{evaluation['total_tasks']} tasks, "
                      f"confidence {evaluation['avg_confidence']})")

    elif action == "convert_leads":
        converted = await _convert_all_research(db, org_id, vp.id)
        steps.append(f"VP ordered conversion: {converted} research findings → CRM leads")

    elif action == "deploy_sdr":
        sdr_name = plan.get("sdr_name", "SDR - Auto")
        sdr_steps = await _launch_sdr(db, org_id, vp, sdr_name)
        steps.extend(sdr_steps)

    elif action == "create_campaign_mission":
        mission_data = plan.get("mission", {})
        mission = await create_mission(
            db=db, org_id=org_id, vp_id=vp.id,
            name=mission_data.get("name", "Campaign"),
            objective=mission_data.get("objective", "Execute outreach"),
            kpi_target=mission_data.get("kpi_target"),
        )
        steps.append(f"Campaign mission '{mission.name}' created")

        tasks = await decompose_mission(db, org_id, vp.id, mission)
        steps.append(f"Campaign tasks created: {len(tasks)}")

        agent_tasks = await _execute_agent_tasks(db, org_id, vp.id, tasks)
        steps.extend(agent_tasks)

        evaluation = await evaluate_mission_reports(db, org_id, vp.id, mission)
        steps.append(f"Campaign evaluation: {evaluation['verdict']}")

    elif action == "continue_missions":
        steps.append("VP monitoring active missions")

    else:
        steps.append("VP monitoring — no action needed")

    return steps


async def _execute_agent_tasks(
    db: AsyncSession, org_id: str, vp_id: str, tasks: list[MissionTask],
) -> list[str]:
    steps = []

    for task in tasks:
        agent_type = task.agent_type
        try:
            if agent_type == "research":
                agent = ResearchAgentIntelligence(db, org_id)
                agent.agent_id = task.id
                report = await agent.run(task)
                await assign_task_to_agent(db, task, agent.agent_id)

                findings = report.get("findings", [])
                saved = 0
                if findings:
                    for f in findings:
                        rr = ResearchResult(
                            org_id=org_id,
                            research_agent_id=None,
                            source=f.get("_source", "web_research"),
                            source_url=f.get("link", ""),
                            title=f.get("title", ""),
                            snippet=f.get("snippet", ""),
                            company_name=f.get("company_name", ""),
                            contact_name=f.get("contact_name", ""),
                            contact_title=f.get("contact_title", ""),
                            contact_email=f.get("contact_email", ""),
                            contact_phone=f.get("contact_phone", ""),
                            website=f.get("website", ""),
                            industry=f.get("industry", ""),
                            business_type=f.get("business_type", ""),
                            location=f.get("location", ""),
                            city=f.get("city", ""),
                            state=f.get("state", ""),
                            country=f.get("country", ""),
                            postal_code=f.get("postal_code", ""),
                            raw_data=f,
                            status="new",
                        )
                        db.add(rr)
                        saved += 1
                    await db.flush()

                steps.append(f"Research agent found {saved} prospects "
                              f"(confidence: {report.get('confidence', 0):.2f})")

                if saved:
                    converted = await _convert_all_research(db, org_id, vp_id)
                    if converted:
                        steps.append(f"{converted} leads added to CRM")

            elif agent_type == "outreach":
                agent = OutreachAgent(db, org_id)
                agent.agent_id = task.id
                report = await agent.run(task)
                await assign_task_to_agent(db, task, agent.agent_id)
                steps.append(f"Outreach agent: {report.get('work_completed', 'planned')}")

            else:
                await assign_task_to_agent(db, task, f"pending_{agent_type}")
                steps.append(f"{agent_type} agent task created — waiting for execution")
                task.status = "pending"
                await db.flush()

        except Exception as e:
            logger.warning("Agent task failed (%s): %s", agent_type, e)
            task.status = "failed"
            task.report = {"error": str(e)}
            await db.flush()
            steps.append(f"{agent_type} agent task failed: {str(e)[:80]}")

    return steps


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


async def _launch_sdr(db: AsyncSession, org_id: str, vp: VPSalesProfile, sdr_name: str) -> list[str]:
    steps = []
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
                            f"SDR '{sdr_name}' created with {assigned} leads",
                            {"sdr_id": sdr_id, "leads_assigned": assigned})
        steps.append(f"SDR '{sdr_name}' deployed with {assigned} leads")

        campaign_id = await _create_auto_campaign(db, org_id, sdr_id, vp)
        steps.append("Campaign created (email → email → call)")
    except Exception as e:
        logger.warning("SDR deployment failed: %s", e)
        steps.append(f"SDR deployment failed: {e}")
    return steps


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
        description=f"Auto-generated for {vp.product_name or 'prospecting'}. Target: {vp.target_country or 'global'}",
        status="active", ai_generated=True,
    )
    db.add(campaign)
    await db.flush()

    step1 = CampaignStep(campaign_id=campaign.id, step_order=1, channel="email", delay_days=0)
    step2 = CampaignStep(campaign_id=campaign.id, step_order=2, channel="email", delay_days=3)
    step3 = CampaignStep(campaign_id=campaign.id, step_order=3, channel="call", delay_days=7)
    db.add_all([step1, step2, step3])
    await db.flush()

    await log_vp_action(db, org_id, vp.id, "campaign_created",
                        f"Campaign '{campaign.name}' created for SDR {sdr_id[:8]}",
                        {"campaign_id": campaign.id, "sdr_id": sdr_id})
    return campaign.id


async def decide_and_execute(db: AsyncSession, org_id: str, vp: VPSalesProfile) -> dict:
    if not vp.product_name and not vp.target_country:
        await log_vp_action(db, org_id, vp.id, "setup_needed",
                            "VP profile incomplete. Add product and target country.", {})
        return {"action": "setup_needed", "reasoning": "Fill in product and target country in VP profile", "actions_executed": []}

    situation = await assess_lead_situation(db, org_id, vp)
    plan = await _vp_strategic_plan(situation, vp)

    await log_vp_action(db, org_id, vp.id, "vp_decided",
                        reasoning=plan["reasoning"],
                        details={"plan": plan, "situation": situation})

    steps = await _execute_vp_plan(db, org_id, vp, plan)

    final_situation = await assess_lead_situation(db, org_id, vp)

    return {
        "action": plan["action"],
        "reasoning": plan["reasoning"],
        "actions_executed": steps,
        "leads_before": situation["total_leads"],
        "leads_after": final_situation["total_leads"],
        "sdrs_before": situation["total_sdrs"],
        "sdrs_after": final_situation["total_sdrs"],
        "missions_active": final_situation["active_missions"],
    }


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
        .where(Lead.org_id == org_id, Lead.status == "meeting_scheduled")
    )
    meetings_generated = meetings_result.scalar() or 0

    vp = await db.get(VPSalesProfile, vp_id)

    missions = await get_vp_missions(db, org_id)
    decisions = await get_vp_decisions(db, org_id, vp_id)

    agent_perf = await db.execute(
        select(AgentPerformance).where(AgentPerformance.org_id == org_id)
    )
    perf_rows = agent_perf.scalars().all()
    agent_kpis = {}
    for p in perf_rows:
        key = f"{p.agent_type}_{p.metric_name}"
        if key not in agent_kpis or p.updated_at > agent_kpis[key]["updated_at"]:
            agent_kpis[key] = {
                "agent_type": p.agent_type,
                "metric_name": p.metric_name,
                "metric_value": p.metric_value,
                "period": p.period,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }

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
        "active_missions": len([m for m in missions if m["status"] in ("in_progress", "draft")]),
        "missions": missions[:5],
        "agent_performance": list(agent_kpis.values()),
    }
