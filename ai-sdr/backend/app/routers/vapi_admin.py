import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.voice import VoiceAgent, CallRecord, CallAnalytics
from app.models.integration import Integration
from app.utils.auth import get_current_admin
from app.utils.crypto import encrypt_value, decrypt_value
from app.services.integrations.service import get_api_key, set_integration, get_integration
from app.services.voice.vapi_service import (
    validate_api_key, list_assistants, create_default_assistant,
    auto_create_if_missing, list_phone_numbers, get_call,
    sync_assistants_to_db, sync_phone_numbers_to_db, sync_call_logs,
    start_call,
)
from app.services.voice.twilio_service import (
    validate_twilio_credentials, list_twilio_phone_numbers,
    check_phone_capabilities, format_phone_for_vapi,
)
from app.services.voice.call_campaign_service import process_queue, enqueue_leads

router = APIRouter(prefix="/admin/calling", tags=["vapi_admin"])


# ============================================================
# Status / Connectivity
# ============================================================

@router.get("/status")
async def calling_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    vapi = await get_integration(db, user.org_id, "vapi")
    vapi_key = await get_api_key(db, user.org_id, "vapi") if vapi else ""

    twilio = await get_integration(db, user.org_id, "twilio")
    twilio_sid = await get_api_key(db, user.org_id, "twilio") if twilio else ""
    twilio_token = await get_api_key(db, user.org_id, "twilio") if twilio else ""

    vapi_valid = False
    vapi_assistants = 0
    vapi_phones = 0
    if vapi_key:
        try:
            vresult = await validate_api_key(vapi_key)
            vapi_valid = vresult.get("valid", False)
            if vapi_valid:
                vapi_assistants = vresult.get("assistant_count", 0)
                phones = await list_phone_numbers(vapi_key)
                vapi_phones = len(phones)
        except Exception:
            pass

    twilio_valid = False
    twilio_phones = []
    if twilio_sid and twilio_token:
        try:
            tresult = await validate_twilio_credentials(twilio_sid, twilio_token)
            twilio_valid = tresult.get("valid", False)
            if twilio_valid:
                twilio_phones = await list_twilio_phone_numbers(twilio_sid, twilio_token)
        except Exception:
            pass

    agents_result = await db.execute(
        select(VoiceAgent).where(VoiceAgent.org_id == user.org_id)
    )
    agents = agents_result.scalars().all()

    return {
        "vapi": {
            "configured": bool(vapi and vapi_key),
            "connected": vapi_valid,
            "assistants_count": vapi_assistants,
            "phone_numbers_count": vapi_phones,
        },
        "twilio": {
            "configured": bool(twilio and twilio_sid and twilio_token),
            "connected": twilio_valid,
            "available_numbers": twilio_phones,
        },
        "voice_agents": [
            {
                "id": a.id,
                "name": a.name,
                "vapi_assistant_id": a.vapi_assistant_id,
                "is_active": a.is_active,
                "is_default": a.is_default,
                "ai_model": a.ai_model,
                "voice_provider": a.voice_provider,
            }
            for a in agents
        ],
        "kill_switch": False,
    }


# ============================================================
# Vapi Connection
# ============================================================

@router.post("/connect/vapi")
async def connect_vapi(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    body = await request.json()
    api_key = body.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required")

    result = await validate_api_key(api_key)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid Vapi API key"))

    await set_integration(db, user.org_id, "vapi", api_key=api_key, is_active=True)
    return {"status": "connected", "detail": "Vapi API key validated and saved"}


@router.post("/connect/twilio")
async def connect_twilio(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    body = await request.json()
    sid = body.get("account_sid", "")
    token = body.get("auth_token", "")
    if not sid or not token:
        raise HTTPException(status_code=400, detail="Account SID and Auth Token required")

    result = await validate_twilio_credentials(sid, token)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid Twilio credentials"))

    await set_integration(
        db, user.org_id, "twilio",
        api_key=sid,
        api_secret=token,
        is_active=True,
    )
    return {"status": "connected", "detail": "Twilio credentials validated and saved"}


# ============================================================
# Assistants
# ============================================================

@router.get("/assistants")
async def list_voice_assistants(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(VoiceAgent).where(VoiceAgent.org_id == user.org_id).order_by(VoiceAgent.created_at.desc())
    )
    return [
        {
            "id": a.id,
            "name": a.name,
            "vapi_assistant_id": a.vapi_assistant_id,
            "ai_model": a.ai_model,
            "voice_provider": a.voice_provider,
            "voice_id": a.voice_id,
            "is_active": a.is_active,
            "is_default": a.is_default,
            "system_prompt": a.system_prompt,
            "first_message": a.first_message,
            "temperature": a.temperature,
            "max_duration_seconds": a.max_duration_seconds,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().all()
    ]


@router.post("/assistants/auto-create")
async def auto_create_assistant(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    vapi_key = await get_api_key(db, user.org_id, "vapi")
    if not vapi_key:
        raise HTTPException(status_code=400, detail="Vapi API key not configured")

    webhook_url = ""
    from app.config import get_settings
    settings = get_settings()
    if settings.IS_PRODUCTION:
        webhook_url = "https://api.offdx.in/api/v1/calling/webhook"

    result = await auto_create_if_missing(vapi_key, user.org_id, "AI SDR", webhook_url)
    assistant = result.get("assistant", {})

    if assistant.get("id"):
        existing = await db.execute(
            select(VoiceAgent).where(
                VoiceAgent.vapi_assistant_id == assistant["id"],
                VoiceAgent.org_id == user.org_id,
            )
        )
        if not existing.scalar_one_or_none():
            agent = VoiceAgent(
                org_id=user.org_id,
                name=assistant.get("name", "AI SDR Assistant"),
                vapi_assistant_id=assistant["id"],
                ai_model=assistant.get("model", {}).get("model", "gpt-4o-mini"),
                voice_provider=assistant.get("voice", {}).get("provider", "11labs"),
                voice_id=assistant.get("voice", {}).get("voiceId", "default"),
                system_prompt=assistant.get("model", {}).get("systemPrompt", ""),
                first_message=assistant.get("firstMessage", ""),
                temperature=assistant.get("model", {}).get("temperature", 0.7),
                is_active=True,
                is_default=True,
            )
            db.add(agent)
            await db.flush()

    return {"result": result, "message": "Assistant created" if result.get("created") else "Assistant already exists"}


# ============================================================
# Twilio Import
# ============================================================

@router.post("/twilio/import-number")
async def import_twilio_number(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    body = await request.json()
    phone_number = body.get("phone_number", "")
    assistant_id = body.get("assistant_id", "")

    if not phone_number:
        raise HTTPException(status_code=400, detail="Phone number required")

    import httpx
    from app.services.voice.vapi_service import _headers

    vapi_key = await get_api_key(db, user.org_id, "vapi")
    if not vapi_key:
        raise HTTPException(status_code=400, detail="Vapi API key not configured")

    integration = await get_integration(db, user.org_id, "twilio")
    if not integration:
        raise HTTPException(status_code=400, detail="Twilio not configured")

    twilio_sid = await get_api_key(db, user.org_id, "twilio")
    twilio_token = await get_api_key(db, user.org_id, "twilio")

    formatted = format_phone_for_vapi(phone_number)
    payload = {
        "provider": "twilio",
        "number": formatted,
        "twilioAccountSid": twilio_sid,
        "twilioAuthToken": twilio_token,
    }
    if assistant_id:
        agent_result = await db.execute(
            select(VoiceAgent).where(VoiceAgent.id == assistant_id, VoiceAgent.org_id == user.org_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent and agent.vapi_assistant_id:
            payload["assistantId"] = agent.vapi_assistant_id

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.vapi.ai/phone-number",
            headers=_headers(vapi_key),
            json=payload,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail=f"Vapi import failed: {r.text}")
        return {"status": "imported", "data": r.json()}


# ============================================================
# Calls
# ============================================================

class TestCallRequest(BaseModel):
    phone_number: str
    voice_agent_id: Optional[str] = None
    assistant_id: Optional[str] = None


@router.post("/test-call")
async def make_test_call(
    body: TestCallRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    vapi_key = await get_api_key(db, user.org_id, "vapi")
    if not vapi_key:
        raise HTTPException(status_code=400, detail="Vapi not configured")

    assistant_id = body.assistant_id or ""
    if not assistant_id and body.voice_agent_id:
        agent_result = await db.execute(
            select(VoiceAgent).where(VoiceAgent.id == body.voice_agent_id, VoiceAgent.org_id == user.org_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            assistant_id = agent.vapi_assistant_id or ""

    if not assistant_id:
        raise HTTPException(status_code=400, detail="No assistant configured. Auto-create one first.")

    result = await start_call(vapi_key, body.phone_number, assistant_id, customer_name="Test User")
    return result


# ============================================================
# Sync
# ============================================================

@router.post("/sync")
async def sync_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    vapi_key = await get_api_key(db, user.org_id, "vapi")
    if not vapi_key:
        raise HTTPException(status_code=400, detail="Vapi not configured")

    agents = await sync_assistants_to_db(vapi_key, db, user.org_id)
    phones = await sync_phone_numbers_to_db(vapi_key)
    calls = await sync_call_logs(vapi_key, db, user.org_id)

    return {
        "agents_synced": len(agents),
        "phones_found": len(phones),
        "call_logs_synced": len(calls),
    }


# ============================================================
# Kill Switch
# ============================================================

@router.post("/kill-switch")
async def toggle_kill_switch(
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    integration = await get_integration(db, user.org_id, "vapi")
    if integration:
        integration.is_active = not enabled
        await db.flush()
    return {"kill_switch": enabled, "calling_disabled": enabled}
