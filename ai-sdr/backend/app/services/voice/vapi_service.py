import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import get_settings

settings = get_settings()
VAPI_BASE = "https://api.vapi.ai"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def _vapi_get(path: str, api_key: str) -> Any:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{VAPI_BASE}{path}", headers=_headers(api_key))
        if r.status_code == 401:
            return {"error": "Invalid API key", "code": "auth_failed"}
        if r.status_code == 429:
            return {"error": "Rate limited", "code": "rate_limited"}
        r.raise_for_status()
        return r.json()


async def _vapi_post(path: str, api_key: str, data: dict = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{VAPI_BASE}{path}", headers=_headers(api_key), json=data or {})
        if r.status_code in (401, 429):
            return {"error": r.text, "code": "auth_failed" if r.status_code == 401 else "rate_limited"}
        r.raise_for_status()
        return r.json()


async def _vapi_patch(path: str, api_key: str, data: dict = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.patch(f"{VAPI_BASE}{path}", headers=_headers(api_key), json=data or {})
        if r.status_code in (401, 429):
            return {"error": r.text, "code": "auth_failed" if r.status_code == 401 else "rate_limited"}
        r.raise_for_status()
        return r.json()


async def _vapi_delete(path: str, api_key: str) -> Any:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(f"{VAPI_BASE}{path}", headers=_headers(api_key))
        if r.status_code == 401:
            return {"error": "Invalid API key", "code": "auth_failed"}
        r.raise_for_status()
        return r.json() if r.content else {}


# ============================================================
# Connection & Validation
# ============================================================

async def validate_api_key(api_key: str) -> dict:
    result = await _vapi_get("/assistant", api_key)
    if isinstance(result, dict) and result.get("code") == "auth_failed":
        return {"valid": False, "error": "Invalid Vapi API key"}
    return {"valid": True, "assistant_count": len(result) if isinstance(result, list) else 0}


# ============================================================
# Assistants
# ============================================================

DEFAULT_SYSTEM_PROMPT = """You are an AI SDR (Sales Development Representative) calling on behalf of {business_name}.

Your role:
1. Introduce yourself professionally
2. Qualify the prospect by asking discovery questions
3. Handle objections with empathy
4. Identify pain points and interest
5. Book meetings or send follow-up information

Guidelines:
- Keep conversations natural and conversational
- Listen to the prospect and respond appropriately
- If the prospect is not interested, thank them and end politely
- Never make false claims or promises
- Respect do-not-call preferences
- If you don't understand, ask clarifying questions
- Log key information from the conversation

Lead context: {lead_context}

Product/Service: {product_info}"""


async def list_assistants(api_key: str) -> list:
    result = await _vapi_get("/assistant", api_key)
    if isinstance(result, dict) and "error" in result:
        return []
    return result if isinstance(result, list) else []


async def get_assistant(assistant_id: str, api_key: str) -> dict:
    return await _vapi_get(f"/assistant/{assistant_id}", api_key)


async def create_default_assistant(
    api_key: str,
    org_id: str = "",
    business_name: str = "our company",
    product_info: str = "our solutions",
    webhook_url: str = "",
) -> dict:
    prompt = DEFAULT_SYSTEM_PROMPT.format(
        business_name=business_name,
        lead_context="The prospect's name, title, company, and industry will be provided dynamically.",
        product_info=product_info,
    )
    payload = {
        "name": f"AI SDR Assistant - {business_name}",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "systemPrompt": prompt,
            "maxTokens": 300,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "default",
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en",
        },
        "firstMessage": "Hi, this is {name} calling from {company}. Am I speaking with {first_name}?",
        "endCallMessage": "Thank you for your time. Have a great day!",
        "endCallPhrases": ["goodbye", "bye", "thanks", "thank you"],
        "maxDurationSeconds": 300,
        "silenceTimeoutSeconds": 10,
        "backgroundSound": "office",
        "recordingEnabled": True,
        "isAnsweringMachineDetectionEnabled": True,
    }
    if webhook_url:
        payload["server"] = {
            "url": webhook_url,
            "timeoutSeconds": 10,
        }
    payload["serverMessages"] = {
        "transcript": True,
        "summary": True,
        "endOfCallReport": True,
        "statusUpdate": True,
        "hangup": True,
        "recording": True,
    }
    return await _vapi_post("/assistant", api_key, payload)


async def update_assistant(assistant_id: str, api_key: str, updates: dict) -> dict:
    return await _vapi_patch(f"/assistant/{assistant_id}", api_key, updates)


async def delete_assistant(assistant_id: str, api_key: str) -> dict:
    return await _vapi_delete(f"/assistant/{assistant_id}", api_key)


async def auto_create_if_missing(api_key: str, org_id: str, business_name: str = "AI SDR", webhook_url: str = "") -> dict:
    assistants = await list_assistants(api_key)
    for a in assistants:
        if "AI SDR" in a.get("name", ""):
            return {"assistant": a, "created": False}
    created = await create_default_assistant(api_key, org_id, business_name, webhook_url=webhook_url)
    return {"assistant": created, "created": True}


# ============================================================
# Phone Numbers
# ============================================================

async def list_phone_numbers(api_key: str) -> list:
    result = await _vapi_get("/phone-number", api_key)
    if isinstance(result, dict) and "error" in result:
        return []
    return result if isinstance(result, list) else []


async def import_twilio_number(api_key: str, twilio_phone: str, twilio_sid: str, twilio_token: str, assistant_id: str = "") -> dict:
    payload = {
        "provider": "twilio",
        "number": twilio_phone,
        "twilioAccountSid": twilio_sid,
        "twilioAuthToken": twilio_token,
    }
    if assistant_id:
        payload["assistantId"] = assistant_id
    return await _vapi_post("/phone-number", api_key, payload)


async def update_phone_assistant(phone_id: str, api_key: str, assistant_id: str) -> dict:
    return await _vapi_patch(f"/phone-number/{phone_id}", api_key, {"assistantId": assistant_id})


# ============================================================
# Outbound Calls
# ============================================================

async def start_call(
    api_key: str,
    phone_number: str,
    assistant_id: str,
    customer_name: str = "",
    customer_data: dict = None,
    idempotency_key: str = "",
) -> dict:
    payload = {
        "phoneNumber": phone_number,
        "assistantId": assistant_id,
    }
    if customer_name:
        payload["customer"] = {"name": customer_name}
    if customer_data:
        payload.setdefault("customer", {}).update(customer_data)
    if idempotency_key:
        payload["idempotencyKey"] = idempotency_key
    return await _vapi_post("/call", api_key, payload)


async def get_call(call_id: str, api_key: str) -> dict:
    return await _vapi_get(f"/call/{call_id}", api_key)


async def end_call(call_id: str, api_key: str) -> dict:
    return await _vapi_patch(f"/call/{call_id}/end", api_key)


# ============================================================
# Sync helpers
# ============================================================

async def sync_assistants_to_db(api_key: str, db_session, org_id: str) -> list[dict]:
    from app.models.voice import VoiceAgent
    assistants = await list_assistants(api_key)
    synced = []
    for a in assistants:
        existing = await db_session.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(VoiceAgent).where(
                VoiceAgent.vapi_assistant_id == a["id"],
                VoiceAgent.org_id == org_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        agent = VoiceAgent(
            org_id=org_id,
            name=a.get("name", "Synced Assistant"),
            vapi_assistant_id=a["id"],
            ai_model=a.get("model", {}).get("model", "gpt-4o-mini"),
            voice_provider=a.get("voice", {}).get("provider", "11labs"),
            voice_id=a.get("voice", {}).get("voiceId", "default"),
            system_prompt=a.get("model", {}).get("systemPrompt", ""),
            is_active=True,
        )
        db_session.add(agent)
        synced.append(agent)
    await db_session.flush()
    return synced


async def sync_phone_numbers_to_db(api_key: str) -> list[dict]:
    return await list_phone_numbers(api_key)


async def sync_call_logs(api_key: str, db_session, org_id: str, since: str = "") -> list[dict]:
    from app.models.voice import CallRecord
    params = {"limit": 100}
    if since:
        params["since"] = since
    result = await _vapi_get("/call", api_key)
    if isinstance(result, dict) and "error" in result:
        return []
    calls = result if isinstance(result, list) else []
    synced = []
    for c in calls:
        existing = await db_session.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(CallRecord).where(
                CallRecord.vapi_call_id == c["id"],
                CallRecord.org_id == org_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        record = CallRecord(
            org_id=org_id,
            vapi_call_id=c.get("id"),
            phone_number=c.get("customer", {}).get("number", ""),
            direction="outbound",
            status=c.get("status", "unknown"),
            duration_seconds=c.get("durationSeconds"),
            cost=c.get("cost"),
            outcome=c.get("analysis", {}).get("summary", ""),
            transcript=c.get("transcript"),
            recording_url=c.get("recordingUrl"),
            ai_summary=c.get("analysis", {}).get("summary", ""),
            voicemail_detected=c.get("answeringMachineDetected"),
            called_at=datetime.fromisoformat(c["createdAt"].replace("Z", "+00:00")) if c.get("createdAt") else None,
        )
        db_session.add(record)
        synced.append(record)
    await db_session.flush()
    return synced


# ============================================================
# Webhook verification
# ============================================================

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def extract_webhook_event(body: dict) -> dict:
    event_type = body.get("type", body.get("message", body.get("status", "unknown")))
    call_data = body.get("call", body.get("message", {}).get("call", body))
    return {
        "type": event_type,
        "call_id": call_data.get("id", body.get("callId", "")),
        "status": call_data.get("status", body.get("status", "")),
        "data": call_data,
        "raw": body,
    }
