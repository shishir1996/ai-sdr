import httpx
from typing import Any, Optional

from app.config import get_settings

settings = get_settings()


async def search_leads(criteria: dict, api_key_override: Optional[str] = None) -> list[dict]:
    api_key = api_key_override or settings.APOLLO_API_KEY
    if not api_key:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.apollo.io/v1/people/search",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
            json={
                "api_key": api_key,
                "page": criteria.get("page", 1),
                "per_page": criteria.get("per_page", 25),
                "person_titles": criteria.get("titles", []),
                "person_locations": criteria.get("locations", []),
                "organization_domains": criteria.get("domains", []),
                "q_organization_domains_list": criteria.get("domains", []),
            },
        )
        data = resp.json()
        return [
            {
                "first_name": p.get("first_name", ""),
                "last_name": p.get("last_name", ""),
                "title": p.get("title", ""),
                "company": (p.get("organization") or {}).get("name", ""),
                "email": p.get("email", ""),
                "phone": p.get("phone", ""),
                "linkedin_url": p.get("linkedin_url", ""),
                "industry": (p.get("organization") or {}).get("industry", ""),
                "location": f"{p.get('city', '')}, {p.get('state', '')}".strip(", "),
                "company_size": str((p.get("organization") or {}).get("estimated_num_employees", "")),
                "source": "apollo",
            }
            for p in data.get("people", [])
        ]
