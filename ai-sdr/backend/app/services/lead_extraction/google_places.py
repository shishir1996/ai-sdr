import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def search_places(
    query: str,
    location: str,
    api_key: str,
    radius: int = 50000,
) -> list[dict]:
    if not api_key:
        logger.warning("Google Places API key not configured")
        return []

    businesses = []
    async with httpx.AsyncClient() as client:
        text_search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"{query} in {location}",
            "key": api_key,
            "radius": radius,
        }
        try:
            resp = await client.get(text_search_url, params=params, timeout=15)
            data = resp.json()
            if data.get("status") != "OK":
                logger.warning("Google Places API error: %s — %s", data.get("status"), data.get("error_message", ""))
                return []
            for place in data.get("results", []):
                place_id = place.get("place_id", "")
                details = await _get_place_details(place_id, api_key, client)
                businesses.append({
                    "name": place.get("name", ""),
                    "address": place.get("formatted_address", ""),
                    "rating": str(place.get("rating", "")),
                    "reviews": str(place.get("user_ratings_total", "")),
                    "phone": details.get("phone", ""),
                    "website": details.get("website", ""),
                    "category": (place.get("types") or [""])[0] if place.get("types") else "",
                    "place_id": place_id,
                    "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                    "source": "google_business",
                })
        except Exception as e:
            logger.error("Google Places API request failed: %s", e)
    return businesses


async def _get_place_details(place_id: str, api_key: str, client: httpx.AsyncClient) -> dict:
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,website,opening_hours",
        "key": api_key,
    }
    try:
        resp = await client.get(details_url, params=params, timeout=10)
        data = resp.json()
        result = data.get("result", {})
        return {
            "phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "hours": result.get("opening_hours", {}).get("weekday_text", []) if result.get("opening_hours") else [],
        }
    except Exception:
        return {}
