from typing import Any, Optional

import httpx


def _basic_auth(sid: str, token: str) -> str:
    import base64
    return f"Basic {base64.b64encode(f'{sid}:{token}'.encode()).decode()}"


async def validate_twilio_credentials(sid: str, token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
            headers={"Authorization": _basic_auth(sid, token)},
        )
        if r.status_code == 200:
            data = r.json()
            return {"valid": True, "name": data.get("friendly_name", ""), "status": data.get("status", "")}
        if r.status_code == 401:
            return {"valid": False, "error": "Invalid Twilio credentials"}
        return {"valid": False, "error": f"Twilio error: {r.status_code}"}


async def list_twilio_phone_numbers(sid: str, token: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
            headers={"Authorization": _basic_auth(sid, token)},
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return [
            {
                "sid": n.get("sid", ""),
                "phone_number": n.get("phoneNumber", ""),
                "friendly_name": n.get("friendlyName", ""),
                "capabilities": n.get("capabilities", {}),
            }
            for n in data.get("incoming_phone_numbers", [])
        ]


async def check_phone_capabilities(sid: str, token: str, phone_sid: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers/{phone_sid}.json",
            headers={"Authorization": _basic_auth(sid, token)},
        )
        if r.status_code != 200:
            return {"error": "Could not fetch phone number details"}
        n = r.json()
        caps = n.get("capabilities", {})
        return {
            "voice": caps.get("voice", False),
            "sms": caps.get("sms", False),
            "mms": caps.get("mms", False),
            "phone_number": n.get("phoneNumber", ""),
            "friendly_name": n.get("friendlyName", ""),
        }


async def provision_phone_number(sid: str, token: str, area_code: str = "") -> dict:
    area = area_code or "415"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
            headers={
                "Authorization": _basic_auth(sid, token),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"AreaCode": area, "Voice": True},
        )
        if r.status_code != 200:
            return {"error": f"Provision failed: {r.text}"}
        n = r.json()
        return {
            "sid": n.get("sid", ""),
            "phone_number": n.get("phoneNumber", ""),
        }


def format_phone_for_vapi(phone: str) -> str:
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if not cleaned.startswith("+"):
        cleaned = f"+1{cleaned}" if len(cleaned) == 10 else f"+{cleaned}"
    return cleaned
