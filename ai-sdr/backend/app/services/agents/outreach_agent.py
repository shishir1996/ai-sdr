import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class OutreachAgent(BaseAgent):
    """SDR Agent — executes outreach campaigns.

    Brain: Plans outreach sequence, creates messaging,
    handles objections, plans followups, reports to VP.
    """

    agent_type = "sdr"
    system_prompt = (
        "You are a Senior SDR with 8+ years in B2B outbound sales. "
        "You excel at creating personalized outreach that gets replies. "
        "You plan multi-channel sequences and adapt based on response."
    )

    async def execute(self, plan: dict) -> dict:
        await self.log_reasoning("execution_start", "Planning outreach campaign")

        steps = plan.get("steps", [{"name": "plan", "description": "Plan outreach"}])
        campaign_plan = None
        messages = []
        recommendations = []

        for step in steps:
            name = step.get("name", "").lower()
            if "plan" in name or "campaign" in name:
                campaign_plan = self._build_campaign_plan(step.get("description", ""))
            elif "message" in name or "email" in name:
                messages = self._generate_messages(step.get("description", ""))
            elif "objection" in name:
                recommendations.append("Train on objection handling: budget, timing, authority")
            elif "follow" in name:
                recommendations.append("Follow up day 3 and day 7 if no reply")

        return {
            "work_completed": "Campaign planned with multi-step sequence",
            "findings": {
                "campaign": campaign_plan or self._default_campaign(),
                "messages": messages or self._default_messages(),
            },
            "confidence": 0.8 if campaign_plan else 0.5,
            "risks": ["No AI API key — using template messages"] if not messages else [],
            "recommendations": recommendations or ["Launch campaign when VP approves"],
            "next_action": "launch_campaign",
        }

    def _build_campaign_plan(self, context: str) -> dict:
        return {
            "name": f"Outreach Campaign",
            "steps": [
                {"day": 0, "channel": "email", "action": "Initial outreach"},
                {"day": 3, "channel": "email", "action": "Follow-up with value prop"},
                {"day": 7, "channel": "call", "action": "Phone call follow-up"},
                {"day": 14, "channel": "email", "action": "Final break-up email"},
            ],
            "strategy": "Multi-touch, multi-channel sequence with increasing urgency",
        }

    def _default_campaign(self) -> dict:
        return {
            "name": "Standard 3-Step Campaign",
            "steps": [
                {"step": 1, "channel": "email", "delay_days": 0},
                {"step": 2, "channel": "email", "delay_days": 3},
                {"step": 3, "channel": "call", "delay_days": 7},
            ],
        }

    def _generate_messages(self, context: str) -> list[dict]:
        return [
            {
                "type": "email",
                "subject": "Quick question",
                "body": "Hi {{first_name}}, I noticed {{company_name}}...",
            },
            {
                "type": "email",
                "subject": "Following up",
                "body": "Hi {{first_name}}, following up on my previous email...",
            },
        ]

    def _default_messages(self) -> list[dict]:
        return [
            {"step": 1, "channel": "email", "template": "Hi {{first_name}}, I wanted to reach out about..."},
            {"step": 2, "channel": "email", "template": "Hi {{first_name}}, following up on my message from last week..."},
            {"step": 3, "channel": "call", "script": "Hi {{first_name}}, this is {{sdr_name}}..."},
        ]
