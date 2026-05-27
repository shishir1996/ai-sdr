import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.agent import SDRProfile, AgentLog
from app.services.ai.model_client import generate_text

logger = logging.getLogger(__name__)


async def check_safety_controls(
    db: AsyncSession,
    org_id: str,
    profile: SDRProfile,
    channel: str,
) -> dict:
    today = datetime.now(timezone.utc).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    daily_counts = await _get_daily_counts(db, org_id, today_start)

    checks = {
        "can_proceed": True,
        "reasons": [],
        "daily_usage": {},
    }

    channel_limits = {
        "email": ("max_daily_emails", profile.max_daily_emails or 20),
        "linkedin": ("max_daily_linkedin", profile.max_daily_linkedin or 15),
        "call": ("max_daily_calls", profile.max_daily_calls or 10),
        "linkedin_like": ("max_daily_likes", profile.max_daily_likes or 20),
        "linkedin_comment": ("max_daily_comments", profile.max_daily_comments or 10),
    }

    limit_field, limit_value = channel_limits.get(channel, (None, None))
    if limit_field and limit_value:
        used = daily_counts.get(channel, 0)
        checks["daily_usage"][channel] = {"used": used, "limit": limit_value}
        if used >= limit_value:
            checks["can_proceed"] = False
            checks["reasons"].append(f"Daily {channel} limit reached ({used}/{limit_value})")

    if profile.leads_target and profile.leads_target > 0:
        total_contacted = await db.scalar(
            select(func.count(AgentLog.id)).where(
                AgentLog.org_id == org_id,
                AgentLog.sdr_profile_id == profile.id,
                AgentLog.created_at >= today_start,
            )
        )
        if total_contacted and total_contacted >= profile.leads_target:
            checks["can_proceed"] = False
            checks["reasons"].append(f"Daily lead target reached ({total_contacted}/{profile.leads_target})")

    return checks


async def _get_daily_counts(db: AsyncSession, org_id: str, today_start: datetime) -> dict:
    result = await db.execute(
        select(AgentLog.channel, func.count(AgentLog.id)).where(
            AgentLog.org_id == org_id,
            AgentLog.created_at >= today_start,
            AgentLog.status == "completed",
        ).group_by(AgentLog.channel)
    )
    counts = {"email": 0, "linkedin": 0, "call": 0, "linkedin_like": 0, "linkedin_comment": 0}
    for row in result.fetchall():
        channel = row[0]
        count = row[1]
        if channel in counts:
            counts[channel] = count
    return counts


async def moderate_outbound_message(
    message_text: str,
    channel: str,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> dict:
    system_prompt = """You are an AI moderation system for sales outreach. Review this message and check for:
1. Spam signals: excessive links, ALL CAPS, spam trigger words
2. Aggressive sales: pressure tactics, urgency manipulation, fear-based language
3. Compliance issues: CAN-SPAM compliance, GDPR compliance
4. Quality: does it sound human-written?
5. Safety: any inappropriate or risky content

Return ONLY valid JSON:
{
  "approved": true/false,
  "issues": ["array of specific issues found"],
  "suggested_fix": "how to fix the main issue",
  "spam_score": 0-100,
  "human_score": 0-100
}

A score is approved if spam_score < 30 and human_score > 60."""

    user_prompt = f"""Moderate this {channel} message:\n\n{message_text}\n\nReturn valid JSON."""

    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=300, temperature=0.2, ai_key=ai_key)
        result = json.loads(raw)
        return result
    except Exception as e:
        logger.warning(f"Moderation failed: {e}")
        return {"approved": True, "issues": [], "suggested_fix": "", "spam_score": 0, "human_score": 80}


async def check_blacklist(
    db: AsyncSession,
    org_id: str,
    lead_email: str,
    lead_domain: str,
) -> bool:
    if not lead_email and not lead_domain:
        return False
    from app.models.lead import Lead
    blacklisted = await db.execute(
        select(Lead).where(
            Lead.org_id == org_id,
            Lead.is_blacklisted == True,
            (Lead.email == lead_email) | (Lead.company.ilike(f"%{lead_domain}%") if lead_domain else False),
        )
    )
    return blacklisted.scalar_one_or_none() is not None
