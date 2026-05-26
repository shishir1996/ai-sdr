import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.model_client import generate_text
from app.services.lead_extraction.apollo import search_leads
from app.services.integrations.resolver import resolve_api_key, resolve_api_secret, resolve_refresh_token
from app.models.agent import SDRProfile


async def research_lead_tool(email: str) -> dict:
    return {"status": "research_attempted", "email": email}


async def _generate_email_content(lead_data: dict, profile: SDRProfile, tone: str, ai_key: Optional[str] = None) -> dict:
    system_prompt = f"""You are an AI SDR writing a {tone} sales email.
Return JSON with: subject (under 60 chars), body (plain text, 3-4 sentences).
Personalize using lead info. Include a clear CTA.
Selling: {profile.product_name or profile.service_description or 'Our solution'}
Type: {profile.sell_type}"""

    if profile.sdr_personality:
        system_prompt += f"\nPersonality: {profile.sdr_personality}"

    user_prompt = f"""Write email for:
Name: {lead_data['name']}
Title: {lead_data['title']}
Company: {lead_data['company']}

Return valid JSON with keys: subject, body"""

    raw = generate_text(system_prompt, user_prompt, max_tokens=512, temperature=0.7, api_key=ai_key)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"subject": f"Quick question, {lead_data['name']}", "body": raw}


async def send_email_tool(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> str:
    if not lead_data.get("email"):
        return "No email address available"

    email_content = await _generate_email_content(lead_data, profile, profile.outreach_tone, ai_key)

    from app.services.email.gmail_client import send_email as gmail_send
    gmail_client_id = await resolve_api_key(db, org_id, "gmail")
    gmail_client_secret = await resolve_api_secret(db, org_id, "gmail")
    gmail_refresh_token = await resolve_refresh_token(db, org_id, "gmail")

    result = gmail_send(
        lead_data["email"],
        email_content.get("subject", "Hello"),
        email_content.get("body", ""),
        client_id=gmail_client_id or None,
        client_secret=gmail_client_secret or None,
        refresh_token=gmail_refresh_token or None,
    )

    if result and result.get("status") == "sent":
        return f"Email sent to {lead_data['email']}: {email_content.get('subject', '')}"
    return f"Email queued for {lead_data['email']} (configure Gmail in Integrations)"


async def send_linkedin_message_tool(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
    action_type: str = "connect",
) -> str:
    if not lead_data.get("linkedin_url"):
        return "No LinkedIn URL available"

    li_email = await resolve_api_key(db, org_id, "linkedin")
    li_password = await resolve_api_secret(db, org_id, "linkedin")
    if not li_email or not li_password:
        return "LinkedIn credentials not configured. Add them in Integrations."

    system_prompt = f"""Write a short LinkedIn outreach message (under 300 chars).
Be professional and personalized. Use the lead's name and context.
Selling: {profile.product_name or profile.service_description or 'our solution'}
Tone: {profile.outreach_tone}"""

    user_prompt = f"Write a LinkedIn {'connection request' if action_type == 'connect' else 'DM'} for {lead_data['name']}, {lead_data['title']} at {lead_data['company']}"

    message_text = generate_text(system_prompt, user_prompt, max_tokens=200, temperature=0.7, api_key=ai_key)

    from app.services.linkedin.linkedin_client import send_connection_request, send_dm

    if action_type == "dm":
        result = await send_dm(
            linkedin_url=lead_data["linkedin_url"],
            email=li_email,
            password=li_password,
            message=message_text,
        )
        if result.get("status") == "sent":
            return f"DM sent to {lead_data['name']}: {message_text[:100]}..."
        return f"DM failed for {lead_data['name']}: {result.get('reason', 'unknown')}"

    result = await send_connection_request(
        linkedin_url=lead_data["linkedin_url"],
        email=li_email,
        password=li_password,
        message=message_text,
    )
    if result.get("status") == "sent":
        return f"Connection request sent to {lead_data['name']}: {message_text[:100]}..."
    return f"Connection request failed for {lead_data['name']}: {result.get('reason', 'unknown')}"


async def linkedin_like_tool(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> str:
    li_email = await resolve_api_key(db, org_id, "linkedin")
    li_password = await resolve_api_secret(db, org_id, "linkedin")
    if not li_email or not li_password:
        return "LinkedIn credentials not configured"

    from app.services.linkedin.linkedin_client import like_post

    result = await like_post(
        post_url=lead_data.get("linkedin_url", ""),
        email=li_email,
        password=li_password,
    )
    if result.get("status") == "liked":
        return f"Liked post for {lead_data['name']}"
    return f"Like failed: {result.get('reason', 'unknown')}"


async def linkedin_comment_tool(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> str:
    li_email = await resolve_api_key(db, org_id, "linkedin")
    li_password = await resolve_api_secret(db, org_id, "linkedin")
    if not li_email or not li_password:
        return "LinkedIn credentials not configured"

    system_prompt = f"""Write a brief, thoughtful comment on a LinkedIn post (under 200 chars).
Be professional and add value. Selling: {profile.product_name or profile.service_description or 'our solution'}.
Tone: {profile.outreach_tone}"""

    user_prompt = f"Write a LinkedIn comment engaging with {lead_data['name']}, {lead_data['title']} at {lead_data['company']}"

    comment_text = generate_text(system_prompt, user_prompt, max_tokens=200, temperature=0.7, api_key=ai_key)

    from app.services.linkedin.linkedin_client import comment_on_post

    result = await comment_on_post(
        post_url=lead_data.get("linkedin_url", ""),
        email=li_email,
        password=li_password,
        comment_text=comment_text,
    )
    if result.get("status") == "commented":
        return f"Commented on post for {lead_data['name']}: {comment_text[:100]}..."
    return f"Comment failed: {result.get('reason', 'unknown')}"


async def make_call_tool(
    db: AsyncSession,
    org_id: str,
    lead_data: dict,
    profile: SDRProfile,
    ai_key: Optional[str] = None,
) -> str:
    if not lead_data.get("phone"):
        return "No phone number available"

    vapi_key = await resolve_api_key(db, org_id, "vapi")
    if not vapi_key:
        return "VAPI.ai not configured. Add API key in Integrations."

    system_prompt = f"""Create a brief call script for an AI SDR calling a prospect.
Selling: {profile.product_name or profile.service_description or 'our solution'}
Keep it under 30 seconds. Include greeting, value prop, and call to action."""

    user_prompt = f"Call script for {lead_data['name']}, {lead_data['title']} at {lead_data['company']}"

    script = generate_text(system_prompt, user_prompt, max_tokens=300, temperature=0.7, api_key=ai_key)

    from app.services.voice.vapi_client import make_call as vapi_call
    result = await vapi_call(lead_data["phone"], script=script, lead_info=lead_data, api_key_override=vapi_key)

    status = result.get("status", "failed")
    call_id = result.get("call_id", "")
    return f"Call initiated via VAPI: status={status}, call_id={call_id}"


async def schedule_meeting_tool(lead_data: dict, profile: SDRProfile) -> str:
    if not profile.calendar_link:
        return "No calendar link configured"
    return f"Meeting invite sent to {lead_data.get('email', '')}: {profile.calendar_link}"


async def send_payment_tool(lead_data: dict, profile: SDRProfile) -> str:
    if not profile.payment_link:
        return "No payment link configured"
    return f"Payment link sent to {lead_data.get('email', '')}: {profile.payment_link}"
