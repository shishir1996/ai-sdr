import httpx
import logging
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


async def get_calendly_user(api_key: str) -> Optional[dict]:
    if not api_key:
        return None
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.calendly.com/users/me",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("resource", {})
        except Exception as e:
            logger.warning("Calendly user fetch failed: %s", e)
    return None


async def list_calendly_event_types(api_key: str) -> list[dict]:
    user = await get_calendly_user(api_key)
    if not user:
        return []
    uri = user.get("uri", "")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.calendly.com/event_types",
                params={"user": uri},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return [
                    {
                        "uri": et.get("uri", ""),
                        "name": et.get("name", ""),
                        "duration": et.get("duration", 30),
                        "active": et.get("active", False),
                        "scheduling_url": et.get("scheduling_url", ""),
                    }
                    for et in resp.json().get("collection", [])
                ]
        except Exception as e:
            logger.warning("Calendly event types fetch failed: %s", e)
    return []


async def create_calendly_scheduling_link(
    event_type_uri: str,
    owner_name: str = "",
    owner_email: str = "",
    api_key: str = "",
) -> dict:
    if not api_key:
        return {"success": False, "error": "Calendly not configured"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.calendly.com/scheduling_links",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "max_event_count": 1,
                    "owner": event_type_uri,
                    "owner_type": "EventType",
                },
                timeout=10,
            )
            if resp.status_code == 201:
                data = resp.json().get("resource", {})
                return {
                    "success": True,
                    "booking_url": data.get("booking_url", ""),
                    "owner": data.get("owner", ""),
                }
            return {"success": False, "error": f"Calendly API error: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def book_calendly_meeting(
    event_type_uri: str,
    invitee_name: str,
    invitee_email: str,
    api_key: str = "",
) -> dict:
    if not api_key:
        return {"success": False, "error": "Calendly not configured"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.calendly.com/scheduled_events",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "event_type": event_type_uri,
                    "invitee": {
                        "name": invitee_name,
                        "email": invitee_email,
                    },
                },
                timeout=10,
            )
            if resp.status_code == 201:
                data = resp.json().get("resource", {})
                return {
                    "success": True,
                    "event_uri": data.get("uri", ""),
                    "start_time": data.get("start_time", ""),
                    "end_time": data.get("end_time", ""),
                    "location": data.get("location", {}),
                    "invitee": data.get("invitee", {}),
                }
            return {"success": False, "error": f"Calendly API error: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
