import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def enrich_lead(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    company: Optional[str] = None,
    api_key: str = "",
) -> dict:
    if not api_key:
        logger.warning("Lusha API key not configured")
        return {}

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if email:
            payload = {"email": email}
            try:
                resp = await client.post(
                    "https://api.lusha.com/person",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return _parse_person(data)
            except Exception as e:
                logger.warning("Lusha email lookup failed: %s", e)

        if phone:
            payload = {"phone": phone}
            try:
                resp = await client.post(
                    "https://api.lusha.com/person",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return _parse_person(data)
            except Exception as e:
                logger.warning("Lusha phone lookup failed: %s", e)

    return {}


def _parse_person(data: dict) -> dict:
    person = data.get("data", {})
    return {
        "first_name": person.get("firstName", ""),
        "last_name": person.get("lastName", ""),
        "title": person.get("title", ""),
        "company": person.get("company", {}).get("name", "") if person.get("company") else "",
        "email": (
            next((e.get("email", "") for e in (person.get("emails") or []) if e.get("email")), "")
        ),
        "phone": (
            next((p.get("phoneNumber", "") for p in (person.get("phones") or []) if p.get("phoneNumber")), "")
        ),
        "industry": person.get("company", {}).get("industry", "") if person.get("company") else "",
        "location": f"{person.get('city', '')}, {person.get('state', '')}".strip(", "),
        "source": "lusha",
    }


async def search_company(company_name: str, api_key: str = "") -> list[dict]:
    if not api_key:
        return []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.lusha.com/company",
                json={"name": company_name},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [{
                    "company": company_name,
                    "industry": data.get("data", {}).get("industry", ""),
                    "company_size": str(data.get("data", {}).get("size", "")),
                    "website": data.get("data", {}).get("website", ""),
                    "source": "lusha",
                }]
        except Exception as e:
            logger.warning("Lusha company search failed: %s", e)
    return []
