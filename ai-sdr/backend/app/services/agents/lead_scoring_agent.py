import logging
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.models.lead import Lead
from app.models.lead_intelligence import LeadScore, CompanyIntelligence, BuyingSignal, EnrichmentProfile
from app.models.vp_sales import ResearchResult
from sqlalchemy import select

logger = logging.getLogger(__name__)


class LeadScoringAgent(BaseAgent):
    """Calculates comprehensive lead quality scores.

    Scores: Company Score, Contact Score, ICP Match Score,
    Buying Signal Score, Data Quality Score, Overall Score.
    """

    agent_type = "lead_scoring"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Scoring leads")
        steps = plan.get("steps", [{"name": "score", "description": "Score lead quality"}])
        all_scores = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_scores.extend(step_result.get("scores", []))
            recommendations.extend(step_result.get("recommendations", []))

        avg_score = 0.0
        if all_scores:
            avg_score = sum(s.get("overall_score", 0) for s in all_scores) / len(all_scores)

        return {
            "work_completed": f"Scored {len(all_scores)} leads (avg: {avg_score:.1f}/100)",
            "findings": all_scores,
            "confidence": 0.85 if all_scores else 0.0,
            "risks": ["Scores based on available data quality"],
            "recommendations": recommendations or ["Score all leads before SDR assignment"],
            "next_action": "assign_sdr" if avg_score >= 50 else "collect_more_data",
        }

    async def _execute_step(self, step: dict) -> dict:
        lead_id = step.get("lead_id", "")
        company = step.get("company", "")
        scores = []

        if lead_id:
            score = await self._score_single_lead(lead_id)
            if score:
                scores.append(score)
        elif company:
            scores.append(self._score_from_data(company, step))

        return {"scores": scores, "recommendations": ["Score periodically as new data arrives"]}

    async def _score_single_lead(self, lead_id: str) -> Optional[dict]:
        lead = await self.db.get(Lead, lead_id)
        if not lead:
            return None

        ci_result = await self.db.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.lead_id == lead_id)
        )
        ci = ci_result.scalar_one_or_none()

        bs_result = await self.db.execute(
            select(BuyingSignal).where(BuyingSignal.lead_id == lead_id)
        )
        signals = list(bs_result.scalars().all())

        company_score = self._calc_company_score(ci)
        contact_score = self._calc_contact_score(lead)
        icp_score = self._calc_icp_score(lead, ci)
        buying_signal_score = self._calc_buying_signal_score(signals)
        data_quality_score = self._calc_data_quality(lead, ci)

        overall = round(
            company_score * 0.25 +
            contact_score * 0.25 +
            icp_score * 0.25 +
            buying_signal_score * 0.15 +
            data_quality_score * 0.10
        )

        score_record = LeadScore(
            org_id=self.org_id,
            lead_id=lead_id,
            company_score=company_score,
            contact_score=contact_score,
            icp_match_score=icp_score,
            buying_signal_score=buying_signal_score,
            data_quality_score=data_quality_score,
            overall_score=overall,
            scoring_breakdown={
                "company_score": company_score,
                "contact_score": contact_score,
                "icp_score": icp_score,
                "buying_signal_score": buying_signal_score,
                "data_quality_score": data_quality_score,
            },
        )
        self.db.add(score_record)
        await self.db.flush()

        lead.score = overall
        await self.db.flush()

        return {
            "lead_id": lead_id,
            "company_name": lead.company,
            "company_score": company_score,
            "contact_score": contact_score,
            "icp_match_score": icp_score,
            "buying_signal_score": buying_signal_score,
            "data_quality_score": data_quality_score,
            "overall_score": overall,
        }

    def _calc_company_score(self, ci: Optional[CompanyIntelligence]) -> float:
        if not ci:
            return 20.0
        score = 0
        if ci.description: score += 15
        if ci.industry: score += 15
        if ci.company_size and ci.company_size != "Unknown": score += 15
        if ci.technology_stack: score += 15
        if ci.location: score += 10
        if ci.social_profiles: score += 10
        if ci.business_model and ci.business_model != "Unknown": score += 10
        if ci.estimated_revenue and ci.estimated_revenue != "Unknown": score += 10
        return min(100, score)

    def _calc_contact_score(self, lead: Lead) -> float:
        score = 0
        if lead.first_name: score += 15
        if lead.last_name: score += 15
        if lead.email: score += 25
        if lead.phone: score += 20
        if lead.title: score += 15
        if lead.linkedin_url: score += 10
        return min(100, score)

    def _calc_icp_score(self, lead: Lead, ci: Optional[CompanyIntelligence]) -> float:
        score = 50
        if lead.industry: score += 10
        if lead.country: score += 10
        if ci and ci.company_size and ci.company_size != "Unknown": score += 10
        if lead.title and any(t in (lead.title or "").lower() for t in
                              ["founder", "ceo", "owner", "director", "vp", "president"]):
            score += 20
        return min(100, score)

    def _calc_buying_signal_score(self, signals: list) -> float:
        if not signals:
            return 10.0
        strong = [s for s in signals if s.signal_strength >= 0.7]
        if strong:
            return min(100, len(strong) * 30 + 20)
        return min(100, len(signals) * 15 + 10)

    def _calc_data_quality(self, lead: Lead, ci: Optional[CompanyIntelligence]) -> float:
        score = 0
        fields = 0
        for f in [lead.first_name, lead.last_name, lead.email, lead.phone,
                  lead.company, lead.title, lead.website, lead.industry]:
            if f: score += 12.5; fields += 1
        if ci and (ci.description or ci.technology_stack):
            score += 0
        return min(100, score)

    def _score_from_data(self, company: str, data: dict) -> dict:
        has_email = bool(data.get("email"))
        has_phone = bool(data.get("phone"))
        has_website = bool(data.get("website"))
        contact_score = (25 if has_email else 0) + (20 if has_phone else 0) + (15 if has_website else 0) + 15
        return {
            "company_name": company,
            "company_score": 30.0,
            "contact_score": min(100, contact_score),
            "icp_match_score": 50.0,
            "buying_signal_score": 10.0,
            "data_quality_score": min(100, contact_score),
            "overall_score": min(100, int(30 * 0.25 + min(100, contact_score) * 0.25 + 50 * 0.25 + 10 * 0.15 + min(100, contact_score) * 0.10)),
        }
