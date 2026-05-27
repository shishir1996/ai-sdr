import json
import logging
from typing import Optional

from app.services.ai.model_client import generate_text
from app.models.lead import Lead

logger = logging.getLogger(__name__)


async def analyze_lead_deeply(lead: Lead, ai_key: Optional[str] = None) -> dict:
    """Deeply analyzes a lead using available data and AI reasoning.
    Returns a rich profile with pain points, challenges, interests, and personalization hooks."""
    profile = {}
    if lead.company:
        profile["company"] = lead.company
        company_analysis = await _analyze_company(lead.company, lead.industry or "", ai_key)
        profile.update(company_analysis)
    if lead.linkedin_url:
        linkedin_analysis = await _analyze_linkedin_profile(
            lead.linkedin_url, lead.first_name or "", lead.last_name or "", lead.title or "", ai_key
        )
        profile.update(linkedin_analysis)
    if lead.industry:
        profile["industry_insights"] = await _get_industry_insights(lead.industry, ai_key)
    profile["personalization_hooks"] = _build_personalization_hooks(lead, profile)
    return profile


async def _analyze_company(company_name: str, industry: str, ai_key: Optional[str] = None) -> dict:
    system_prompt = """You are a business research analyst. Analyze a company and return JSON with:
- business_type: what kind of business
- likely_pain_points: array of 3-5 likely pain points this company faces
- business_challenges: array of 2-4 current business challenges
- growth_indicators: array of 2-3 potential growth areas
- value_proposition_angle: a 1-sentence angle for outreach
- decision_makers: array of likely decision-maker titles
- company_culture_tone: how to approach this type of company (formal/casual/innovative/traditional)
Return only valid JSON."""
    user_prompt = f"Analyze company: {company_name}, Industry: {industry}"
    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=1024, temperature=0.3, api_key=ai_key)
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Company analysis failed for {company_name}: {e}")
        return {}


async def _analyze_linkedin_profile(
    linkedin_url: str, first_name: str, last_name: str, title: str,
    ai_key: Optional[str] = None,
) -> dict:
    name = f"{first_name} {last_name}".strip()
    system_prompt = """You are a LinkedIn profile analyst. Based on the available info, infer likely profile details.
Return JSON with:
- likely_interests: array of 3-5 professional interests
- pain_points_role: array of 2-4 likely pain points for someone in this role
- communication_style: how this person would likely prefer to be communicated with
- personalization_hook: a 1-sentence personalized hook for this person
- engagement_strategy: how to best engage this person (thoughtful/straightforward/value-first)
Return only valid JSON."""
    user_prompt = f"Analyze: {name}, Title: {title}, LinkedIn: {linkedin_url}"
    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=800, temperature=0.4, api_key=ai_key)
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"LinkedIn analysis failed for {name}: {e}")
        return {}


async def _get_industry_insights(industry: str, ai_key: Optional[str] = None) -> dict:
    system_prompt = """You are an industry analyst. Return JSON with industry-specific insights:
- common_challenges: array of 3-5 common challenges in this industry
- sales_approach: 1-2 sentence best sales approach for this industry
- keywords: array of 5-7 keywords that resonate in this industry
- objection_handling: 1-2 sentence approach for handling objections
Return only valid JSON."""
    user_prompt = f"Industry: {industry}"
    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=600, temperature=0.3, api_key=ai_key)
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Industry insights failed for {industry}: {e}")
        return {}


def _build_personalization_hooks(lead: Lead, profile: dict) -> list:
    hooks = []
    name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
    if lead.company:
        hooks.append(f"Company-specific: {lead.company}")
    if lead.title:
        hooks.append(f"Role-specific: {lead.title}")
    if lead.location:
        hooks.append(f"Location-specific: {lead.location}")
    if lead.industry:
        hooks.append(f"Industry-specific: {lead.industry}")
    if profile.get("likely_pain_points"):
        hooks.append(f"Pain point: {profile['likely_pain_points'][0]}")
    if profile.get("personalization_hook"):
        hooks.append(f"Hook: {profile['personalization_hook']}")
    if profile.get("value_proposition_angle"):
        hooks.append(f"Angle: {profile['value_proposition_angle']}")
    return hooks
