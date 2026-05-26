import httpx
from typing import Any, Optional

from app.config import get_settings

settings = get_settings()


async def make_call(
    phone_number: str,
    script: Optional[str] = None,
    lead_info: Optional[dict[str, Any]] = None,
    api_key_override: Optional[str] = None,
) -> dict[str, Any]:
    api_key = api_key_override or settings.VAPI_API_KEY
    if not api_key:
        return {"status": "error", "error": "VAPI API key not configured"}

    payload: dict[str, Any] = {
        "phoneNumber": phone_number,
        "assistant": {
            "model": {
                "provider": "together",
                "model": settings.TOGETHER_MODEL,
            },
        },
    }

    if lead_info:
        payload["customer"] = {
            "name": f"{lead_info.get('first_name', '')} {lead_info.get('last_name', '')}".strip(),
            "company": lead_info.get("company", ""),
        }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.VAPI_BASE_URL}/call",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        data = resp.json()
        return {
            "call_id": data.get("id"),
            "status": data.get("status", "initiated"),
            "cost": data.get("cost"),
        }


async def get_call_log(call_id: str, api_key_override: Optional[str] = None) -> dict[str, Any]:
    api_key = api_key_override or settings.VAPI_API_KEY
    if not api_key:
        return {"status": "error", "error": "VAPI API key not configured"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.VAPI_BASE_URL}/call/{call_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return resp.json()
