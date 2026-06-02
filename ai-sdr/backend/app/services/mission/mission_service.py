import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vp_orchestration import Mission, MissionTask, AgentPerformance
from app.models.vp_sales import VPSalesProfile, VPActionLog
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)

AGENT_TYPE_MAP = {
    "research": "ResearchAgent",
    "outreach": "OutreachAgent",
    "linkedin": "LinkedInAgent",
    "calling": "CallingAgent",
}


async def create_mission(
    db: AsyncSession,
    org_id: str,
    vp_id: str,
    name: str,
    objective: str,
    kpi_target: Optional[str] = None,
) -> Mission:
    mission = Mission(
        org_id=org_id,
        vp_id=vp_id,
        name=name,
        objective=objective,
        kpi_target=kpi_target,
        status="draft",
    )
    db.add(mission)
    await db.flush()

    vp_log = VPActionLog(
        org_id=org_id,
        vp_id=vp_id,
        action_type="mission_created",
        reasoning=f"Created mission '{name}': {objective[:200]}",
        details={"mission_id": mission.id, "objective": objective, "kpi_target": kpi_target},
    )
    db.add(vp_log)
    await db.flush()
    return mission


async def decompose_mission(
    db: AsyncSession,
    org_id: str,
    vp_id: str,
    mission: Mission,
    vp_reasoning: Optional[str] = None,
) -> list[MissionTask]:
    mission.vp_reasoning = vp_reasoning
    await db.flush()

    task_defs = await _vp_decompose_objective(mission.objective, mission.kpi_target)

    tasks = []
    for td in task_defs:
        task = MissionTask(
            mission_id=mission.id,
            org_id=org_id,
            agent_type=td.get("agent_type", "research"),
            objective=td.get("objective", mission.objective),
            status="pending",
        )
        db.add(task)
        tasks.append(task)
    await db.flush()

    mission.status = "in_progress"
    await db.flush()

    vp_log = VPActionLog(
        org_id=org_id,
        vp_id=vp_id,
        action_type="mission_decomposed",
        reasoning=f"Decomposed mission '{mission.name}' into {len(tasks)} tasks: {', '.join(t.agent_type for t in tasks)}",
        details={"mission_id": mission.id, "task_count": len(tasks), "task_defs": task_defs},
    )
    db.add(vp_log)
    await db.flush()
    return tasks


async def _vp_decompose_objective(objective: str, kpi_target: Optional[str] = None) -> list[dict]:
    try:
        prompt = (
            f"As VP of Sales, decompose this objective into agent tasks.\n\n"
            f"Objective: {objective}\n"
            f"KPI Target: {kpi_target or 'Not specified'}\n\n"
            f"Available agents: research (finds prospects), outreach (creates campaigns/messaging), "
            f"linkedin (social selling), calling (phone outreach).\n\n"
            f"Return ONLY a JSON array of task objects, each with:\n"
            f"- agent_type: one of research/outreach/linkedin/calling\n"
            f"- objective: clear objective for this agent\n"
            f"- priority: 1-5\n\n"
            f"Example: [{{\"agent_type\":\"research\",\"objective\":\"Find 500 SaaS founders in USA\",\"priority\":1}}]"
        )
        result = await generate_text("", prompt)
        tasks = json.loads(result.strip())
        if isinstance(tasks, list):
            return tasks[:5]
    except Exception:
        pass

    return [{
        "agent_type": "research",
        "objective": objective,
        "priority": 1,
    }]


async def assign_task_to_agent(db: AsyncSession, task: MissionTask, agent_id: str) -> MissionTask:
    task.agent_id = agent_id
    task.status = "assigned"
    await db.flush()
    return task


async def collect_task_report(db: AsyncSession, task: MissionTask) -> dict:
    if task.report:
        return task.report
    return {
        "task_objective": task.objective,
        "status": task.status,
        "note": "No report generated yet",
    }


async def evaluate_mission_reports(
    db: AsyncSession,
    org_id: str,
    vp_id: str,
    mission: Mission,
) -> dict:
    tasks = await db.execute(
        select(MissionTask).where(
            MissionTask.mission_id == mission.id,
        )
    )
    all_tasks = list(tasks.scalars().all())

    completed = [t for t in all_tasks if t.status == "completed"]
    failed = [t for t in all_tasks if t.status == "failed"]
    pending = [t for t in all_tasks if t.status not in ("completed", "failed")]

    avg_confidence = 0.0
    if completed:
        avg_confidence = sum(t.confidence_score or 0 for t in completed) / len(completed)

    evaluation = {
        "mission_id": mission.id,
        "mission_name": mission.name,
        "total_tasks": len(all_tasks),
        "completed": len(completed),
        "failed": len(failed),
        "pending": len(pending),
        "avg_confidence": round(avg_confidence, 2),
        "verdict": "approved" if completed and avg_confidence >= 0.4 else "revise",
        "vp_recommendation": "",
    }

    if evaluation["verdict"] == "approved":
        mission.status = "completed"
        evaluation["vp_recommendation"] = "Mission objectives met. Proceeding to next phase."
    elif completed and avg_confidence < 0.4:
        mission.status = "in_progress"
        evaluation["vp_recommendation"] = "Low confidence. Consider refining search queries or enabling more sources."
    else:
        mission.status = "blocked"
        evaluation["vp_recommendation"] = "Some tasks incomplete. Waiting for agent reports."

    await db.flush()

    vp_log = VPActionLog(
        org_id=org_id,
        vp_id=vp_id,
        action_type="mission_evaluated",
        reasoning=(f"Mission '{mission.name}' evaluated: {evaluation['verdict'].upper()}. "
                   f"{evaluation['completed']}/{evaluation['total_tasks']} tasks completed. "
                   f"Avg confidence: {evaluation['avg_confidence']}"),
        details=evaluation,
    )
    db.add(vp_log)
    await db.flush()

    return evaluation


async def get_vp_missions(db: AsyncSession, org_id: str, status: Optional[str] = None) -> list[dict]:
    query = select(Mission).where(Mission.org_id == org_id)
    if status:
        query = query.where(Mission.status == status)
    query = query.order_by(Mission.created_at.desc()).limit(20)

    result = await db.execute(query)
    missions = result.scalars().all()

    output = []
    for m in missions:
        tasks = await db.execute(
            select(MissionTask).where(MissionTask.mission_id == m.id)
        )
        task_list = list(tasks.scalars().all())
        output.append({
            "id": m.id,
            "name": m.name,
            "objective": m.objective,
            "kpi_target": m.kpi_target,
            "status": m.status,
            "vp_reasoning": m.vp_reasoning,
            "tasks": [
                {
                    "id": t.id,
                    "agent_type": t.agent_type,
                    "agent_id": t.agent_id,
                    "objective": t.objective,
                    "status": t.status,
                    "confidence_score": t.confidence_score,
                    "vp_feedback": t.vp_feedback,
                    "report_summary": t.report.get("work_completed", "") if t.report else "",
                }
                for t in task_list
            ],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return output


async def get_mission_detail(db: AsyncSession, mission_id: str) -> Optional[dict]:
    mission = await db.get(Mission, mission_id)
    if not mission:
        return None

    tasks = await db.execute(
        select(MissionTask).where(MissionTask.mission_id == mission.id)
    )
    task_list = list(tasks.scalars().all())

    return {
        "id": mission.id,
        "org_id": mission.org_id,
        "vp_id": mission.vp_id,
        "name": mission.name,
        "objective": mission.objective,
        "kpi_target": mission.kpi_target,
        "status": mission.status,
        "vp_reasoning": mission.vp_reasoning,
        "tasks": [
            {
                "id": t.id,
                "agent_type": t.agent_type,
                "agent_id": t.agent_id,
                "objective": t.objective,
                "execution_plan": t.execution_plan,
                "status": t.status,
                "report": t.report,
                "confidence_score": t.confidence_score,
                "vp_feedback": t.vp_feedback,
                "vp_notes": t.vp_notes,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in task_list
        ],
        "created_at": mission.created_at.isoformat() if mission.created_at else None,
        "updated_at": mission.updated_at.isoformat() if mission.updated_at else None,
    }
