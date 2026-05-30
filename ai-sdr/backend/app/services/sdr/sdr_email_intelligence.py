import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import SDRProfile, AgentLog
from app.services.ai.model_client import generate_text, generate_text_async
from app.services.sdr.sdr_country_adapter import detect_country, adapt_outreach_for_country

logger = logging.getLogger(__name__)

FOLLOWUP_TYPES = [
    "soft_followup",
    "value_add_followup",
    "reminder_followup",
    "breakup_email",
    "case_study_followup",
    "social_proof_followup",
    "objection_handling_followup",
]


async def generate_intelligent_email(
    lead_data: dict,
    profile: SDRProfile,
    campaign_context: str = "",
    previous_interactions: list = None,
    followup_type: str = "initial",
    ai_key: Optional[str] = None,
) -> dict:
    name = lead_data.get("name", "")
    title = lead_data.get("title", "")
    company = lead_data.get("company", "")
    industry = lead_data.get("industry", "")
    location = lead_data.get("location", "")
    email = lead_data.get("email", "")
    pain_points = lead_data.get("pain_points", "")
    personalization_hooks = lead_data.get("personalization_hooks", [])

    country = detect_country(location, email, company)

    rules_text = _get_followup_rules(followup_type)
    industry_text = industry or "the prospect's industry"
    personality_text = profile.sdr_personality or "Professional and helpful"
    product_text = profile.product_name or profile.service_description or "Our solution"
    system_prompt = f"""You are a world-class SDR writing a personalized sales email.
You write like a human expert in {industry_text} sales.

SELLING: {product_text}
SELL TYPE: {profile.sell_type.upper()}
TONE: {profile.outreach_tone}
PERSONALITY: {personality_text}

CAMPAIGN CONTEXT: {campaign_context}

FOLLOWUP TYPE: {followup_type}

RULES:
{rules_text}

Return ONLY valid JSON:
{{
  "subject": "subject line under 60 chars, avoid spam triggers",
  "body": "email body in plain text, 3-5 sentences, natural human tone",
  "cta": "the call to action",
  "personalization_elements": ["list of what was personalized"]
}}

CRITICAL:
- Sound 100% human-written. Never robotic, never salesy.
- No spam words, no aggressive language
- Build curiosity, don't pitch immediately
- Reference specific context about their role at their company
- One clear CTA
- Feel like a real person wrote this specific email"""

    hooks_text = "\n".join(f"- {h}" for h in personalization_hooks[:3]) if personalization_hooks else ""
    prev_text = ""
    if previous_interactions:
        prev_text = "Previous interactions:\n" + "\n".join(
            f"- {p.get('action', 'contact')}: {p.get('result', '')[:100]}"
            for p in previous_interactions[-3:]
        )

    user_prompt = f"""Write a personalized email for:

Name: {name}
Title: {title}
Company: {company}
Industry: {industry}
Location: {location}

Personalization Hooks:
{hooks_text}

{prev_text}

Return valid JSON with subject, body, cta, personalization_elements."""

    try:
        raw = await generate_text_async(system_prompt, user_prompt, max_tokens=800, temperature=0.7, api_key=ai_key)
        email = json.loads(raw)
        if not isinstance(email, dict) or "subject" not in email or "body" not in email:
            raise ValueError("Invalid email format")
    except Exception as e:
        logger.warning(f"AI email generation failed: {e}, using fallback")
        email = {
            "subject": f"Quick thought, {name.split()[0] if name else 'there'}",
            "body": f"Hi {name.split()[0] if name else 'there'},\n\nI was looking at {company or 'your work'} and thought I'd reach out. We help {industry or 'companies'} like yours {profile.product_description or 'achieve better results'}.\n\nWould you be open to a quick chat this week?\n\nBest,\n{profile.name or 'AI SDR'}",
            "cta": "Quick chat this week?",
            "personalization_elements": [f"Company: {company}", f"Role: {title}"],
        }

    adapted_body = await adapt_outreach_for_country(email["body"], country, name, ai_key)
    adapted_subject = await adapt_outreach_for_country(email["subject"], country, name, ai_key)

    return {
        "subject": adapted_subject[:60],
        "body": adapted_body,
        "cta": email.get("cta", ""),
        "personalization_elements": email.get("personalization_elements", []),
    }


def _get_followup_rules(followup_type: str) -> str:
    rules = {
        "initial": "- First email, introduce value proposition\n- Build curiosity\n- Reference their specific context\n- One clear CTA\n- Keep it to 4-5 sentences",
        "soft_followup": "- Gentle nudge, reference first email\n- Add one new insight or value point\n- Keep it shorter than first email (2-3 sentences)\n- Assume they were busy, not disinterested",
        "value_add_followup": "- Provide genuine value (article, insight, tip)\n- Relate the value to their business\n- No hard pitch, just helpful\n- Position yourself as a resource",
        "reminder_followup": "- Brief reminder that you reached out\n- Reiterate the core value in one sentence\n- Make it easy to respond\n- Shortest email (2-3 sentences)",
        "breakup_email": "Final email acknowledging they might not be interested\n- Leave the door open\n- Professional and respectful tone\n- No pressure, no guilt",
        "case_study_followup": "- Share a relevant success story or case study\n- Make it directly applicable to their situation\n- Show proof that similar companies benefit\n- Include specific results (metrics if possible)",
        "social_proof_followup": "- Mention other companies in their industry/region using your solution\n- Use social proof to build credibility\n- Not arrogant, just factual\n- 'Many {industry} companies find...'",
        "objection_handling_followup": "- Address a common objection proactively\n- Show understanding of their potential concerns\n- Provide a thoughtful response\n- Invite discussion about the objection",
    }
    return rules.get(followup_type, rules["initial"])


async def decide_followup_type(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    profile: SDRProfile,
    contact_count: int,
    ai_key: Optional[str] = None,
) -> str:
    result = await db.execute(
        select(AgentLog).where(
            AgentLog.org_id == org_id,
            AgentLog.lead_id == lead_id,
            AgentLog.action.in_(["email_sent", "reply_handled"]),
        ).order_by(AgentLog.created_at.desc()).limit(5)
    )
    logs = result.scalars().all()
    recent_actions = [l.action for l in logs]

    if contact_count == 0:
        return "initial"
    if contact_count == 1:
        return "soft_followup"
    if contact_count == 2:
        return "value_add_followup"
    if contact_count == 3:
        return "case_study_followup"
    if contact_count >= 4:
        return "breakup_email"

    system_prompt = f"""Given the followup history for this lead, decide the best followup type.
Options: {', '.join(FOLLOWUP_TYPES)}
Return ONLY the followup type as a string, no other text."""
    user_prompt = f"Contact count: {contact_count}\nRecent actions: {recent_actions}\nBest followup type:"
    try:
        return await generate_text_async(system_prompt, user_prompt, max_tokens=50, temperature=0.3, api_key=ai_key).strip()
    except Exception:
        return "soft_followup"
