import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.services.research.search_service import search_all_enabled
from app.models.vp_sales import ResearchResult
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Research Agent — finds real business owners with contact info.

    Brain: uses AI to understand the ICP, determine the best search strategy,
    generates queries, executes searches, scores data quality,
    validates findings, saves to CRM, reports to VP.
    """

    agent_type = "research"
    progress_session: Optional[str] = None

    system_prompt = (
        "You are a Senior Research Agent with 10+ years in B2B lead research. "
        "You specialize in finding real business owners and decision makers "
        "with accurate contact information from public sources."
    )

    async def execute(self, plan: dict) -> dict:
        await self.log_reasoning("execution_start", "Planning research strategy")

        mission_context = plan.get("understanding", "") or plan.get("approach", "")

        # AI decides the best search approach based on mission
        queries = await self._determine_search_strategy(mission_context)
        await self.log_reasoning("search_strategy", f"AI decided {len(queries)} search directions")

        all_findings = []
        for query in queries[:5]:
            try:
                results = await search_all_enabled(
                    self.db, self.org_id, query, num_results=10,
                    progress_session=self.progress_session,
                )
                for r in results:
                    scored = self._score_finding(r)
                    all_findings.append(scored)
                await self.log_reasoning("query_executed", f"'{query[:50]}...' → {len(results)} results")
            except Exception as e:
                logger.warning("Query failed '%s': %s", query[:40], e)

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

    async def _determine_search_strategy(self, context: str) -> list[str]:
        """AI decides the best search queries based on mission context."""
        prompt = (
            f"You are a lead research strategist. Given this mission context:\n{context}\n\n"
            f"Generate 5 targeted search queries to find real business owners and decision makers "
            f"with emails and phone numbers.\n\n"
            f"Use strategic variations:\n"
            f"- Google search queries (e.g., 'plumbers in chicago email')\n"
            f"- Industry-specific terms\n"
            f"- Location-based searches\n"
            f"- Niche directories\n"
            f"- Phrases that surface contact pages\n\n"
            f"Return ONLY a JSON array of 5 search query strings."
        )
        try:
            result = await self.think(prompt)
            queries = json.loads(result)
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:10]
        except Exception:
            logger.info("AI search strategy failed, using fallback queries")

        biz = ""
        country = "USA"
        import re
        lines = context.split('\n')
        for line in lines:
            if 'find' in line.lower() and 'owner' in line.lower():
                parts = line.replace('Find real', '').replace('find real', '').replace('Find', '').replace('find', '').strip()
                m = re.match(r'(.+?)\s+owners?\s+in\s+([A-Za-z\s]+)', parts)
                if m:
                    biz = m.group(1).strip().rstrip(',').strip()
                    country = m.group(2).strip().rstrip(',').strip()
                break
        if not biz:
            biz = context[:60].replace('Find real', '').replace('find', '').strip()

        biz_terms = [b.strip() for b in biz.replace(',', ' ').split() if b.strip()]
        if not biz_terms:
            biz_terms = ['business']

        return [
            f"{' '.join(biz_terms[:3])} in {country} owner email contact",
            f"{' '.join(biz_terms[:3])} {country} business directory",
            f"{' '.join(biz_terms[:3])} {country} company contact information",
            f"{' '.join(biz_terms[:3])} near me phone email",
            f"{' '.join(biz_terms[:2])} {country} contact page",
        ]

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
            company = f.get("company_name") or f.get("title", "")
            contact_name = f.get("contact_name", "")
            if not contact_name:
                contact_name = company

            rr = ResearchResult(
                org_id=self.org_id,
                source=f.get("_source", "web_research"),
                source_url=f.get("link", ""),
                title=f.get("title", ""),
                snippet=f.get("snippet", ""),
                company_name=company,
                contact_name=contact_name,
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
                raw_data={**f, "search_rank": f.get("search_rank", 0)},
                status="new",
            )
            self.db.add(rr)
            saved += 1
        await self.db.flush()
        return saved
