import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.services.ai.provider import generate_text
from app.models.vp_sales import VPActionLog

logger = logging.getLogger(__name__)


class OutreachAgent(BaseAgent):
    """Intelligent outreach/sales agent.

    Creates messaging, handles objections, plans followups.
    """

    agent_type = "outreach"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Beginning outreach execution")

        steps = plan.get("steps", [{"name": "create_messaging", "description": "Create outreach messages"}])
        all_messages = []
        recommendations = []

        for step in steps:
            step_name = step.get("name", "message")
            await self._log_reasoning("step", f"Executing step: {step_name}")

            step_result = await self._execute_step(step)
            all_messages.extend(step_result.get("messages", []))
            recommendations.extend(step_result.get("recommendations", []))

        return {
            "work_completed": f"Created {len(all_messages)} message variants",
            "findings": all_messages,
            "confidence": 0.7 if all_messages else 0.3,
            "risks": ["No AI API key for personalized messages"] if not all_messages else [],
            "recommendations": recommendations or ["Review and approve messages before sending"],
            "next_action": "review_messages",
        }

    async def _execute_step(self, step: dict) -> dict:
        step_name = step.get("name", "message").lower()
        description = step.get("description", "")

        if "message" in step_name or "email" in step_name or "sequence" in step_name:
            messages = self._generate_messages(description)
            return {"messages": messages, "recommendations": ["Personalize with lead details before sending"]}

        if "objection" in step_name:
            return self._generate_objection_handling(description)

        if "followup" in step_name:
            return self._generate_followup_plan(description)

        if "campaign" in step_name:
            return self._generate_campaign_plan(description)

        return {"messages": [], "recommendations": ["Define outreach objective clearly"]}

    def _generate_messages(self, context: str) -> list[dict]:
        return [
            {
                "type": "email",
                "purpose": "initial_outreach",
                "subject": f"Quick question about {context[:30]}",
                "body_preview": f"Hi {{first_name}}, I noticed your work at {{company_name}}...",
                "suggested_channel": "email",
            },
            {
                "type": "email",
                "purpose": "follow_up_day_3",
                "subject": "Following up",
                "body_preview": "Hi {{first_name}}, just following up on my previous message...",
                "suggested_channel": "email",
            },
            {
                "type": "call",
                "purpose": "call_script_day_7",
                "script_preview": "Hi {{first_name}}, this is {{sdr_name}}...",
                "suggested_channel": "call",
            },
        ]

    def _generate_objection_handling(self, context: str) -> dict:
        return {
            "objections": [
                {"objection": "Not interested", "response": "I understand. Would you be open to a brief 5-min chat?"},
                {"objection": "No budget", "response": "What budget range would work for you?"},
                {"objection": "Happy with current solution", "response": "What do you like about your current setup?"},
            ],
            "recommendations": ["Train SDR on objection responses before campaign launch"],
        }

    def _generate_followup_plan(self, context: str) -> dict:
        return {
            "plan": [
                {"day": 1, "action": "Initial email", "channel": "email"},
                {"day": 3, "action": "Follow-up email with value prop", "channel": "email"},
                {"day": 7, "action": "Call with personalized script", "channel": "call"},
                {"day": 14, "action": "Final break-up email", "channel": "email"},
            ],
            "recommendations": ["Adjust timing based on lead engagement"],
        }

    def _generate_campaign_plan(self, context: str) -> dict:
        return {
            "campaign_steps": [
                {"step": 1, "channel": "email", "delay": 0, "purpose": "Introduction"},
                {"step": 2, "channel": "email", "delay": 3, "purpose": "Value proposition"},
                {"step": 3, "channel": "call", "delay": 7, "purpose": "Qualification call"},
            ],
            "recommendations": ["A/B test subject lines", "Track open and reply rates"],
        }
