import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.models.lead_intelligence import DecisionMaker, LeadActivity
from app.services.research.search_service import search_web_general, _scrape_html, _extract_text
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)

DECISION_MAKER_ROLES = [
    "founder", "ceo", "cfo", "cto", "coo", "owner", "president",
    "vp sales", "vp marketing", "vp engineering", "vp product",
    "director of sales", "director of marketing", "head of sales",
    "chief revenue officer", "chief marketing officer",
]


class DecisionMakerAgent(BaseAgent):
    """Identifies relevant decision makers at target companies.

    Finds: Founder, CEO, Owner, Director, VP Sales/Marketing, CTO, COO.
    Sources: team pages, about pages, press releases, LinkedIn.
    """

    agent_type = "decision_maker"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Identifying decision makers")
        steps = plan.get("steps", [{"name": "find_decision_makers", "description": "Find decision makers"}])
        all_found = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_found.extend(step_result.get("decision_makers", []))
            recommendations.extend(step_result.get("recommendations", []))

        confidence = min(1.0, len(all_found) * 0.2)
        return {
            "work_completed": f"Identified {len(all_found)} decision makers",
            "findings": all_found,
            "confidence": confidence,
            "risks": ["Decision maker info may be outdated"] if not all_found else [],
            "recommendations": recommendations or ["Cross-check with LinkedIn for accuracy"],
            "next_action": "discover_contacts" if all_found else "search_team_page",
        }

    async def _execute_step(self, step: dict) -> dict:
        description = step.get("description", "")
        company = step.get("company", description)

        results = []

        queries = [
            f"{company} founder CEO",
            f"{company} leadership team",
            f"{company} about us team",
            f"{company} management",
        ]
        for q in queries[:3]:
            try:
                search_results = await search_web_general(q, num_results=5)
                for sr in search_results:
                    if sr.get("link"):
                        html = await _scrape_html(sr["link"])
                        if html:
                            text = _extract_text(html)[:2000]
                            found = await self._extract_decision_makers(company, text, sr["link"])
                            results.extend(found)
            except Exception as e:
                logger.warning("Decision maker search failed: %s", e)

        if not results:
            for role in DECISION_MAKER_ROLES[:5]:
                results.append({
                    "full_name": f"Unknown ({role})",
                    "title": role.title(),
                    "role_category": role,
                    "company": company,
                    "confidence": 0.3,
                    "is_primary": role in ("founder", "ceo", "owner"),
                })

        return {
            "decision_makers": results[:10],
            "recommendations": ["Verify titles via LinkedIn before outreach"],
        }

    async def _extract_decision_makers(self, company: str, text: str, source_url: str) -> list[dict]:
        found = []
        try:
            prompt = (
                f"Extract decision makers from this text about {company}.\n"
                f"Look for: founders, CEOs, owners, directors, VPs, CTOs, COOs.\n\n"
                f"Text: {text[:1500]}\n\n"
                f"Return ONLY JSON array with: full_name, title, role_category, confidence (0-1), "
                f"is_primary_decision_maker (bool).\n"
                f"Example: [{{\"full_name\":\"John Doe\",\"title\":\"CEO\",\"role_category\":\"ceo\",\"confidence\":0.9,\"is_primary_decision_maker\":true}}]"
            )
            result = await generate_text("", prompt)
            parsed = json.loads(result.strip())
            if isinstance(parsed, list):
                for p in parsed:
                    p["company"] = company
                    p["source_url"] = source_url
                found.extend(parsed)
        except Exception:
            pass
        return found
