import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.agents.base_agent import BaseAgent
from app.models.lead_intelligence import CompanyIntelligence, LeadActivity
from app.models.vp_sales import ResearchResult
from app.services.research.search_service import search_web_general, _scrape_html, _extract_text
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


class CompanyIntelligenceAgent(BaseAgent):
    """Analyzes discovered companies to collect rich intelligence.

    Collects: description, services, size, tech stack, social profiles,
    location, business model.
    Generates: Company Intelligence Report.
    """

    agent_type = "company_intelligence"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Gathering company intelligence")
        steps = plan.get("steps", [{"name": "analyze_company", "description": "Analyze company data"}])
        all_reports = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_reports.extend(step_result.get("reports", []))
            recommendations.extend(step_result.get("recommendations", []))

        confidence = min(1.0, len(all_reports) * 0.15 or 0.3)
        return {
            "work_completed": f"Generated {len(all_reports)} company intelligence reports",
            "findings": all_reports,
            "confidence": confidence,
            "risks": ["Website may be unavailable or blocked"] if not all_reports else [],
            "recommendations": recommendations or ["Verify company details manually for high-value targets"],
            "next_action": "find_decision_makers" if all_reports else "refine_company_search",
        }

    async def _execute_step(self, step: dict) -> dict:
        description = step.get("description", "")
        target_company = step.get("target", description)

        try:
            results = await search_web_general(f"{target_company} company profile about", num_results=5)
            for r in results:
                if r.get("link"):
                    html = await _scrape_html(r["link"])
                    if html:
                        text = _extract_text(html)[:3000]
                        report = await self._generate_intelligence_report(target_company, text, r["link"])
                        if report:
                            return {"reports": [report], "recommendations": ["Cross-reference with LinkedIn profile"]}
        except Exception as e:
            logger.warning("Company intelligence step failed: %s", e)

        return {"reports": [self._basic_report(target_company)], "recommendations": ["Enable more search sources"]}

    async def _generate_intelligence_report(self, company: str, page_text: str, source_url: str) -> Optional[dict]:
        try:
            prompt = (
                f"Extract company intelligence from this text about {company}.\n\n"
                f"Text: {page_text[:2000]}\n\n"
                f"Return ONLY valid JSON with: company_name, description, services, industry, "
                f"sub_industry, company_size, estimated_revenue, technology_stack (array), "
                f"social_profiles (object), location, business_model, founded_year, confidence (0-1)."
            )
            result = await generate_text("", prompt)
            report = json.loads(result.strip())
            report["source_url"] = source_url
            return report
        except Exception:
            return None

    def _basic_report(self, company: str) -> dict:
        return {
            "company_name": company,
            "description": "",
            "services": "",
            "industry": "",
            "sub_industry": "",
            "company_size": "Unknown",
            "estimated_revenue": "Unknown",
            "technology_stack": [],
            "social_profiles": {},
            "location": "",
            "business_model": "Unknown",
            "founded_year": "",
            "source_url": "",
            "confidence": 0.2,
        }

    async def save_intelligence(self, company_name: str, report: dict) -> Optional[str]:
        ci = CompanyIntelligence(
            org_id=self.org_id,
            company_name=company_name,
            website=report.get("source_url", ""),
            description=report.get("description", ""),
            services=report.get("services", ""),
            industry=report.get("industry", ""),
            sub_industry=report.get("sub_industry", ""),
            company_size=report.get("company_size", ""),
            estimated_revenue=report.get("estimated_revenue", ""),
            technology_stack=report.get("technology_stack", []),
            social_profiles=report.get("social_profiles", {}),
            location=report.get("location", ""),
            business_model=report.get("business_model", ""),
            founded_year=report.get("founded_year", ""),
            source_url=report.get("source_url", ""),
            confidence=report.get("confidence", 0.0),
            raw_data=report,
        )
        self.db.add(ci)
        await self.db.flush()
        return ci.id
