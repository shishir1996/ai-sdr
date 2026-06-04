import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vp_orchestration import MissionTask, AgentMemory
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all intelligent agents.

    Every agent has its own brain — independent reasoning, planning,
    execution, memory, and reporting capability.
    """

    agent_type: str = "base"
    system_prompt: str = "You are an AI sales agent."

    def __init__(self, db: AsyncSession, org_id: str):
        self.db = db
        self.org_id = org_id
        self.agent_id: Optional[str] = None
        self.reasoning_log: list[str] = []

    async def think(self, prompt: str) -> str:
        """Use AI to think, with rule-based fallback."""
        try:
            full_prompt = f"{self.system_prompt}\n\n{prompt}"
            return await generate_text("", full_prompt)
        except Exception:
            return ""

    async def log_reasoning(self, step: str, detail: str = ""):
        self.reasoning_log.append(f"[{step}] {detail}")
        logger.info("[%s] %s: %s", self.agent_type, step, detail[:150])

    async def store_memory(self, memory_type: str, content: dict):
        mem = AgentMemory(
            org_id=self.org_id,
            agent_type=self.agent_type,
            agent_id=self.agent_id,
            memory_type=memory_type,
            content=content,
        )
        self.db.add(mem)
        await self.db.flush()

    async def recall_memories(self, memory_type: str, limit: int = 5) -> list[dict]:
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

    async def understand_mission(self, objective: str) -> dict:
        await self.log_reasoning("mission_analysis", f"Analyzing: {objective[:100]}...")
        prompt = (
            f"As a {self.agent_type} agent, analyze this mission:\n{objective}\n\n"
            f"Return ONLY JSON with:\n"
            f"- understanding: your interpretation\n"
            f"- approach: how you will execute\n"
            f"- steps: [array of step objects with name and description]\n"
            f"- success_criteria: what success looks like\n"
            f"- risks: potential issues"
        )
        result = await self.think(prompt)
        try:
            plan = json.loads(result)
        except Exception:
            plan = {
                "understanding": objective[:100],
                "approach": "Direct execution",
                "steps": [{"name": "execute", "description": f"Perform {self.agent_type} work"}],
                "success_criteria": "Mission completed",
                "risks": [],
            }
        await self.store_memory("plan", plan)
        return plan

    async def generate_report(self, task: MissionTask, findings: dict) -> dict:
        report = {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "task_objective": task.objective,
            "work_completed": findings.get("work_completed", ""),
            "findings": findings.get("findings", []),
            "confidence": findings.get("confidence", 0.5),
            "risks": findings.get("risks", []),
            "recommendations": findings.get("recommendations", []),
            "next_action": findings.get("next_action", ""),
            "reasoning": self.reasoning_log,
        }
        task.report = report
        task.confidence_score = report["confidence"]
        task.status = "completed"
        await self.db.flush()
        await self.store_memory("report", report)
        return report

    async def run(self, task: MissionTask) -> dict:
        await self.log_reasoning("task_start", f"Starting: {task.objective[:80]}...")
        task.status = "in_progress"
        task.agent_id = self.agent_id or task.id
        await self.db.flush()

        plan = await self.understand_mission(task.objective)
        task.execution_plan = plan
        await self.db.flush()

        findings = await self.execute(plan)
        report = await self.generate_report(task, findings)
        return report

    async def execute(self, plan: dict) -> dict:
        raise NotImplementedError("Subclasses implement execute()")
