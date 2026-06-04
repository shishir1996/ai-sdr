import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.services.research.search_service import search_all_enabled
from app.models.vp_sales import ResearchResult

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Research Agent — finds real business owners with contact info.

    Brain: understands ICP, plans search queries, executes searches,
    scores data quality, validates findings, reports to VP.
    """

    agent_type = "research"
    system_prompt = (
        "You are a Senior Research Agent with 10+ years in B2B lead research. "
        "You specialize in finding real business owners and decision makers "
        "with accurate contact information from public sources."
    )

    async def execute(self, plan: dict) -> dict:
        await self.log_reasoning("execution_start", "Beginning research")

        steps = plan.get("steps", [{"name": "search", "description": "Find prospects"}])

        # Generate search queries based on the mission objective
        queries = await self._generate_queries(plan.get("understanding", ""))
        await self.log_reasoning("queries_generated", f"{len(queries)} queries")

        all_findings = []
        for query in queries[:5]:
            try:
                results = await search_all_enabled(self.db, self.org_id, query, num_results=10)
                for r in results:
                    scored = self._score_finding(r)
                    all_findings.append(scored)
                await self.log_reasoning("query_executed", f"'{query[:50]}...' → {len(results)} results")
            except Exception as e:
                logger.warning("Query failed '%s': %s", query[:40], e)

        # Deduplicate by email/company
        seen = set()
        unique = []
        for f in all_findings:
            key = f.get("contact_email", "") or f.get("company_name", "") or f.get("link", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(f)

        emails = len([f for f in unique if f.get("contact_email")])
        phones = len([f for f in unique if f.get("contact_phone")])
        quality = min(1.0, (emails + phones) / max(len(unique), 1) * 0.5 + 0.3)

        await self.log_reasoning("quality_assessment",
                                 f"{len(unique)} unique leads, {emails} emails, {phones} phones")

        return {
            "work_completed": f"Searched {len(queries)} queries, found {len(unique)} leads",
            "findings": unique[:30],
            "confidence": quality,
            "risks": ["Some emails may be generic"] if not emails else [],
            "recommendations": ["Convert high-confidence leads to CRM"] if unique else ["Broaden search queries"],
            "next_action": "convert_to_leads" if unique else "retry",
        }

    async def _generate_queries(self, context: str) -> list[str]:
        prompt = (
            f"Generate 5 targeted search queries to find real business owners with contact info. "
            f"Context: {context}\n"
            f"Examples: 'restaurant owner new york email contact', 'salon owner los angeles phone'\n"
            f"Return ONLY a JSON array of strings."
        )
        try:
            result = await self.think(prompt)
            queries = json.loads(result)
            if isinstance(queries, list):
                return queries[:5]
        except Exception:
            pass
        return [f"{context} owner email", f"{context} contact", f"{context} business directory"]

    def _score_finding(self, result: dict) -> dict:
        score = 0
        if result.get("contact_email"): score += 30
        if result.get("contact_phone"): score += 25
        if result.get("contact_name"): score += 20
        if result.get("company_name"): score += 15
        if result.get("source_url"): score += 10
        result["quality"] = min(100, score)
        result["_agent"] = "research"
        return result

    async def save_to_crm(self, findings: list[dict]) -> int:
        saved = 0
        for f in findings:
            rr = ResearchResult(
                org_id=self.org_id,
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
            self.db.add(rr)
            saved += 1
        await self.db.flush()
        return saved
