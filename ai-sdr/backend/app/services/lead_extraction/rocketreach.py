import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def enrich_lead(
    email: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    domain: Optional[str] = None,
    api_key: str = "",
) -> dict:
    if not api_key:
        logger.warning("RocketReach API key not configured")
        return {}

    async with httpx.AsyncClient() as client:
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

        if email:
            payload = {"email": email}
            try:
                resp = await client.post(
                    "https://api.rocketreach.co/v1/api/lookupProfile",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return _parse_profile(data)
            except Exception as e:
                logger.warning("RocketReach email lookup failed: %s", e)

        if linkedin_url:
            payload = {"linkedin_url": linkedin_url}
            try:
                resp = await client.post(
                    "https://api.rocketreach.co/v1/api/lookupProfile",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return _parse_profile(data)
            except Exception as e:
                logger.warning("RocketReach LinkedIn lookup failed: %s", e)

    return {}


def _parse_profile(data: dict) -> dict:
    profile = data.get("profile", {}) or data
    return {
        "first_name": profile.get("first_name", "") or profile.get("name", "").split(" ")[0] if profile.get("name") else "",
        "last_name": profile.get("last_name", "") or (profile.get("name", "").split(" ")[-1] if profile.get("name") else ""),
        "title": profile.get("current_work", [{}])[0].get("title", "") if profile.get("current_work") else profile.get("title", ""),
        "company": profile.get("current_work", [{}])[0].get("company", "") if profile.get("current_work") else profile.get("company", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", "") or profile.get("mobile_phone", ""),
        "linkedin_url": profile.get("linkedin_url", ""),
        "industry": profile.get("industry", ""),
        "location": f"{profile.get('city', '')}, {profile.get('state', '')}".strip(", "),
        "source": "rocketreach",
    }


async def search_people(
    query: str,
    page: int = 1,
    api_key: str = "",
) -> list[dict]:
    if not api_key:
        return []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.rocketreach.co/v1/api/search",
                params={"query": query, "page": page, "page_size": 25},
                headers={"api-key": api_key},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                profiles = data.get("profiles", []) or data.get("results", [])
                return [_parse_profile(p) for p in profiles]
        except Exception as e:
            logger.warning("RocketReach search failed: %s", e)
    return []
