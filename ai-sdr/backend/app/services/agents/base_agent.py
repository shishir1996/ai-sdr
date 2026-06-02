import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vp_orchestration import MissionTask, AgentMemory
from app.models.vp_sales import VPActionLog
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all intelligent agents.

    Every agent has independent reasoning, planning, execution,
    and reporting capability.
    """

    agent_type: str = "base"

    def __init__(self, db: AsyncSession, org_id: str, agent_id: Optional[str] = None):
        self.db = db
        self.org_id = org_id
        self.agent_id = agent_id
        self.reasoning_log: list[str] = []

    async def _log_reasoning(self, step: str, detail: str = ""):
        entry = {"step": step, "detail": detail}
        self.reasoning_log.append(f"{step}: {detail}")
        logger.info("[%s] %s: %s", self.agent_type, step, detail[:200])
        return entry

    async def _store_memory(self, memory_type: str, content: dict):
        mem = AgentMemory(
            org_id=self.org_id,
            agent_type=self.agent_type,
            agent_id=self.agent_id,
            memory_type=memory_type,
            content=content,
        )
        self.db.add(mem)
        await self.db.flush()

    async def _recall_memory(self, memory_type: str, limit: int = 5) -> list[dict]:
        result = await self.db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.org_id == self.org_id,
                AgentMemory.agent_type == self.agent_type,
                AgentMemory.memory_type == memory_type,
            )
            .order_by(AgentMemory.created_at.desc())
            .limit(limit)
        )
        return [m.content for m in result.scalars().all()]

    async def understand_mission(self, objective: str, context: Optional[dict] = None) -> dict:
        await self._log_reasoning("mission_analysis", f"Analyzing mission: {objective[:120]}...")
        plan = await self._create_execution_plan(objective, context)
        await self._log_reasoning("plan_created", f"Plan: {json.dumps(plan)[:200]}")
        await self._store_memory("plan", plan)
        return plan

    async def _create_execution_plan(self, objective: str, context: Optional[dict] = None) -> dict:
        try:
            prompt = (
                f"You are a {self.agent_type} agent in a sales organization. "
                f"Your mission: {objective}\n\n"
                f"Create a detailed execution plan. Return ONLY valid JSON with:\n"
                f"- objective: re-stated objective\n"
                f"- approach: your approach strategy\n"
                f"- steps: [array of step objects with name and description]\n"
                f"- success_criteria: what constitutes success\n"
                f"- estimated_effort: low/medium/high\n"
            )
            result = await generate_text("", prompt)
            return json.loads(result.strip())
        except Exception:
            return {
                "objective": objective,
                "approach": "Direct execution",
                "steps": [{"name": "execute", "description": f"Perform {self.agent_type} research"}],
                "success_criteria": "Data collected",
                "estimated_effort": "medium",
            }

    async def generate_report(self, task: MissionTask, findings: dict) -> dict:
        report = {
            "task_objective": task.objective,
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "work_completed": findings.get("work_completed", ""),
            "findings": findings.get("findings", []),
            "confidence_score": findings.get("confidence", 0.5),
            "risks": findings.get("risks", []),
            "recommendations": findings.get("recommendations", []),
            "next_suggested_action": findings.get("next_action", ""),
            "reasoning_log": self.reasoning_log,
        }
        task.report = report
        task.confidence_score = report["confidence_score"]
        task.status = "completed"
        await self.db.flush()

        await self._store_memory("report", report)
        return report

    async def run(self, task: MissionTask) -> dict:
        await self._log_reasoning("task_started", f"Starting task {task.id[:8]}: {task.objective[:100]}")
        task.status = "in_progress"
        await self.db.flush()

        plan = await self.understand_mission(task.objective)
        task.execution_plan = plan
        await self.db.flush()

        findings = await self.execute_plan(plan)
        report = await self.generate_report(task, findings)

        await self._log_reasoning("task_completed",
                                  f"Confidence: {findings.get('confidence', 0.5)}, "
                                  f"Findings: {len(findings.get('findings', []))}")
        return report

    async def execute_plan(self, plan: dict) -> dict:
        raise NotImplementedError("Subclasses must implement execute_plan")
