import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CallingAgent(BaseAgent):
    """Intelligent calling agent for phone outreach.

    Handles call flow, qualification, information gathering.
    """

    agent_type = "calling"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Beginning call campaign planning")

        steps = plan.get("steps", [{"name": "create_script", "description": "Create call scripts"}])
        all_scripts = []
        qualification_criteria = []
        recommendations = []

        for step in steps:
            step_name = step.get("name", "script")
            await self._log_reasoning("step", f"Executing: {step_name}")
            step_result = await self._execute_step(step)
            all_scripts.extend(step_result.get("scripts", []))
            qualification_criteria.extend(step_result.get("qualification_criteria", []))
            recommendations.extend(step_result.get("recommendations", []))

        return {
            "work_completed": f"Created {len(all_scripts)} call scripts with {len(qualification_criteria)} qualification criteria",
            "findings": all_scripts + [{"qualification_criteria": qualification_criteria}],
            "confidence": 0.6,
            "risks": ["Phone numbers may be outdated", "Requires Twilio/VAPI integration"],
            "recommendations": recommendations or ["Test call scripts before deploying"],
            "next_action": "review_call_scripts",
        }

    async def _execute_step(self, step: dict) -> dict:
        step_name = step.get("name", "script").lower()
        description = step.get("description", "")

        if "script" in step_name or "voice" in step_name:
            return {
                "scripts": [
                    {
                        "type": "initial_call",
                        "duration": "2-3 minutes",
                        "flow": [
                            "Introduction: Hi {{first_name}}, this is {{sdr_name}} from {{company}}",
                            "Permission: Got a quick 2 minutes?",
                            "Value prop: I help {{industry}} businesses with {{benefit}}",
                            "Question: How is {{company}} currently handling {{pain_point}}?",
                            "Close: Would you be open to a quick demo?",
                        ],
                        "suggested_time": "10am-11am or 2pm-4pm local time",
                    },
                    {
                        "type": "follow_up_call",
                        "flow": [
                            "Reference: I emailed you last week about {{topic}}",
                            "Question: Did you get a chance to review?",
                            "Next step: Can I send you more info?",
                        ],
                    },
                ],
                "recommendations": ["Keep initial calls under 3 minutes", "Always ask for permission first"],
            }

        if "qualify" in step_name or "qualification" in step_name:
            return {
                "qualification_criteria": [
                    {"question": "What's your current role?", "purpose": "Verify decision maker"},
                    {"question": "What tools are you currently using?", "purpose": "Understand tech stack"},
                    {"question": "What budget range are you looking at?", "purpose": "Qualify budget"},
                    {"question": "What's your timeline for a decision?", "purpose": "Qualify urgency"},
                ],
                "recommendations": ["Use BANT framework for qualification"],
            }

        if "schedule" in step_name or "meeting" in step_name:
            return {
                "scripts": [{
                    "type": "meeting_confirmation",
                    "flow": [
                        "Confirm time and date",
                        "Send calendar invite",
                        "Share agenda",
                    ],
                }],
                "recommendations": ["Use Calendly or Cal.com for self-scheduling"],
            }

        return {"scripts": [], "recommendations": ["Define calling objective"]}
