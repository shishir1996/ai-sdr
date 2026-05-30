import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import LeadState, AgentLog
from app.models.campaign import EmailMessage
from app.models.lead import Lead
from app.models.agent import SDRProfile
from app.services.email.conversation import store_reply, build_conversation_context, analyze_reply
from app.services.integrations.resolver import resolve_api_key, resolve_api_secret, resolve_refresh_token
from app.services.ai.model_client import generate_text, generate_text_async

logger = logging.getLogger(__name__)


async def _update_state(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    new_state: str,
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
    await db.flush()


async def _log(
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


async def handle_reply(
    db: AsyncSession,
    org_id: str,
    lead: Lead,
    lead_data: dict,
    profile: SDRProfile,
    reply: dict,
    ai_key: Optional[str] = None,
) -> str:
    rfc_message_id = reply.get("rfc_message_id", reply.get("message_id", ""))
    in_reply_to = reply.get("in_reply_to", "")
    references = reply.get("references", "") or in_reply_to
    thread_id = reply.get("thread_id", "")

    msg = await store_reply(
        db=db,
        org_id=org_id,
        lead_id=lead.id,
        from_email=reply.get("from", lead.email or ""),
        subject=reply.get("subject", ""),
        body_snippet=reply.get("snippet", ""),
        message_id=reply.get("message_id", ""),
        rfc_message_id=rfc_message_id,
        in_reply_to=in_reply_to,
        references=references,
        thread_id=thread_id,
    )

    context = await build_conversation_context(db, org_id, lead.id)

    analysis = await analyze_reply(context, ai_key)
    sentiment = analysis.get("sentiment", "neutral")
    intent = analysis.get("intent", "other")
    next_action = analysis.get("suggested_next_action", "wait")
    analysis_reasoning = analysis.get("reasoning", "")

    system_prompt = f"""You are an AI SDR replying to a lead's email.
Conversation sentiment: {sentiment}
Lead intent: {intent}
Next action: {next_action}

Selling: {profile.product_name or profile.service_description or 'our solution'}
Type: {profile.sell_type}
Tone: {profile.outreach_tone}

Write a professional email reply (3-5 sentences). Address the lead's specific points.
Return JSON with keys: subject, body"""

    user_prompt = f"Conversation:\n{json.dumps(context, indent=2)}\n\nLatest reply: {reply.get('snippet', '')}\n\nWrite reply JSON."

    try:
        raw = await generate_text_async(system_prompt, user_prompt, max_tokens=512, temperature=0.7, api_key=ai_key)
        email_content = json.loads(raw)
    except Exception:
        email_content = {
            "subject": f"Re: {reply.get('subject', '')}",
            "body": f"Thank you for your response. {analysis_reasoning}",
        }

    subject = email_content.get("subject", f"Re: {reply.get('subject', '')}")
    body = email_content.get("body", "")

    sdr_creds = None
    if profile.email_credentials_encrypted:
        from app.services.sdr.credentials import decrypt_sdr_credentials
        sdr_creds = decrypt_sdr_credentials(profile.email_credentials_encrypted)

    gmail_client_id = None
    gmail_secret = None
    gmail_refresh = None
    smtp_host = None
    smtp_port = None
    smtp_use_ssl = None
    smtp_use_tls = None
    smtp_username = None
    smtp_password = None
    smtp_sender_email = None
    smtp_sender_name = None

    if sdr_creds:
        if sdr_creds.get("provider") == "gmail":
            gmail_client_id = sdr_creds.get("client_id")
            gmail_secret = sdr_creds.get("client_secret")
            gmail_refresh = sdr_creds.get("refresh_token")
        elif sdr_creds.get("provider") == "smtp":
            smtp_host = sdr_creds.get("host")
            smtp_port = sdr_creds.get("port", 587)
            smtp_use_ssl = sdr_creds.get("use_ssl", False)
            smtp_use_tls = sdr_creds.get("use_tls", True)
            smtp_username = sdr_creds.get("username")
            smtp_password = sdr_creds.get("password")
            smtp_sender_email = sdr_creds.get("sender_email") or sdr_creds.get("username")
            smtp_sender_name = sdr_creds.get("sender_name", "AI SDR")

    if not gmail_client_id or not gmail_refresh:
        gmail_client_id = await resolve_api_key(db, org_id, "gmail")
        gmail_secret = await resolve_api_secret(db, org_id, "gmail")
        gmail_refresh = await resolve_refresh_token(db, org_id, "gmail")

    reply_sent = False
    outbound_msg_id = ""

    if gmail_client_id and gmail_refresh and lead.email:
        from app.services.email.gmail_client import send_email as gmail_send
        result = gmail_send(
            lead.email,
            subject,
            body,
            client_id=gmail_client_id,
            client_secret=gmail_secret,
            refresh_token=gmail_refresh,
            in_reply_to=rfc_message_id,
            references=references,
            thread_id=thread_id,
        )
        if result and result.get("status") == "sent":
            reply_sent = True
            outbound_msg_id = result.get("message_id", "")
    elif smtp_host and smtp_username and lead.email:
        from app.services.email.smtp_service import SMTPSender
        from app.models.smtp import SMTPConfig
        import uuid
        temp_cfg = SMTPConfig(
            id=str(uuid.uuid4()),
            org_id=org_id,
            host=smtp_host,
            port=smtp_port or 587,
            use_ssl=smtp_use_ssl or False,
            use_tls=smtp_use_tls or True,
            username=smtp_username,
            password_encrypted=smtp_password or "",
            sender_name=smtp_sender_name or "AI SDR",
            sender_email=smtp_sender_email or lead.from_email or "",
            is_active=False,
        )
        from app.utils.crypto import encrypt_value
        temp_cfg.password_encrypted = encrypt_value(smtp_password or "")
        sender = SMTPSender(temp_cfg)
        result = await sender.send(lead.email, subject, body)
        if result.get("success"):
            reply_sent = True
            outbound_msg_id = f"smtp-{uuid.uuid4().hex[:12]}"
    else:
        from app.services.email.smtp_service import send_email_via_smtp
        result = await send_email_via_smtp(db, org_id, lead.email, subject, body)
        if result.get("success"):
            reply_sent = True
            outbound_msg_id = "smtp-global"

    if reply_sent:
        reply_msg = EmailMessage(
            org_id=org_id,
            lead_id=lead.id,
            from_email="",
            to_email=lead.email,
            subject=subject,
            body_html=body,
            status="sent",
            direction="outbound",
            message_id=outbound_msg_id,
            in_reply_to=rfc_message_id,
            references=references,
            thread_id=thread_id or "",
        )
        db.add(reply_msg)
        await db.flush()

    if next_action == "schedule_meeting":
        await _update_state(db, org_id, lead.id, "meeting_scheduled")
        result_text = f"AI analyzed reply ({sentiment}/{intent}): {analysis_reasoning}. Lead interested, suggested meeting."
        if profile.calendar_link:
            result_text += f" Calendar: {profile.calendar_link}"
    elif next_action == "send_payment":
        await _update_state(db, org_id, lead.id, "payment_sent")
        result_text = f"AI analyzed reply ({sentiment}/{intent}): {analysis_reasoning}. Sent payment link."
    elif next_action == "provide_details":
        await _update_state(db, org_id, lead.id, "follow_up")
        result_text = f"AI analyzed reply ({sentiment}/{intent}): {analysis_reasoning}. Provided details, continuing follow-up."
    elif next_action == "end_followup":
        await _update_state(db, org_id, lead.id, "closed_lost")
        result_text = f"AI analyzed reply ({sentiment}/{intent}): {analysis_reasoning}. Lead closed politely."
    else:
        await _update_state(db, org_id, lead.id, "follow_up")
        result_text = f"AI analyzed reply ({sentiment}/{intent}): {analysis_reasoning}. Following up."

    await _log(db, org_id, lead.id, "reply_handled", "email", analysis_reasoning, result_text)

    return result_text
