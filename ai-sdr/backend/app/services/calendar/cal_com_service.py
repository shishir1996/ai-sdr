import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def get_cal_com_user(api_key: str) -> Optional[dict]:
    if not api_key:
        return None
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.cal.com/v1/memberships",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                memberships = resp.json().get("memberships", [])
                if memberships:
                    return memberships[0]
        except Exception as e:
            logger.warning("Cal.com user fetch failed: %s", e)
    return None


async def list_cal_com_event_types(api_key: str) -> list[dict]:
    if not api_key:
        return []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.cal.com/v1/event-types",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return [
                    {
                        "id": et.get("id", 0),
                        "title": et.get("title", ""),
                        "slug": et.get("slug", ""),
                        "length": et.get("length", 30),
                        "description": et.get("description", ""),
                        "scheduling_url": f"https://cal.com/{et.get('slug', '')}" if et.get("slug") else "",
                    }
                    for et in resp.json().get("event_types", [])
                ]
        except Exception as e:
            logger.warning("Cal.com event types fetch failed: %s", e)
    return []


async def book_cal_com_meeting(
    event_type_id: int,
    attendee_name: str,
    attendee_email: str,
    start_time: str,
    api_key: str = "",
) -> dict:
    if not api_key:
        return {"success": False, "error": "Cal.com not configured"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.cal.com/v1/bookings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "eventTypeId": event_type_id,
                    "start": start_time,
                    "attendee": [
                        {
                            "name": attendee_name,
                            "email": attendee_email,
                            "timeZone": "UTC",
                        }
                    ],
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                booking = data if isinstance(data, dict) else {}
                return {
                    "success": True,
                    "booking_uid": booking.get("uid", ""),
                    "booking_url": f"https://cal.com/booking/{booking.get('uid', '')}" if booking.get("uid") else "",
                    "start_time": booking.get("startTime", ""),
                    "end_time": booking.get("endTime", ""),
                    "attendees": booking.get("attendees", []),
                }
            return {"success": False, "error": f"Cal.com API error: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
