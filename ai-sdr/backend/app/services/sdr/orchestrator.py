import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.agent import SDRProfile, LeadState, AgentLog
from app.models.lead import Lead
from app.models.user import Organization
from app.services.ai.model_client import generate_text
from app.services.integrations.resolver import resolve_api_key
from app.services.sdr.auto_discovery import auto_discover_leads
from app.services.lead_extraction.web_scraper import scrape_and_create_lead
from app.services.sdr.rate_limiter import rate_limiter
from app.services.email.reply_detector import check_for_replies as check_gmail_replies
from app.services.sdr.tools import (
    research_lead_tool,
    send_email_tool,
    send_linkedin_message_tool,
    linkedin_like_tool,
    linkedin_comment_tool,
    make_call_tool,
    schedule_meeting_tool,
    send_payment_tool,
)

logger = logging.getLogger(__name__)


LEAD_STATE_FLOW = [
    "new",
    "researching",
    "researched",
    "contacting_email",
    "contacted_email",
    "contacting_linkedin",
    "contacted_linkedin",
    "contacting_call",
    "contacted_call",
    "follow_up",
    "meeting_scheduled",
    "payment_sent",
    "closed_won",
    "closed_lost",
]


def _now():
    return datetime.now(timezone.utc)


async def start_sdr_cycle(org_id: str, sdr_profile_id: Optional[str] = None):
    logger.info(f"SDR cycle started for org {org_id} profile {sdr_profile_id}")
    try:
        while True:
            async with async_session_factory() as db:
                if sdr_profile_id:
                    result = await db.execute(select(SDRProfile).where(SDRProfile.id == sdr_profile_id))
                    profile = result.scalar_one_or_none()
                else:
                    profile = await _get_profile(db, org_id)
                if not profile or not profile.is_active:
                    logger.info(f"SDR deactivated for org {org_id}")
                    break

                discovered_apollo = await auto_discover_leads(db, org_id, profile)
                await db.commit()
                if discovered_apollo:
                    logger.info(f"Auto-discovered {discovered_apollo} new leads from Apollo")

                discovered_web = await _web_scrape_discovery(db, org_id, profile)
                if discovered_web:
                    logger.info(f"Auto-discovered {discovered_web} new leads from web scraping")
                    await db.commit()

                leads = await _get_leads_needing_attention(db, org_id, profile)
                logger.info(f"SDR cycle: {len(leads)} leads need attention")

                for lead in leads:
                    await _process_lead(db, org_id, lead, profile)

            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"SDR cycle error: {e}")


async def _web_scrape_discovery(db: AsyncSession, org_id: str, profile: SDRProfile) -> int:
    targets_raw = profile.web_scrape_targets
    if not targets_raw:
        return 0

    urls = [u.strip() for u in targets_raw.split("\n") if u.strip() and u.strip().startswith("http")]
    if not urls:
        return 0

    existing_result = await db.execute(
        select(Lead.email).where(Lead.org_id == org_id, Lead.email.isnot(None))
    )
    existing_emails = {row[0] for row in existing_result.fetchall()}

    added = 0
    for url in urls[:10]:
        try:
            data = await scrape_and_create_lead(url)
            if not data.get("company") and not data.get("email"):
                continue
            if data.get("email") and data["email"] in existing_emails:
                continue
            lead = Lead(org_id=org_id, **data)
            db.add(lead)
            if data.get("email"):
                existing_emails.add(data["email"])
            added += 1
        except Exception as e:
            logger.warning(f"Web scrape discovery failed for {url}: {e}")

    await db.flush()
    return added


async def _get_profile(db: AsyncSession, org_id: str) -> Optional[SDRProfile]:
    result = await db.execute(select(SDRProfile).where(SDRProfile.org_id == org_id))
    return result.scalar_one_or_none()


async def _get_leads_needing_attention(db: AsyncSession, org_id: str, profile: SDRProfile) -> list[Lead]:
    lead_sources = []
    if profile.lead_sources:
        try:
            lead_sources = json.loads(profile.lead_sources)
        except Exception:
            lead_sources = [s.strip() for s in profile.lead_sources.split(",") if s.strip()]

    query = select(Lead).where(Lead.org_id == org_id)
    if lead_sources:
        source_filters = [Lead.source == s for s in lead_sources]
        from sqlalchemy import or_
        query = query.where(or_(*source_filters))
    query = query.order_by(Lead.created_at.desc()).limit(20)
    result = await db.execute(query)
    all_leads = result.scalars().all()

    state_result = await db.execute(
        select(LeadState).where(LeadState.org_id == org_id)
    )
    states = {s.lead_id: s for s in state_result.scalars().all()}

    needs_attention = []
    for lead in all_leads:
        ls = states.get(lead.id)
        if ls and ls.is_paused:
            continue
        if not ls or ls.state in ("new", "researched", "follow_up"):
            needs_attention.append(lead)
        elif ls.state not in ("closed_won", "closed_lost", "archived", "meeting_scheduled", "payment_sent"):
            needs_attention.append(lead)

    return needs_attention[:5]


async def _log_action(
    db: AsyncSession,
    org_id: str,
    lead_id: Optional[str],
    action: str,
    channel: Optional[str],
    reasoning: str,
    result: str,
    status: str = "completed",
):
    log = AgentLog(
        org_id=org_id,
        lead_id=lead_id,
        action=action,
        channel=channel,
        reasoning=reasoning,
        result=result,
        status=status,
    )
    db.add(log)
    await db.flush()


async def _update_lead_state(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    new_state: str,
    channel: Optional[str] = None,
):
    result = await db.execute(
        select(LeadState).where(LeadState.org_id == org_id, LeadState.lead_id == lead_id)
    )
    ls = result.scalar_one_or_none()
    if not ls:
        ls = LeadState(org_id=org_id, lead_id=lead_id, state=new_state)
        db.add(ls)
    else:
        ls.state = new_state

    if channel:
        used = list(ls.channels_used or [])
        if channel not in used:
            used.append(channel)
            ls.channels_used = used
        ls.contact_count = (ls.contact_count or 0) + 1
        ls.last_contacted_at = _now()

    await db.flush()


async def _process_lead(db: AsyncSession, org_id: str, lead: Lead, profile: SDRProfile):
    result = await db.execute(
        select(LeadState).where(LeadState.org_id == org_id, LeadState.lead_id == lead.id)
    )
    ls = result.scalar_one_or_none()
    state = ls.state if ls else "new"

    lead_data = {
        "id": lead.id,
        "name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "title": lead.title or "",
        "company": lead.company or "",
        "email": lead.email or "",
        "phone": lead.phone or "",
        "linkedin_url": lead.linkedin_url or "",
        "industry": lead.industry or "",
        "location": lead.location or "",
    }

    ai_key = await resolve_api_key(db, org_id, "together_ai")

    # Check for email replies
    gmail_client_id = await resolve_api_key(db, org_id, "gmail")
    gmail_secret = await resolve_api_secret(db, org_id, "gmail")
    gmail_refresh = await resolve_refresh_token(db, org_id, "gmail")
    if lead.email and gmail_client_id and gmail_refresh:
        replies = check_gmail_replies(gmail_client_id, gmail_secret, gmail_refresh, lead.email, since=ls.last_contacted_at if ls else None)
        for reply in replies:
            await _log_action(db, org_id, lead.id, "reply_detected", "email", f"Lead replied: {reply['snippet'][:100]}", reply["snippet"], status="success")
            await _update_lead_state(db, org_id, lead.id, "follow_up", "email")
            logger.info(f"Email reply detected from {lead_data['name']}: {reply['subject']}")

    # AI decides next action
    decision = await _decide_next_action(db, org_id, lead_data, state, profile, ai_key)
    action = decision.get("action", "skip")
    reasoning = decision.get("reasoning", "No reasoning provided")
    channel = decision.get("channel")

    logger.info(f"SDR decision for {lead_data['name']}: {action} ({reasoning})")

    if action == "research":
        await _log_action(db, org_id, lead.id, "research", None, reasoning, "Researching lead...")
        await _update_lead_state(db, org_id, lead.id, "researching")
        if lead.email:
            enriched = await research_lead_tool(lead.email)
            if enriched:
                lead.title = enriched.get("title") or lead.title
                lead.company = enriched.get("company") or lead.company
                lead.industry = enriched.get("industry") or lead.industry
                lead.linkedin_url = enriched.get("linkedin_url") or lead.linkedin_url
                await db.flush()
        await _update_lead_state(db, org_id, lead.id, "researched")

    elif action == "send_email" and lead.email:
        allowed, remaining = rate_limiter.check_email(org_id, profile.max_daily_emails)
        if not allowed:
            await _log_action(db, org_id, lead.id, "send_email", "email", f"Rate limit exceeded ({remaining} remaining today)", "Skipped", status="skipped")
        else:
            await _log_action(db, org_id, lead.id, "send_email", "email", reasoning, "Drafting email...")
            await _update_lead_state(db, org_id, lead.id, "contacting_email", "email")
            result_text = await send_email_tool(db, org_id, lead_data, profile, ai_key)
            await _log_action(db, org_id, lead.id, "email_sent", "email", reasoning, result_text)
            await _update_lead_state(db, org_id, lead.id, "contacted_email", "email")

    elif action == "send_linkedin" and lead.linkedin_url:
        if not profile.linkedin_connect_enabled and not profile.linkedin_dm_enabled:
            await _log_action(db, org_id, lead.id, "send_linkedin", "linkedin", "LinkedIn outreach disabled in profile", "Skipped", status="skipped")
        elif not lead_data.get("linkedin_url"):
            await _log_action(db, org_id, lead.id, "send_linkedin", "linkedin", "No LinkedIn URL", "Skipped", status="skipped")
        else:
            allowed, remaining = rate_limiter.check_linkedin(org_id, profile.max_daily_linkedin)
            if not allowed:
                await _log_action(db, org_id, lead.id, "send_linkedin", "linkedin", f"Rate limit exceeded ({remaining} remaining today)", "Skipped", status="skipped")
            else:
                await _log_action(db, org_id, lead.id, "send_linkedin", "linkedin", reasoning, "Sending LinkedIn message...")
                await _update_lead_state(db, org_id, lead.id, "contacting_linkedin", "linkedin")
                action_type = "dm" if profile.linkedin_dm_enabled and ls and ls.contact_count and ls.contact_count > 0 else "connect"
                result_text = await send_linkedin_message_tool(db, org_id, lead_data, profile, ai_key, action_type=action_type)
                await _log_action(db, org_id, lead.id, "linkedin_sent", "linkedin", reasoning, result_text)
                await _update_lead_state(db, org_id, lead.id, "contacted_linkedin", "linkedin")

    elif action == "make_call" and lead.phone:
        allowed, remaining = rate_limiter.check_call(org_id, profile.max_daily_calls)
        if not allowed:
            await _log_action(db, org_id, lead.id, "make_call", "phone", f"Rate limit exceeded ({remaining} remaining today)", "Skipped", status="skipped")
        else:
            await _log_action(db, org_id, lead.id, "make_call", "phone", reasoning, "Initiating call...")
            await _update_lead_state(db, org_id, lead.id, "contacting_call", "phone")
            result_text = await make_call_tool(db, org_id, lead_data, profile, ai_key)
            await _log_action(db, org_id, lead.id, "call_made", "phone", reasoning, result_text)
            await _update_lead_state(db, org_id, lead.id, "contacted_call", "phone")

    elif action == "send_payment" and profile.payment_link:
        await _log_action(db, org_id, lead.id, "send_payment", "email", reasoning, "Sending payment link...")
        result_text = await send_payment_tool(lead_data, profile)
        await _log_action(db, org_id, lead.id, "payment_sent", "email", reasoning, result_text)
        await _update_lead_state(db, org_id, lead.id, "payment_sent")

    elif action == "schedule_meeting" and profile.calendar_link:
        await _log_action(db, org_id, lead.id, "schedule_meeting", "email", reasoning, "Sending calendar invite...")
        result_text = await schedule_meeting_tool(lead_data, profile)
        await _log_action(db, org_id, lead.id, "meeting_scheduled", "email", reasoning, result_text)
        await _update_lead_state(db, org_id, lead.id, "meeting_scheduled")

    elif action == "linkedin_like":
        await _log_action(db, org_id, lead.id, "linkedin_like", "linkedin", reasoning, "Liking LinkedIn post...")
        result_text = await linkedin_like_tool(db, org_id, lead_data, profile, ai_key)
        await _log_action(db, org_id, lead.id, "like_sent", "linkedin", reasoning, result_text)
        await _update_lead_state(db, org_id, lead.id, "follow_up", "linkedin")

    elif action == "linkedin_comment":
        await _log_action(db, org_id, lead.id, "linkedin_comment", "linkedin", reasoning, "Commenting on LinkedIn post...")
        result_text = await linkedin_comment_tool(db, org_id, lead_data, profile, ai_key)
        await _log_action(db, org_id, lead.id, "comment_sent", "linkedin", reasoning, result_text)
        await _update_lead_state(db, org_id, lead.id, "follow_up", "linkedin")

    elif action == "follow_up":
        await _log_action(db, org_id, lead.id, "follow_up", channel or "email", reasoning, "Following up...")
        await _update_lead_state(db, org_id, lead.id, "follow_up", channel)

    elif action == "close_won":
        await _log_action(db, org_id, lead.id, "close_won", None, reasoning, "Deal closed won")
        await _update_lead_state(db, org_id, lead.id, "closed_won")

    elif action == "close_lost":
        await _log_action(db, org_id, lead.id, "close_lost", None, reasoning, "Deal closed lost")
        await _update_lead_state(db, org_id, lead.id, "closed_lost")

    await db.commit()


async def _decide_next_action(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    current_state: str,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> dict:
    channels_used = []
    ls_result = await db.execute(
        select(LeadState).where(LeadState.org_id == org_id, LeadState.lead_id == lead_data["id"])
    )
    ls = ls_result.scalar_one_or_none()
    if ls and ls.channels_used:
        channels_used = list(ls.channels_used)

    system_prompt = """You are an AI SDR (Sales Development Representative). You are autonomous and make all decisions.

Given a lead profile, current state, and your SDR configuration, decide the NEXT BEST ACTION.

Return a JSON with:
- action: one of [research, send_email, send_linkedin, linkedin_like, linkedin_comment, make_call, send_payment, schedule_meeting, follow_up, close_won, close_lost, wait]
- channel: the channel to use if applicable [email, linkedin, phone, null]
- reasoning: brief explanation of why you chose this action

Rules:
- If lead state is "new", start with research or first email
- If lead is "researched" and hasn't been contacted yet, send first email
- If emailed and no reply after 3+ days, try LinkedIn
- If LinkedIn sent and no reply after 3+ days, try call
- If lead engages positively (meeting_scheduled, payment_sent), move to close_won
- If lead has been contacted 3+ times across channels with no engagement, close_lost
- For products: if lead shows interest, send_payment link
- For services: if lead shows interest, schedule_meeting
- Use follow_up if it's been 3+ days since last contact
- If no action needed right now, return "wait" """

    target_info = f"""TARGET: {profile.target_titles or 'Any title'}
INDUSTRIES: {profile.target_industries or 'Any'}
LOCATIONS: {profile.target_locations or 'Any'}
COMPANY SIZE: {profile.target_company_size_min or 'Any'} - {profile.target_company_size_max or 'Any'} employees
SELL TYPE: {profile.sell_type.upper()}
PRODUCT/SERVICE: {profile.product_name or profile.service_description or 'Not specified'}
TONE: {profile.outreach_tone}"""

    user_prompt = f"""SDR CONFIG:
{target_info}

LEAD:
Name: {lead_data['name']}
Title: {lead_data['title']}
Company: {lead_data['company']}
Email: {lead_data.get('email', 'N/A')}
Phone: {lead_data.get('phone', 'N/A')}
LinkedIn: {lead_data.get('linkedin_url', 'N/A')}
Industry: {lead_data.get('industry', 'N/A')}

CURRENT STATE: {current_state}
CHANNELS USED SO FAR: {channels_used}
CONTACT COUNT: {ls.contact_count if ls else 0}

Decide the next action. Return only valid JSON."""

    try:
        raw = generate_text(system_prompt, user_prompt, max_tokens=256, temperature=0.4, api_key=ai_key)
        decision = json.loads(raw)
        if "action" not in decision:
            return {"action": "wait", "channel": None, "reasoning": "AI returned invalid decision format"}
        return decision
    except Exception:
        if current_state == "new":
            return {"action": "research", "channel": None, "reasoning": "New lead, starting research"}
        elif current_state == "researched":
            return {"action": "send_email", "channel": "email", "reasoning": "Lead researched, sending intro email"}
        elif "contacted" in current_state:
            return {"action": "follow_up", "channel": "email", "reasoning": "Following up after previous contact"}
        return {"action": "wait", "channel": None, "reasoning": "No action needed at this time"}
