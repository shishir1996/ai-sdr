import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.voice import CallRecord, AiSummary
from app.models.lead import Lead
from app.services.integrations.service import get_integration
from app.utils.crypto import decrypt_value

router = APIRouter(prefix="/calling", tags=["webhooks"])


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body_bytes = await request.body()
    signature = request.headers.get("x-vapi-signature", "")
    body = await request.json() if body_bytes else {}

    event_type = body.get("type", body.get("message", body.get("status", "unknown")))
    call_data = body.get("call", body.get("message", {}).get("call", body))
    vapi_call_id = call_data.get("id", body.get("callId", ""))

    if not vapi_call_id:
        return {"status": "ignored", "reason": "no call_id"}

    result = await db.execute(select(CallRecord).where(CallRecord.vapi_call_id == vapi_call_id))
    record = result.scalar_one_or_none()
    if not record:
        return {"status": "ignored", "reason": "call_record_not_found"}

    try:
        integration = await get_integration(db, record.org_id, "vapi")
        if integration and integration.api_key_encrypted:
            secret = decrypt_value(integration.api_key_encrypted)
            expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            if signature and not hmac.compare_digest(expected, signature):
                pass
    except Exception:
        pass

    updates = {}

    if call_data.get("status"):
        updates["status"] = call_data["status"]

    if call_data.get("durationSeconds"):
        updates["duration_seconds"] = call_data["durationSeconds"]

    if call_data.get("cost"):
        updates["cost"] = call_data["cost"]

    if call_data.get("recordingUrl"):
        updates["recording_url"] = call_data["recordingUrl"]

    if call_data.get("transcript"):
        updates["transcript"] = call_data["transcript"]

    if call_data.get("answeringMachineDetected") is not None:
        updates["voicemail_detected"] = call_data["answeringMachineDetected"]

    analysis = call_data.get("analysis", {})
    if analysis.get("summary"):
        updates["ai_summary"] = analysis["summary"]
        updates["outcome"] = analysis.get("summary", "")[:200]

    if analysis.get("sentiment"):
        updates["sentiment"] = analysis["sentiment"]

    if call_data.get("endedAt"):
        updates["ended_at"] = datetime.fromisoformat(call_data["endedAt"].replace("Z", "+00:00"))

    if updates:
        for key, val in updates.items():
            setattr(record, key, val)
        await db.flush()

    if updates.get("ai_summary") or call_data.get("transcript"):
        summary = AiSummary(
            org_id=record.org_id,
            call_record_id=record.id,
            lead_id=record.lead_id,
            summary=updates.get("ai_summary", ""),
            transcript_summary=call_data.get("transcript", "")[:500],
            key_points=analysis.get("keyPoints", []),
            action_items=analysis.get("actionItems", []),
            sentiment_analysis={"sentiment": analysis.get("sentiment", "")},
            qualification_score=50 if analysis.get("summary") else None,
        )
        db.add(summary)
        await db.flush()

    return {"status": "processed", "call_id": vapi_call_id, "updates": updates}


@router.post("/webhook/status")
async def status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    return vapi_webhook(request, db)
