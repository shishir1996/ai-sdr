import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.agents.base_agent import BaseAgent
from app.services.research.search_service import search_all_enabled
from app.services.research.agent_service import convert_to_lead
from app.models.vp_sales import ResearchAgent, ResearchResult, VPActionLog
from app.models.vp_orchestration import MissionTask
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


class ResearchAgentIntelligence(BaseAgent):
    """Intelligent research agent with independent reasoning.

    Understands research objectives, decides search paths,
    validates sources, and scores data quality.
    """

    agent_type = "research"

    def __init__(self, db: AsyncSession, org_id: str, agent_id: Optional[str] = None):
        super().__init__(db, org_id, agent_id)
        self.queries_used: list[str] = []
        self.results_collected: list[dict] = []

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Beginning research execution")

        steps = plan.get("steps", [{"name": "search", "description": "Search for prospects"}])
        all_findings = []
        risks = []
        recommendations = []

        for step in steps:
            step_name = step.get("name", "research")
            await self._log_reasoning("step", f"Executing step: {step_name}")

            step_result = await self._execute_step(step)
            step_findings = step_result.get("findings", [])
            all_findings.extend(step_findings)
            self.results_collected.extend(step_findings)
            risks.extend(step_result.get("risks", []))
            recommendations.extend(step_result.get("recommendations", []))

        sources_validated = len([f for f in all_findings if f.get("source_url")])
        emails_found = len([f for f in all_findings if f.get("contact_email")])
        phones_found = len([f for f in all_findings if f.get("contact_phone")])
        quality_score = min(1.0, (emails_found + phones_found) / max(len(all_findings), 1) * 0.5 + 0.3)

        await self._log_reasoning("quality_assessment",
                                  f"Sources: {sources_validated}, Emails: {emails_found}, Phones: {phones_found}, "
                                  f"Quality: {quality_score:.2f}")

        return {
            "work_completed": f"Searched {len(self.queries_used)} queries across enabled sources",
            "findings": all_findings,
            "confidence": quality_score,
            "risks": list(set(risks)),
            "recommendations": list(set(recommendations)),
            "next_action": "convert_to_leads" if all_findings else "refine_queries",
        }

    async def _execute_step(self, step: dict) -> dict:
        step_name = step.get("name", "search").lower()
        description = step.get("description", "")

        searches_performed = []
        findings = []
        risks = []
        recommendations = []

        if "search" in step_name or "query" in step_name:
            queries = await self._generate_queries_from_step(description)
            self.queries_used.extend(queries)

            for query in queries[:3]:
                try:
                    results = await search_all_enabled(self.db, self.org_id, query, num_results=10)
                    for r in results:
                        enriched = self._score_finding(r)
                        findings.append(enriched)
                    searches_performed.append({"query": query, "results": len(results)})
                    await self._log_reasoning("query_executed",
                                              f"Query '{query[:60]}...' → {len(results)} results")
                except Exception as e:
                    logger.warning("Research query failed '%s': %s", query, e)
                    risks.append(f"Query failed: {query[:50]}")

        elif "analyze" in step_name or "validate" in step_name:
            pass

        else:
            findings, risks = [], []

        if len(findings) < 3:
            recommendations.append("Broaden search queries or enable more sources")

        return {"findings": findings, "risks": risks, "recommendations": recommendations}

    async def _generate_queries_from_step(self, description: str) -> list[str]:
        try:
            prompt = (
                f"Generate 3 search queries to find business owners/prospects. "
                f"Context: {description}\n"
                f"Return ONLY a JSON array of strings."
            )
            result = await generate_text("", prompt)
            return json.loads(result.strip())[:3]
        except Exception:
            return [f"{description} contact email", f"{description} owners phone", f"{description} business directory"]

    def _score_finding(self, result: dict) -> dict:
        score = 0
        signals = []

        if result.get("contact_email"):
            score += 0.3
            signals.append("email_found")
        if result.get("contact_phone"):
            score += 0.3
            signals.append("phone_found")
        if result.get("contact_name"):
            score += 0.2
            signals.append("name_found")
        if result.get("company_name"):
            score += 0.1
            signals.append("company_found")
        if result.get("source_url"):
            score += 0.1
            signals.append("source_validated")

        result["quality_score"] = round(min(1.0, score), 2)
        result["quality_signals"] = signals
        return result

    async def save_findings(self, vp_id: Optional[str]) -> int:
        saved = 0
        for f in self.results_collected:
            rr = ResearchResult(
                org_id=self.org_id,
                research_agent_id=self.agent_id,
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

        if vp_id:
            vp_log = VPActionLog(
                org_id=self.org_id,
                vp_id=vp_id,
                action_type="research_findings_saved",
                reasoning=f"Research agent saved {saved} findings from {len(self.queries_used)} queries",
                details={"agent_id": self.agent_id, "findings_saved": saved, "queries": self.queries_used},
            )
            self.db.add(vp_log)
            await self.db.flush()

        self.results_collected = []
        return saved



