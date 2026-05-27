import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import SDRProfile
from app.models.campaign import Campaign, CampaignStep
from app.services.ai.model_client import generate_text

logger = logging.getLogger(__name__)


async def design_and_create_campaign(
    db: AsyncSession,
    org_id: str,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> Optional[Campaign]:
    """AI analyzes the admin inputs and auto-designs a complete campaign."""
    existing = await db.execute(
        select(Campaign).where(
            Campaign.org_id == org_id,
            Campaign.sdr_profile_id == profile.id,
            Campaign.status.in_(["active", "draft"]),
        )
    )
    if existing.scalar_one_or_none():
        logger.info(f"Campaign already exists for SDR {profile.id}")
        return None

    config_summary = _build_config_summary(profile)
    industry = _detect_industry(profile)

    campaign_plan = await _ai_design_campaign(config_summary, industry, ai_key)
    if not campaign_plan:
        logger.error("AI campaign design failed")
        return None

    campaign = Campaign(
        org_id=org_id,
        sdr_profile_id=profile.id,
        name=campaign_plan.get("name", f"{profile.name or 'AI SDR'} Campaign"),
        description=campaign_plan.get("objective", ""),
        status="active",
        ai_generated=True,
    )
    db.add(campaign)
    await db.flush()

    steps_data = campaign_plan.get("sequence", [])
    for i, step_data in enumerate(steps_data):
        step = CampaignStep(
            campaign_id=campaign.id,
            step_order=i + 1,
            channel=step_data.get("channel", "email"),
            delay_days=step_data.get("delay_days", 0),
            conditions=step_data.get("conditions"),
        )
        db.add(step)

    await db.flush()
    logger.info(f"AI campaign '{campaign.name}' created for SDR {profile.id}")
    return campaign


def _build_config_summary(profile: SDRProfile) -> str:
    lines = []
    if profile.product_name:
        lines.append(f"Product: {profile.product_name}")
    if profile.product_description:
        lines.append(f"Product Description: {profile.product_description}")
    if profile.service_description:
        lines.append(f"Service: {profile.service_description}")
    if profile.sell_type:
        lines.append(f"Sell Type: {profile.sell_type}")
    if profile.target_titles:
        lines.append(f"Target Titles: {profile.target_titles}")
    if profile.target_industries:
        lines.append(f"Target Industries: {profile.target_industries}")
    if profile.target_locations:
        lines.append(f"Target Locations: {profile.target_locations}")
    if profile.target_company_size_min or profile.target_company_size_max:
        lines.append(f"Company Size: {profile.target_company_size_min or 'Any'} - {profile.target_company_size_max or 'Any'}")
    if profile.lead_sources:
        lines.append(f"Lead Sources: {profile.lead_sources}")
    if profile.sdr_personality:
        lines.append(f"SDR Personality: {profile.sdr_personality}")
    if profile.outreach_tone:
        lines.append(f"Outreach Tone: {profile.outreach_tone}")
    if profile.region:
        lines.append(f"Region: {profile.region}")
    lines.append(f"LinkedIn Connect: {'Yes' if profile.linkedin_connect_enabled else 'No'}")
    lines.append(f"LinkedIn DM: {'Yes' if profile.linkedin_dm_enabled else 'No'}")
    lines.append(f"Has Email: {'Yes' if profile.email_credentials_encrypted else 'No'}")
    return "\n".join(lines)


def _detect_industry(profile: SDRProfile) -> str:
    combined = " ".join(filter(None, [
        profile.target_industries or "",
        profile.product_description or "",
        profile.service_description or "",
        profile.product_name or "",
    ])).lower()
    keywords = {
        "saas": ["saas", "software", "cloud", "app", "platform", "subscription"],
        "real_estate": ["real estate", "property", "realtor", "mortgage", "housing"],
        "agencies": ["agency", "digital agency", "marketing agency", "creative"],
        "manufacturing": ["manufacturing", "factory", "industrial", "production"],
        "local_business": ["local", "restaurant", "salon", "gym", "retail", "store"],
        "b2b_services": ["consulting", "b2b", "professional services", "outsourcing"],
        "healthcare": ["healthcare", "medical", "clinic", "hospital", "health"],
        "education": ["education", "edtech", "school", "university", "training"],
        "enterprise": ["enterprise", "corporation", "fortune", "multinational"],
    }
    scores = {}
    for industry, kw_list in keywords.items():
        score = sum(2 if kw in combined else 0 for kw in kw_list)
        if score > 0:
            scores[industry] = score
    if scores:
        return max(scores, key=scores.get)
    return "saas"


async def _ai_design_campaign(config_summary: str, industry: str, ai_key: Optional[str] = None) -> Optional[dict]:
    system_prompt = f"""You are an expert sales strategist and campaign designer for an AI SDR platform.
Design a complete outbound sales campaign based on the admin's configuration.

Return ONLY valid JSON. No markdown, no explanation.

The JSON must have these keys:
- name: short campaign name (under 60 chars)
- objective: 2-3 sentence campaign objective and strategy
- icp_strategy: 1-2 sentence ideal customer profile approach
- timing_logic: how timing should work
- followup_strategy: the followup approach
- response_handling: how to handle different reply types
- next_step_logic: how to decide next actions
- sequence: array of steps, each with:
  - channel: one of [email, linkedin_connect, linkedin_dm, linkedin_like, linkedin_comment, call]
  - delay_days: number (0 for first step, 2-7 for subsequent)
  - conditions: object with optional keys (open_required, reply_required, min_delay_days)

Design for {industry} industry. Make it specific to this industry's sales dynamics."""

    user_prompt = f"""Admin Configuration:
{config_summary}

Design the complete campaign in JSON format."""

    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=2048, temperature=0.7, api_key=ai_key)
        plan = json.loads(raw)
        if "sequence" not in plan or not plan["sequence"]:
            plan["sequence"] = _default_sequence(industry)
        return plan
    except Exception as e:
        logger.warning(f"AI campaign design failed: {e}")
        return {"name": "AI SDR Campaign", "objective": "Automated outbound campaign", "sequence": _default_sequence(industry)}


def _default_sequence(industry: str) -> list:
    base = [
        {"channel": "email", "delay_days": 0, "conditions": None},
        {"channel": "linkedin_connect", "delay_days": 2, "conditions": {"open_required": False}},
        {"channel": "email", "delay_days": 4, "conditions": {"reply_required": False}},
        {"channel": "linkedin_dm", "delay_days": 7, "conditions": {"reply_required": False}},
        {"channel": "call", "delay_days": 10, "conditions": {"reply_required": False}},
        {"channel": "email", "delay_days": 14, "conditions": {"reply_required": False}},
    ]
    if industry in ["real_estate", "local_business"]:
        base.insert(3, {"channel": "call", "delay_days": 5, "conditions": {"reply_required": False}})
    if industry in ["saas", "enterprise"]:
        base.insert(2, {"channel": "linkedin_like", "delay_days": 1, "conditions": None})
    return base
