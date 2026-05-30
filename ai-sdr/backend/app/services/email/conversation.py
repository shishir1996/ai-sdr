import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import EmailMessage

logger = logging.getLogger(__name__)


async def store_reply(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    from_email: str,
    subject: str,
    body_snippet: str,
    message_id: str,
    rfc_message_id: str,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> EmailMessage:
    msg = EmailMessage(
        org_id=org_id,
        lead_id=lead_id,
        from_email=from_email,
        to_email="",
        subject=subject,
        body_html=body_snippet,
        status="received",
        direction="inbound",
        message_id=message_id,
        rfc_message_id=rfc_message_id,
        in_reply_to=in_reply_to,
        references=references,
        thread_id=thread_id,
        replied_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    await db.flush()

    if in_reply_to:
        orig_result = await db.execute(
            select(EmailMessage).where(
                EmailMessage.org_id == org_id,
                EmailMessage.message_id == in_reply_to,
            )
        )
        orig = orig_result.scalar_one_or_none()
        if orig:
            orig.replied_at = datetime.now(timezone.utc)
            await db.flush()

    return msg


async def build_conversation_context(
    db: AsyncSession,
    org_id: str,
    lead_id: str,
    max_messages: int = 10,
) -> list[dict]:
    result = await db.execute(
        select(EmailMessage)
        .where(
            EmailMessage.org_id == org_id,
            EmailMessage.lead_id == lead_id,
        )
        .order_by(EmailMessage.created_at.asc())
        .limit(max_messages)
    )
    messages = result.scalars().all()
    return [
        {
            "direction": m.direction,
            "subject": m.subject,
            "body": m.body_html,
            "sent_at": m.created_at.isoformat() if m.created_at else "",
        }
        for m in messages
    ]


async def analyze_reply(
    conversation_context: list[dict],
    ai_key: Optional[str] = None,
) -> dict:
    system_prompt = """You are an AI SDR analyzing a lead's email reply in a sales conversation.
Analyze the latest message and return JSON with:
- sentiment: one of [positive, neutral, negative]
- intent: one of [interested, needs_info, not_interested, meeting, payment, other]
- suggested_next_action: one of [provide_details, schedule_meeting, send_payment, end_followup, wait]
- reasoning: brief explanation

Rules:
- "interested" intent -> suggest schedule_meeting or send_payment
- "needs_info" intent -> suggest provide_details and continue follow-up
- "not_interested" intent -> suggest end_followup (polite close)
- "meeting" intent -> suggest schedule_meeting
- "payment" intent -> suggest send_payment
- If sentiment is positive but intent is unclear, suggest schedule_meeting
- If sentiment is negative, suggest end_followup"""

    user_prompt = f"Conversation history:\n{json.dumps(conversation_context, indent=2)}\n\nAnalyze the latest lead reply and return valid JSON."

    from app.services.ai.model_client import generate_text_async
    try:
        raw = await generate_text_async(system_prompt, user_prompt, max_tokens=256, temperature=0.3, api_key=ai_key)
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Failed to analyze reply: {e}")
        return {
            "sentiment": "neutral",
            "intent": "other",
            "suggested_next_action": "wait",
            "reasoning": "Failed to analyze, defaulting to wait",
        }
