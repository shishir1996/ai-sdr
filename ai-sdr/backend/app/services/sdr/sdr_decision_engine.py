import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import SDRProfile, LeadState
from app.services.ai.model_client import generate_text
from app.services.sdr.sdr_country_adapter import detect_country, get_country_profile

logger = logging.getLogger(__name__)

INDUSTRY_STRATEGIES = {
    "saas": {
        "primary_channel": "email",
        "secondary_channel": "linkedin",
        "email_approach": "value-first with social proof",
        "linkedin_approach": "thought leadership engagement",
        "followup_cadence": "4-5 touches over 2 weeks",
        "key_metrics": ["trial signups", "demo requests", "feature interest"],
    },
    "real_estate": {
        "primary_channel": "call",
        "secondary_channel": "email",
        "email_approach": "local market insights",
        "linkedin_approach": "professional networking",
        "followup_cadence": "3-4 touches over 1 week",
        "key_metrics": ["listings", "valuations", "meetings"],
    },
    "agencies": {
        "primary_channel": "email",
        "secondary_channel": "linkedin",
        "email_approach": "capability-focused with case studies",
        "linkedin_approach": "portfolio and expertise showcase",
        "followup_cadence": "4-5 touches over 10 days",
        "key_metrics": ["portfolio reviews", "quotes requested"],
    },
    "manufacturing": {
        "primary_channel": "email",
        "secondary_channel": "call",
        "email_approach": "efficiency and cost reduction focus",
        "linkedin_approach": "industry networking",
        "followup_cadence": "3-4 touches over 2 weeks",
        "key_metrics": ["RFQs", "samples requested", "site visits"],
    },
    "local_business": {
        "primary_channel": "call",
        "secondary_channel": "email",
        "email_approach": "local benefit and community focus",
        "linkedin_approach": "local business groups",
        "followup_cadence": "2-3 touches over 1 week",
        "key_metrics": ["phone pickups", "appointments"],
    },
    "b2b_services": {
        "primary_channel": "linkedin",
        "secondary_channel": "email",
        "email_approach": "consultative and insight-led",
        "linkedin_approach": "expert positioning and value sharing",
        "followup_cadence": "4-6 touches over 2 weeks",
        "key_metrics": ["consultations", "proposals", "retainers"],
    },
    "healthcare": {
        "primary_channel": "email",
        "secondary_channel": "call",
        "email_approach": "compliant, respectful, evidence-based",
        "linkedin_approach": "professional medical networking",
        "followup_cadence": "3-4 touches over 3 weeks",
        "key_metrics": ["HIPAA compliance interest", "demo requests"],
    },
    "education": {
        "primary_channel": "email",
        "secondary_channel": "linkedin",
        "email_approach": "student outcome and institutional benefit",
        "linkedin_approach": "academic networking",
        "followup_cadence": "3-4 touches over 2 weeks",
        "key_metrics": ["demo requests", "pilot programs", "case studies"],
    },
    "enterprise": {
        "primary_channel": "linkedin",
        "secondary_channel": "email",
        "email_approach": "ROI-driven with enterprise case studies",
        "linkedin_approach": "executive networking and thought leadership",
        "followup_cadence": "5-7 touches over 4 weeks",
        "key_metrics": ["PoC requests", "security reviews", " procurement"],
    },
}

DEFAULT_STRATEGY = INDUSTRY_STRATEGIES["saas"]


def _detect_industry_from_profile(profile: SDRProfile) -> str:
    combined = " ".join(filter(None, [
        profile.target_industries or "",
        profile.product_description or "",
        profile.service_description or "",
        profile.product_name or "",
    ])).lower()
    for industry in INDUSTRY_STRATEGIES:
        if industry in combined:
            return industry
    return "saas"


async def decide_next_action(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    current_state: str,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> dict:
    industry = _detect_industry_from_profile(profile)
    strategy = INDUSTRY_STRATEGIES.get(industry, DEFAULT_STRATEGY)
    location = lead_data.get("location", "")
    email_addr = lead_data.get("email", "")
    company = lead_data.get("company", "")
    country = detect_country(location, email_addr, company)
    country_profile = get_country_profile(country)

    ls_result = await db.execute(
        select(LeadState).where(LeadState.org_id == org_id, LeadState.lead_id == lead_data["id"])
    )
    ls = ls_result.scalar_one_or_none()
    channels_used = list(ls.channels_used) if ls and ls.channels_used else []
    contact_count = ls.contact_count if ls else 0
    engagement_score = ls.engagement_score if ls else 0

    system_prompt = f"""You are an expert AI SDR (Sales Development Representative) with deep experience in {industry} sales.
You think independently and make strategic decisions like a top-performing human SDR.

INDUSTRY: {industry}
PRIMARY CHANNEL: {strategy['primary_channel']}
SECONDARY CHANNEL: {strategy['secondary_channel']}
EMAIL APPROACH: {strategy['email_approach']}
LINKEDIN APPROACH: {strategy['linkedin_approach']}
FOLLOWUP CADENCE: {strategy['followup_cadence']}

COUNTRY: {country.upper()}
COMMUNICATION STYLE: {country_profile['communication_style']}
FORMALITY: {country_profile['formality']}
SALES PSYCHOLOGY: {country_profile['sales_psychology']}

SELL TYPE: {profile.sell_type.upper()}
PRODUCT/SERVICE: {profile.product_name or profile.service_description or 'Our solution'}
TONE: {profile.outreach_tone}

Return ONLY valid JSON with these keys:
- action: one of [research, send_email, send_linkedin, linkedin_like, linkedin_comment, make_call, follow_up, send_payment, schedule_meeting, close_won, close_lost, wait]
- channel: the channel [email, linkedin, phone, null]
- reasoning: detailed explanation of why this action was chosen
- timing_insight: when this action should happen
- message_strategy: what the message should focus on
- personalization_focus: what to personalize on

Decision Logic:
1. NEW leads: research first, then decide outreach channel based on industry
2. After research: use primary channel for first outreach
3. If primary channel contacted and no reply: try secondary channel after 2-3 days
4. If both channels used and no reply: use follow_up with different angle
5. If lead engages positively: move to schedule_meeting or send_payment
6. If contact_count >= 5 with no engagement: close_lost
7. For {industry}: prioritize {strategy['primary_channel']} with {strategy['email_approach']}
8. Adapt communication to {country.upper()} ({country_profile['communication_style']})
9. Never use robotic language. Think like a human SDR.
10. Quality conversations over spam volume."""

    user_prompt = f"""LEAD:
Name: {lead_data['name']}
Title: {lead_data['title']}
Company: {lead_data['company']}
Industry: {lead_data.get('industry', 'N/A')}
Location: {lead_data.get('location', 'N/A')}
Email: {lead_data.get('email', 'N/A')}
Phone: {lead_data.get('phone', 'N/A')}
LinkedIn: {lead_data.get('linkedin_url', 'N/A')}

CURRENT STATE: {current_state}
CHANNELS USED SO FAR: {channels_used}
CONTACT COUNT: {contact_count}
ENGAGEMENT SCORE: {engagement_score}

SDR CONFIG:
Target Titles: {profile.target_titles or 'Any'}
Target Industries: {profile.target_industries or 'Any'}
Target Locations: {profile.target_locations or 'Any'}

Decide the next best action. Return only valid JSON."""

    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=512, temperature=0.4, api_key=ai_key)
        decision = json.loads(raw)
        if "action" not in decision:
            return _fallback_decision(current_state, contact_count)
        return decision
    except Exception as e:
        logger.warning(f"AI decision failed: {e}, using fallback")
        return _fallback_decision(current_state, contact_count)


def _fallback_decision(current_state: str, contact_count: int) -> dict:
    if current_state in ("new", "researching"):
        return {"action": "research", "channel": None, "reasoning": "New lead, initiating deep research before outreach", "timing_insight": "Immediate", "message_strategy": "N/A", "personalization_focus": "Company and role analysis"}
    if current_state == "researched" and contact_count == 0:
        return {"action": "send_email", "channel": "email", "reasoning": "Lead researched, sending personalized first outreach", "timing_insight": "Now", "message_strategy": "Value-first introduction", "personalization_focus": "Role-specific pain points"}
    if contact_count >= 5:
        return {"action": "close_lost", "channel": None, "reasoning": "Maximum contact attempts reached without meaningful engagement", "timing_insight": "N/A", "message_strategy": "N/A", "personalization_focus": "N/A"}
    return {"action": "follow_up", "channel": "email", "reasoning": "Continuing followup sequence with fresh angle", "timing_insight": "2-3 days after last contact", "message_strategy": "Value-add with new insight", "personalization_focus": "Previous interaction context"}
