import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.models.lead_intelligence import EnrichmentProfile
from app.services.research.search_service import search_web_general, _scrape_html, _extract_text
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


class EnrichmentAgent(BaseAgent):
    """Adds business intelligence to leads.

    Collects: industry, sub-industry, company size, location,
    target market, services, technology stack, business model.
    """

    agent_type = "enrichment"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Enriching lead data")
        steps = plan.get("steps", [{"name": "enrich", "description": "Enrich with business intelligence"}])
        all_profiles = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_profiles.extend(step_result.get("profiles", []))
            recommendations.extend(step_result.get("recommendations", []))

        confidence = min(1.0, len(all_profiles) * 0.2)
        return {
            "work_completed": f"Enriched {len(all_profiles)} leads with business intelligence",
            "findings": all_profiles,
            "confidence": confidence,
            "risks": ["Enriched data may be approximate"],
            "recommendations": recommendations or ["Use enriched data for ICP matching and scoring"],
            "next_action": "detect_buying_signals" if all_profiles else "gather_more_data",
        }

    async def _execute_step(self, step: dict) -> dict:
        company = step.get("company", step.get("description", ""))
        website = step.get("website", "")
        text = ""

        if website:
            html = await _scrape_html(website)
            if html:
                text = _extract_text(html)

        if not text:
            try:
                results = await search_web_general(f"{company} company profile overview", num_results=3)
                for r in results:
                    if r.get("link"):
                        html = await _scrape_html(r["link"])
                        if html:
                            text += _extract_text(html)[:2000]
            except Exception as e:
                logger.warning("Enrichment search failed: %s", e)

        profile = await self._generate_enrichment(company, text[:3000]) if text else self._basic_profile(company)
        return {"profiles": [profile], "recommendations": ["Verify technology stack via BuiltWith or Wappalyzer"]}

    async def _generate_enrichment(self, company: str, text: str) -> dict:
        try:
            prompt = (
                f"Extract business intelligence about {company} from this text.\n\n"
                f"Text: {text}\n\n"
                f"Return ONLY valid JSON with: industry, sub_industry, company_size, location, "
                f"target_market, services, technology_stack (array), business_model, "
                f"funding_stage, social_links (object), confidence (0-1)."
            )
            result = await generate_text("", prompt)
            return json.loads(result.strip())
        except Exception:
            return self._basic_profile(company)

    def _basic_profile(self, company: str) -> dict:
        return {
            "industry": "", "sub_industry": "", "company_size": "Unknown",
            "location": "", "target_market": "", "services": "",
            "technology_stack": [], "business_model": "Unknown",
            "funding_stage": "Unknown", "social_links": {}, "confidence": 0.2,
        }
