import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.agent import SDRProfile, LeadState, AgentLog
from app.models.lead import Lead
from app.models.campaign import Campaign, CampaignStep
from app.services.ai.model_client import generate_text
from app.services.integrations.resolver import resolve_api_key, resolve_api_secret, resolve_refresh_token
from app.services.sdr.auto_discovery import auto_discover_leads
from app.services.lead_extraction.web_scraper import scrape_and_create_lead
from app.services.sdr.rate_limiter import rate_limiter
from app.services.email.reply_detector import check_email_replies
from app.services.email.reply_handler import handle_reply
from app.services.sdr.credentials import decrypt_sdr_credentials
from app.services.sdr.sdr_campaign_intelligence import design_and_create_campaign
from app.services.sdr.sdr_lead_analyzer import analyze_lead_deeply
from app.services.sdr.sdr_decision_engine import decide_next_action
from app.services.sdr.sdr_email_intelligence import generate_intelligent_email, decide_followup_type
from app.services.sdr.sdr_linkedin_intelligence import analyze_linkedin_for_outreach, generate_linkedin_connection_request, generate_linkedin_followup_dm
from app.services.sdr.sdr_safety_controls import check_safety_controls, moderate_outbound_message, check_blacklist
from app.services.sdr.sdr_country_adapter import detect_country
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
from app.services.sdr.activity_service import (
    log_activity, log_reasoning, log_campaign_event, log_lead_timeline,
    log_sequence_execution, update_sdr_status,
)

logger = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc)


async def _update_status(
    db: AsyncSession, org_id: str, profile_id: str,
    status: str, **kwargs,
):
    try:
        await update_sdr_status(db, org_id, profile_id, status, **kwargs)
    except Exception as e:
        logger.warning(f"Status update failed: {e}")


async def start_sdr_cycle(org_id: str, sdr_profile_id: Optional[str] = None):
    logger.info(f"=== SDR AUTONOMOUS CYCLE STARTED for org {org_id} profile {sdr_profile_id} ===")
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

                ai_key = await resolve_api_key(db, org_id, "together_ai")

                await _update_status(db, org_id, profile.id, "thinking",
                                     current_action="Analyzing org config and designing campaign strategy")

                campaign = await design_and_create_campaign(db, org_id, profile, ai_key)
                if campaign:
                    logger.info(f"AI auto-designed campaign: {campaign.name}")
                    await log_activity(db, org_id, profile.id, "campaign_strategy_created",
                                       summary=f"AI designed campaign: {campaign.name}",
                                       reasoning=f"SDR analyzed org's ICP and industry to create a targeted {campaign.description or 'outbound'} strategy",
                                       campaign_id=campaign.id,
                                       details={"campaign_name": campaign.name, "objective": campaign.description},
                                       next_planned_action="Begin lead discovery and outreach",
                                       confidence_score=85)
                    await log_campaign_event(db, org_id, campaign.id, "campaign_created",
                                             sdr_profile_id=profile.id,
                                             summary=f"Campaign '{campaign.name}' designed by AI SDR",
                                             reasoning="Auto-designed based on admin ICP configuration and industry best practices",
                                             progress_before=0, progress_after=0)
                    await _update_status(db, org_id, profile.id, "planning",
                                         current_action=f"Executing campaign: {campaign.name}",
                                         increment_campaigns=True,
                                         current_campaign_id=campaign.id)

                await _update_status(db, org_id, profile.id, "researching",
                                     current_action="Discovering and researching leads")

                discovered_apollo = await auto_discover_leads(db, org_id, profile)
                await db.commit()
                if discovered_apollo:
                    logger.info(f"Auto-discovered {discovered_apollo} new leads from Apollo")
                    await log_activity(db, org_id, profile.id, "leads_analyzed",
                                       summary=f"Discovered {discovered_apollo} new leads via Apollo.io",
                                       reasoning=f"Apollo.io extraction found {discovered_apollo} leads matching SDR's ICP criteria",
                                       details={"source": "apollo", "count": discovered_apollo},
                                       next_planned_action=f"Analyze and prioritize {discovered_apollo} new leads",
                                       confidence_score=90)

                discovered_web = await _web_scrape_discovery(db, org_id, profile)
                if discovered_web:
                    logger.info(f"Auto-discovered {discovered_web} new leads from web scraping")
                    await db.commit()
                    await log_activity(db, org_id, profile.id, "leads_analyzed",
                                       summary=f"Discovered {discovered_web} new leads via web scraping",
                                       reasoning=f"Web scraping found {discovered_web} leads from configured target URLs",
                                       details={"source": "web_scrape", "count": discovered_web},
                                       next_planned_action=f"Include {discovered_web} scraped leads in outreach pipeline")

                campaign_context = ""
                active_campaign = await db.execute(
                    select(Campaign).where(
                        Campaign.org_id == org_id,
                        Campaign.sdr_profile_id == profile.id,
                        Campaign.status == "active",
                    )
                )
                active_campaign_obj = active_campaign.scalar_one_or_none()
                if active_campaign_obj:
                    campaign_context = active_campaign_obj.description or ""

                leads = await _get_leads_needing_attention(db, org_id, profile)
                logger.info(f"SDR cycle: {len(leads)} leads need attention")

                for lead in leads:
                    try:
                        safety = await check_safety_controls(db, org_id, profile, "email")
                        safety_linkedin = await check_safety_controls(db, org_id, profile, "linkedin")
                        safety_call = await check_safety_controls(db, org_id, profile, "call")
                        if not safety["can_proceed"] and not safety_linkedin["can_proceed"] and not safety_call["can_proceed"]:
                            logger.warning(f"All safety limits reached for org {org_id}. Sleeping.")
                            break

                        await _process_lead_autonomously(db, org_id, lead, profile, ai_key, campaign_context)
                    except Exception as e:
                        logger.error(f"Error processing lead {lead.id}: {e}", exc_info=True)
                        await _update_status(db, org_id, profile.id, "error",
                                             current_action=f"Error processing lead {lead.id}: {str(e)[:100]}")
                        await db.commit()

                await _update_status(db, org_id, profile.id, "waiting_for_response",
                                     next_planned_action="Check replies and plan next outreach cycle")

                await db.commit()

            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"SDR cycle error: {e}", exc_info=True)


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
        from sqlalchemy import or_
        source_filters = [Lead.source == s for s in lead_sources]
        query = query.where(or_(*source_filters))
    query = query.order_by(Lead.created_at.desc()).limit(50)
    result = await db.execute(query)
    all_leads = result.scalars().all()
    state_result = await db.execute(select(LeadState).where(LeadState.org_id == org_id))
    states = {s.lead_id: s for s in state_result.scalars().all()}
    RESEARCHED_DEBOUNCE = 300
    needs_attention = []
    for lead in all_leads:
        ls = states.get(lead.id)
        if ls and ls.is_paused:
            continue
        if not ls or ls.state == "new":
            needs_attention.append(lead)
        elif ls.state == "follow_up":
            needs_attention.append(lead)
        elif ls.state == "researched":
            delta = _now() - (ls.last_contacted_at or lead.created_at)
            if delta.total_seconds() > RESEARCHED_DEBOUNCE:
                needs_attention.append(lead)
        elif ls.state not in ("closed_won", "closed_lost", "archived", "meeting_scheduled", "payment_sent"):
            delta = _now() - (ls.last_contacted_at or lead.created_at)
            if delta.total_seconds() > 86400:
                needs_attention.append(lead)
    return needs_attention[:5]


async def _log_action(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: Optional[str],
    lead_id: Optional[str],
    action: str,
    channel: Optional[str],
    reasoning: str,
    result: str,
    status: str = "completed",
):
    log = AgentLog(
        org_id=org_id,
        sdr_profile_id=sdr_profile_id,
        lead_id=lead_id,
        action=action,
        channel=channel,
        reasoning=reasoning,
        result=result,
        status=status,
    )
    db.add(log)
    await db.flush()


async def _log_system_action(
    db: AsyncSession,
    org_id: str,
    sdr_profile_id: Optional[str],
    lead_id: Optional[str],
    action: str,
    channel: Optional[str],
    result: str,
    status: str = "completed",
):
    log = AgentLog(
        org_id=org_id,
        sdr_profile_id=sdr_profile_id,
        lead_id=lead_id,
        action=action,
        channel=channel,
        reasoning="System action",
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


async def _process_lead_autonomously(
    db: AsyncSession,
    org_id: str,
    lead: Lead,
    profile: SDRProfile,
    ai_key: Optional[str],
    campaign_context: str = "",
):
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

    lead_name = lead_data["name"] or lead_data.get("email", "Unknown")
    await _update_status(db, org_id, profile.id, "analyzing",
                         current_action=f"Analyzing lead: {lead_name}",
                         current_lead_id=lead.id)

    if lead.email:
        blacklisted = await check_blacklist(db, org_id, lead.email, lead.company or "")
        if blacklisted:
            await _log_action(db, org_id, profile.id, lead.id, "blacklist_skip", None,
                              "Lead is blacklisted", "Skipped", "skipped")
            await log_activity(db, org_id, profile.id, "lead_analyzed",
                               lead_id=lead.id,
                               summary=f"Skipped {lead_name} - blacklisted",
                               reasoning="Lead email or company is on the blacklist",
                               status="skipped")
            return

    gmail_client_id = await resolve_api_key(db, org_id, "gmail")
    gmail_secret = await resolve_api_secret(db, org_id, "gmail")
    gmail_refresh = await resolve_refresh_token(db, org_id, "gmail")
    sdr_email_creds = decrypt_sdr_credentials(profile.email_credentials_encrypted) if profile.email_credentials_encrypted else None
    if lead.email:
        replies = check_email_replies(
            lead_email=lead.email,
            since=ls.last_contacted_at if ls else None,
            gmail_client_id=gmail_client_id,
            gmail_secret=gmail_secret,
            gmail_refresh=gmail_refresh,
            sdr_email_creds=sdr_email_creds,
        )
        for reply in replies:
            logger.info(f"Email reply detected from {lead_data['name']}: {reply.get('subject', '')}")
            result_text = await handle_reply(db, org_id, lead, lead_data, profile, reply, ai_key=ai_key)
            await log_activity(db, org_id, profile.id, "reply_detected",
                               lead_id=lead.id, channel="email",
                               summary=f"Reply detected from {lead_name}: {reply.get('subject', '')[:60]}",
                               reasoning=f"SDR analyzed reply sentiment and determined next action",
                               details={"reply_subject": reply.get("subject"), "reply_snippet": reply.get("snippet", "")[:200]},
                               next_planned_action="Continue engagement based on reply context",
                               confidence_score=88)
            await log_lead_timeline(db, org_id, lead.id, "reply_received",
                                    sdr_profile_id=profile.id,
                                    summary=f"Email reply: {reply.get('subject', '')[:60]}",
                                    channel="email",
                                    response_received=reply.get("snippet", "")[:200])
            await _log_action(db, org_id, profile.id, lead.id, "reply_handled", "email",
                              f"Contextual reply handled based on sentiment", result_text, "success")
            return

    await _update_status(db, org_id, profile.id, "thinking",
                         current_action=f"Deciding next action for {lead_name}",
                         current_lead_id=lead.id)

    decision = await decide_next_action(db, org_id, lead_data, state, profile, ai_key)
    action = decision.get("action", "skip")
    reasoning = decision.get("reasoning", "No reasoning provided")
    channel = decision.get("channel")

    await log_reasoning(db, org_id, profile.id, "next_action_decided",
                        lead_id=lead.id,
                        human_readable_reasoning=reasoning,
                        detailed_reasoning=decision,
                        ai_confidence_score=decision.get("confidence_score"),
                        channel_selected=channel,
                        timing_explanation=decision.get("timing_insight"),
                        personalization_strategy=decision.get("message_strategy"),
                        context_summary=f"Lead: {lead_name}, State: {state}, Contacts: {ls.contact_count if ls else 0}")

    logger.info(f"SDR autonomous decision for {lead_data['name']}: {action} - {reasoning}")

    await _update_status(db, org_id, profile.id, "executing",
                         current_action=f"{action.replace('_', ' ').title()} for {lead_name}",
                         current_lead_id=lead.id)

    if action == "research":
        await _log_action(db, org_id, profile.id, lead.id, "research", None,
                          reasoning, "Analyzing lead data for personalization...")
        await _update_lead_state(db, org_id, lead.id, "researching")
        await _update_status(db, org_id, profile.id, "analyzing",
                             current_action=f"Analyzing {lead_name}")
        await log_activity(db, org_id, profile.id, "lead_analyzed",
                           lead_id=lead.id,
                           summary=f"Analyzing {lead_name} for personalization",
                           reasoning=reasoning,
                           next_planned_action="Extract personalization hooks and prepare outreach strategy")

        deep_analysis = {}
        if lead.email:
            deep_analysis = await analyze_lead_deeply(lead, ai_key)
            enriched = await research_lead_tool(lead.email)
            if enriched:
                lead.title = enriched.get("title") or lead.title
                lead.company = enriched.get("company") or lead.company
                lead.industry = enriched.get("industry") or lead.industry
                lead.linkedin_url = enriched.get("linkedin_url") or lead.linkedin_url
        await _update_lead_state(db, org_id, lead.id, "researched")
        hooks = deep_analysis.get("personalization_hooks", [])
        pain_points = deep_analysis.get("likely_pain_points", [])
        await log_activity(db, org_id, profile.id, "lead_analyzed",
                           lead_id=lead.id,
                           summary=f"Analysis complete for {lead_name}" if lead.email else f"Basic analysis for {lead_name} (no email for deep analysis)",
                           reasoning=f"Found {len(hooks)} personalization hooks. Key pain points: {pain_points[:2]}" if lead.email else "No email for deep analysis",
                           details={"personalization_hooks": hooks[:5], "company_analysis": deep_analysis.get("company", "")} if lead.email else {"note": "No email available for enrichment"},
                           next_planned_action="Begin targeted outreach based on analysis insights",
                           is_expandable=True,
                           confidence_score=82 if lead.email else 40)
        await log_lead_timeline(db, org_id, lead.id, "researched",
                                sdr_profile_id=profile.id,
                                summary=f"Lead analyzed - {len(hooks)} personalization hooks identified" if lead.email else "Lead noted (no email for analysis)",
                                reasoning=f"Pain points: {pain_points[:2]}" if lead.email else "No email available")

    elif action == "send_email" and lead.email:
        safety = await check_safety_controls(db, org_id, profile, "email")
        if not safety["can_proceed"]:
            await log_activity(db, org_id, profile.id, "email_drafted",
                               lead_id=lead.id, channel="email",
                               summary=f"Email skipped for {lead_name} - safety limit",
                               reasoning=f"Safety limit: {safety['reasons']}", status="skipped")
            await _log_action(db, org_id, profile.id, lead.id, "send_email", "email",
                              f"Safety limit: {safety['reasons']}", "Skipped", "skipped")
            await _update_lead_state(db, org_id, lead.id, "researched")
        elif not profile.email_credentials_encrypted:
            await log_activity(db, org_id, profile.id, "email_drafted",
                               lead_id=lead.id, channel="email",
                               summary=f"Email skipped - no email credentials",
                               reasoning="No email credentials configured for this SDR", status="skipped")
            await _log_action(db, org_id, profile.id, lead.id, "send_email", "email",
                              "No email credentials configured for this SDR", "Skipped", "skipped")
        else:
            allowed, remaining = await rate_limiter.check_email(org_id, profile.max_daily_emails)
            if not allowed:
                await log_activity(db, org_id, profile.id, "email_drafted",
                                   lead_id=lead.id, channel="email",
                                   summary=f"Email skipped - rate limit",
                                   reasoning=f"Rate limit exceeded ({remaining} remaining today)", status="skipped")
                await _update_lead_state(db, org_id, lead.id, "researched")
            else:
                lead_data["pain_points"] = decision.get("personalization_focus", "")
                if decision.get("message_strategy"):
                    lead_data["message_strategy"] = decision["message_strategy"]

                await _update_status(db, org_id, profile.id, "drafting",
                                     current_action=f"Drafting email for {lead_name}")

                followup_type = await decide_followup_type(db, org_id, lead.id, profile,
                                                           ls.contact_count if ls else 0, ai_key)
                personalized_email = await generate_intelligent_email(
                    lead_data, profile, campaign_context,
                    previous_interactions=None,
                    followup_type=followup_type,
                    ai_key=ai_key,
                )

                moderation = await moderate_outbound_message(
                    personalized_email["body"], "email", profile, ai_key
                )
                if not moderation.get("approved", True):
                    await log_activity(db, org_id, profile.id, "email_drafted",
                                       lead_id=lead.id, channel="email",
                                       summary=f"Email blocked by moderation for {lead_name}",
                                       reasoning=f"Moderation rejected: {moderation.get('issues', [])}",
                                       details={"spam_score": moderation.get("spam_score"), "issues": moderation.get("issues")},
                                       status="blocked", confidence_score=moderation.get("spam_score", 0))
                else:
                    await log_activity(db, org_id, profile.id, "email_drafted",
                                       lead_id=lead.id, channel="email",
                                       summary=f"Email drafted for {lead_name}: {personalized_email.get('subject', '')[:80]}",
                                       reasoning=f"{reasoning}. Using {followup_type} approach. Spam score: {moderation.get('spam_score', 0)}",
                                       details={"subject": personalized_email.get("subject"), "body_preview": personalized_email.get("body", "")[:200]},
                                       is_expandable=True,
                                       next_planned_action=f"Sent {followup_type} email, waiting for response",
                                       confidence_score=75)
                    await log_reasoning(db, org_id, profile.id, "email_strategy",
                                        lead_id=lead.id,
                                        human_readable_reasoning=f"SDR chose {followup_type} email because {reasoning}",
                                        detailed_reasoning={"followup_type": followup_type, "personalization": personalized_email.get("personalization_elements")},
                                        channel_selected="email",
                                        personalization_strategy=decision.get("message_strategy"))
                    await log_lead_timeline(db, org_id, lead.id, "email_drafted",
                                            sdr_profile_id=profile.id,
                                            summary=f"{followup_type.replace('_', ' ').title()} email prepared",
                                            reasoning=reasoning,
                                            message_preview=personalized_email.get("body", "")[:150],
                                            channel="email",
                                            sdr_status_before=state, sdr_status_after="contacting_email")

                    await _update_lead_state(db, org_id, lead.id, "contacting_email", "email")
                    result_text = await send_email_tool(db, org_id, lead_data, profile, ai_key)
                    await _log_action(db, org_id, profile.id, lead.id, "email_sent", "email",
                                      f"Email sent using {followup_type} strategy: {personalized_email.get('subject', '')}",
                                      result_text)
                    await _update_lead_state(db, org_id, lead.id, "contacted_email", "email")
                    await update_sdr_status(db, org_id, profile.id, "waiting_for_response",
                                            current_action=f"Waiting for {lead_name} to respond to email",
                                            current_lead_id=lead.id,
                                            increment_emails=True,
                                            next_planned_action="Follow up in 48-72 hours if no response")

    elif action == "send_linkedin" and lead.linkedin_url:
        safety = await check_safety_controls(db, org_id, profile, "linkedin")
        if not safety["can_proceed"]:
            await _log_action(db, org_id, profile.id, lead.id, "send_linkedin", "linkedin",
                              f"Safety limit: {safety['reasons']}", "Skipped", "skipped")
            await _update_lead_state(db, org_id, lead.id, "researched")
        elif not profile.linkedin_connect_enabled and not profile.linkedin_dm_enabled:
            await _log_action(db, org_id, profile.id, lead.id, "send_linkedin", "linkedin",
                              "LinkedIn outreach disabled in profile", "Skipped", "skipped")
        else:
            allowed, remaining = await rate_limiter.check_linkedin(org_id, profile.max_daily_linkedin)
            if not allowed:
                await _log_action(db, org_id, profile.id, lead.id, "send_linkedin", "linkedin",
                                  f"Rate limit exceeded ({remaining} remaining today)", "Skipped", "skipped")
                await _update_lead_state(db, org_id, lead.id, "researched")
            else:
                await _update_status(db, org_id, profile.id, "personalizing",
                                     current_action=f"Analyzing LinkedIn profile of {lead_name}")
                li_analysis = await analyze_linkedin_for_outreach(
                    lead.linkedin_url, lead_data["name"], lead_data["title"],
                    lead_data["company"], lead_data["industry"], lead_data["location"], ai_key
                )
                country_code = detect_country(lead_data.get("location", ""), lead_data.get("email", ""), lead_data.get("company", ""))
                personalized_request = await generate_linkedin_connection_request(
                    lead_data["name"], lead_data["title"], lead_data["company"],
                    li_analysis, country_code, ai_key
                )

                await log_activity(db, org_id, profile.id, "linkedin_invite_generated",
                                   lead_id=lead.id, channel="linkedin",
                                   summary=f"LinkedIn outreach for {lead_name}",
                                   reasoning=f"{reasoning}. LinkedIn strategy: {li_analysis.get('engagement_approach', 'standard')}. Profile: {li_analysis.get('profile_summary', '')[:100]}",
                                   details={"invite_preview": personalized_request[:150], "profile_analysis": li_analysis.get("profile_summary", "")[:200]},
                                   is_expandable=True,
                                   next_planned_action="Follow up with DM after connection accepted",
                                   confidence_score=78)
                await log_lead_timeline(db, org_id, lead.id, "linkedin_outreach",
                                        sdr_profile_id=profile.id,
                                        summary=f"LinkedIn outreach prepared",
                                        reasoning=f"Strategy: {li_analysis.get('engagement_approach', 'standard')}",
                                        message_preview=personalized_request[:120],
                                        channel="linkedin",
                                        sdr_status_before=state, sdr_status_after="contacting_linkedin")
                await log_reasoning(db, org_id, profile.id, "linkedin_strategy",
                                    lead_id=lead.id,
                                    human_readable_reasoning=f"SDR chose LinkedIn because {reasoning}",
                                    channel_selected="linkedin",
                                    timing_explanation=decision.get("timing_insight"))

                contact_count = ls.contact_count if ls else 0
                action_type = "dm" if profile.linkedin_dm_enabled and contact_count > 0 else "connect"
                result_text = await send_linkedin_message_tool(db, org_id, lead_data, profile, ai_key, action_type=action_type)
                await _log_action(db, org_id, profile.id, lead.id, "linkedin_sent", "linkedin",
                                  f"LinkedIn {action_type} sent. Profile analysis: {li_analysis.get('profile_summary', '')[:100]}",
                                  result_text)
                await _update_lead_state(db, org_id, lead.id, "contacted_linkedin", "linkedin")
                await update_sdr_status(db, org_id, profile.id, "waiting_for_response",
                                        current_action=f"Waiting for {lead_name} to accept LinkedIn {action_type}",
                                        current_lead_id=lead.id,
                                        increment_linkedin=True,
                                        next_planned_action="Send follow-up DM if connection accepted within 7 days")

    elif action == "make_call" and lead.phone:
        safety = await check_safety_controls(db, org_id, profile, "call")
        if not safety["can_proceed"]:
            await log_activity(db, org_id, profile.id, "ai_call_planned",
                               lead_id=lead.id, channel="phone",
                               summary=f"Call skipped for {lead_name} - safety limit",
                               reasoning=f"Safety limit: {safety['reasons']}", status="skipped")
            await _update_lead_state(db, org_id, lead.id, "researched")
        else:
            allowed, remaining = await rate_limiter.check_call(org_id, profile.max_daily_calls)
            if not allowed:
                await log_activity(db, org_id, profile.id, "ai_call_planned",
                                   lead_id=lead.id, channel="phone",
                                   summary=f"Call skipped - rate limit",
                                   reasoning=f"Rate limit exceeded ({remaining} remaining today)", status="skipped")
                await _update_lead_state(db, org_id, lead.id, "researched")
            else:
                await log_activity(db, org_id, profile.id, "ai_call_planned",
                                   lead_id=lead.id, channel="phone",
                                   summary=f"Call planned for {lead_name}",
                                   reasoning=f"{reasoning}. Timing insight: {decision.get('timing_insight', 'now')}",
                                   next_planned_action="Analyze call outcome and determine next step")
                await _update_lead_state(db, org_id, lead.id, "contacting_call", "phone")
                result_text = await make_call_tool(db, org_id, lead_data, profile, ai_key)
                await log_lead_timeline(db, org_id, lead.id, "call_made",
                                        sdr_profile_id=profile.id,
                                        summary=f"AI call initiated",
                                        channel="phone",
                                        sdr_status_before=state, sdr_status_after="contacted_call")
                await _update_lead_state(db, org_id, lead.id, "contacted_call", "phone")

    elif action == "send_payment" and profile.payment_link:
        await log_activity(db, org_id, profile.id, "payment_sent",
                           lead_id=lead.id,
                           summary=f"Payment link sent to {lead_name}",
                           reasoning=f"{reasoning}. Lead has shown purchase intent",
                           confidence_score=90)
        result_text = await send_payment_tool(db, org_id, lead_data, profile)
        await _update_lead_state(db, org_id, lead.id, "payment_sent")
        await log_lead_timeline(db, org_id, lead.id, "payment_sent",
                                sdr_profile_id=profile.id,
                                summary=f"Payment link sent based on engagement signals",
                                channel="email")

    elif action == "schedule_meeting" and profile.calendar_link:
        await log_activity(db, org_id, profile.id, "meeting_booked",
                           lead_id=lead.id,
                           summary=f"Meeting scheduling initiated for {lead_name}",
                           reasoning=f"{reasoning}. Lead is ready for a meeting",
                           confidence_score=85)
        result_text = await schedule_meeting_tool(db, org_id, lead_data, profile)
        await _update_lead_state(db, org_id, lead.id, "meeting_scheduled")
        await log_lead_timeline(db, org_id, lead.id, "meeting_scheduled",
                                sdr_profile_id=profile.id,
                                summary=f"Meeting scheduled based on positive engagement",
                                channel="email")
        await update_sdr_status(db, org_id, profile.id, "executing",
                                increment_meetings=True,
                                next_planned_action="Prepare for scheduled meeting and send reminder")

    elif action == "linkedin_like":
        if not lead.linkedin_url:
            await _log_action(db, org_id, profile.id, lead.id, "linkedin_like", "linkedin",
                              "No LinkedIn URL available for this lead", "Skipped", "skipped")
        else:
            safety = await check_safety_controls(db, org_id, profile, "linkedin_like")
            if not safety["can_proceed"]:
                await _log_action(db, org_id, profile.id, lead.id, "linkedin_like", "linkedin",
                                  f"Safety limit: {safety['reasons']}", "Skipped", "skipped")
            else:
                await log_activity(db, org_id, profile.id, "linkedin_invite_generated",
                                   lead_id=lead.id, channel="linkedin",
                                   summary=f"Liked LinkedIn content from {lead_name}",
                                   reasoning=f"{reasoning}. Building awareness through social engagement")
                result_text = await linkedin_like_tool(db, org_id, lead_data, profile, ai_key)
                await _update_lead_state(db, org_id, lead.id, "follow_up", "linkedin")

    elif action == "linkedin_comment":
        if not lead.linkedin_url:
            await _log_action(db, org_id, profile.id, lead.id, "linkedin_comment", "linkedin",
                              "No LinkedIn URL available for this lead", "Skipped", "skipped")
        else:
            safety = await check_safety_controls(db, org_id, profile, "linkedin_comment")
            if not safety["can_proceed"]:
                await _log_action(db, org_id, profile.id, lead.id, "linkedin_comment", "linkedin",
                                  f"Safety limit: {safety['reasons']}", "Skipped", "skipped")
            else:
                await log_activity(db, org_id, profile.id, "linkedin_invite_generated",
                                   lead_id=lead.id, channel="linkedin",
                                   summary=f"Commented on LinkedIn content from {lead_name}",
                                   reasoning=f"{reasoning}. Adding value through thoughtful engagement")
                result_text = await linkedin_comment_tool(db, org_id, lead_data, profile, ai_key)
                await _update_lead_state(db, org_id, lead.id, "follow_up", "linkedin")

    elif action == "follow_up":
        followup_type = await decide_followup_type(db, org_id, lead.id, profile,
                                                   ls.contact_count if ls else 0, ai_key)
        await log_activity(db, org_id, profile.id, "followup_scheduled",
                           lead_id=lead.id, channel=channel or "email",
                           summary=f"Follow-up ({followup_type}) scheduled for {lead_name}",
                           reasoning=f"{reasoning}. Followup strategy: {followup_type}",
                           next_planned_action=f"Execute {followup_type} followup after appropriate delay",
                           is_expandable=True)
        await _update_lead_state(db, org_id, lead.id, "follow_up", channel)

    elif action == "close_won":
        await log_activity(db, org_id, profile.id, "lead_won",
                           lead_id=lead.id,
                           summary=f"Deal closed won for {lead_name}",
                           reasoning=f"{reasoning}. Deal successfully closed after engagement sequence",
                           confidence_score=95)
        await log_lead_timeline(db, org_id, lead.id, "closed_won",
                                sdr_profile_id=profile.id,
                                summary="Deal closed won")

    elif action == "close_lost":
        await log_activity(db, org_id, profile.id, "lead_lost",
                           lead_id=lead.id,
                           summary=f"Deal closed lost for {lead_name}",
                           reasoning=f"{reasoning}. Lead did not convert after full sequence")

    elif action == "wait":
        await log_activity(db, org_id, profile.id, "followup_scheduled",
                           lead_id=lead.id,
                           summary=f"Action deferred for {lead_name} - waiting for right timing",
                           reasoning=reasoning,
                           details={"timing_insight": decision.get("timing_insight", "N/A")},
                           next_planned_action="Re-evaluate at next cycle",
                           confidence_score=70)
        await _log_action(db, org_id, profile.id, lead.id, "deferred", None,
                          f"Action deferred: {reasoning}", "Deferred", "pending")

    await db.commit()
