import json
import logging
from typing import Optional
from app.services.ai.model_client import generate_text, generate_text_async
from app.services.sdr.sdr_country_adapter import detect_country, adapt_outreach_for_country

logger = logging.getLogger(__name__)


async def analyze_linkedin_for_outreach(
    linkedin_url: str,
    name: str,
    title: str,
    company: str,
    industry: str,
    location: str,
    ai_key: Optional[str] = None,
) -> dict:
    system_prompt = """You are a LinkedIn outreach strategist. Based on the available prospect information, 
design a personalized LinkedIn outreach strategy.

Return ONLY valid JSON:
{
  "profile_summary": "1-2 sentence summary of who this person is",
  "interests": ["3-5 inferred professional interests"],
  "connection_request": "a personalized connection request under 150 characters that creates curiosity",
  "conversation_starter": "a first DM after acceptance (under 200 chars, no pitch)",
  "engagement_approach": "how to engage this person (thoughtful/insight-first/question-based)",
  "topic_angles": ["2-3 conversation topics that would resonate"],
  "introduction_timing": "when to introduce your product (immediately/after 2-3 messages/after building rapport)"
}
Rules:
- Connection request must be under 150 chars
- Must feel natural and human, never salesy
- Create curiosity without pitching
- Reference specific context from their role/industry/company
- No generic messages"""

    user_prompt = f"""Design LinkedIn outreach for:
Name: {name}
Title: {title}
Company: {company}
Industry: {industry}
Location: {location}
LinkedIn URL: {linkedin_url}

Return valid JSON."""

    try:
        raw = await generate_text_async(system_prompt, user_prompt, max_tokens=800, temperature=0.5, api_key=ai_key)
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"LinkedIn analysis failed: {e}")
        return {
            "connection_request": f"Hi {name.split()[0] if name else 'there'}, I came across your profile and was impressed by your work at {company or 'your company'}. Would love to connect!",
            "conversation_starter": f"Thanks for connecting! I really admire the work you're doing at {company or 'your company'}. What's the most exciting project you're working on right now?",
            "interests": [industry or "Professional growth", company or "Business development"],
            "engagement_approach": "thoughtful",
            "topic_angles": [f"Work at {company}", f"{industry or 'Industry'} trends"],
            "introduction_timing": "after 2-3 messages",
        }


async def generate_linkedin_connection_request(
    name: str,
    title: str,
    company: str,
    analysis: dict,
    country_code: str,
    ai_key: Optional[str] = None,
) -> str:
    base_request = analysis.get("connection_request", "")
    if len(base_request) > 150:
        base_request = base_request[:147] + "..."
    adapted = await adapt_outreach_for_country(base_request, country_code, name, ai_key)
    if len(adapted) > 150:
        adapted = adapted[:147] + "..."
    return adapted


async def generate_linkedin_followup_dm(
    lead_name: str,
    company: str,
    analysis: dict,
    invite_accepted: bool,
    previous_messages: list = None,
    ai_key: Optional[str] = None,
) -> str:
    if invite_accepted:
        system_prompt = f"""Write a natural LinkedIn DM followup after connection acceptance.
Rules:
- Under 200 characters
- Do NOT pitch immediately
- Build conversation naturally
- Reference their work or interests
- Ask an engaging question
- Sound human, not salesy
- No generic messages

The prospect's interests: {analysis.get('interests', [])}
Suggested topics: {analysis.get('topic_angles', [])}
Timing advice: {analysis.get('introduction_timing', 'after 2-3 messages')}"""
        user_prompt = f"Write a followup DM for {lead_name} at {company} after they accepted the connection request."
    else:
        system_prompt = f"""Write a followup email for a LinkedIn connection request that was not accepted.
Rules:
- Reference the LinkedIn request briefly
- Don't sound hurt or desperate
- Offer value
- Under 200 characters
- Transition naturally to email communication"""
        user_prompt = f"Write a LinkedIn followup email for {lead_name} at {company}"

    try:
        return await generate_text_async(system_prompt, user_prompt, max_tokens=200, temperature=0.6, api_key=ai_key).strip()
    except Exception as e:
        logger.warning(f"LinkedIn DM generation failed: {e}")
        if invite_accepted:
            return f"Thanks for connecting, {lead_name}! I really admire what you're doing at {company}. What's been your biggest focus this quarter?"
        return f"Hi {lead_name}, I sent a LinkedIn request earlier - just wanted to follow up here in case that's easier!"
