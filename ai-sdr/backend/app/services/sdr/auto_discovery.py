import logging
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.agent import SDRProfile
from app.services.lead_extraction.apollo import search_leads
from app.services.lead_extraction.web_scraper import scrape_and_create_lead
from app.services.integrations.resolver import resolve_api_key

logger = logging.getLogger(__name__)


async def auto_discover_leads(
    db: AsyncSession,
    org_id: str,
    profile: SDRProfile,
    max_leads: int = 25,
) -> int:
    if not profile.target_titles:
        logger.info(f"No target titles configured for org {org_id}, skipping auto-discovery")
        return 0

    titles = [t.strip() for t in profile.target_titles.split(",") if t.strip()]
    industries = [i.strip() for i in (profile.target_industries or "").split(",") if i.strip()]
    locations = [l.strip() for l in (profile.target_locations or "").split(",") if l.strip()]

    criteria = {
        "titles": titles,
        "per_page": min(max_leads, 100),
        "page": 1,
    }
    if industries:
        criteria["industries"] = industries
    if locations:
        criteria["locations"] = locations

    api_key = await resolve_api_key(db, org_id, "apollo")
    if not api_key:
        logger.info(f"No Apollo API key for org {org_id}, skipping auto-discovery")
        return 0

    candidates = await search_leads(criteria, api_key_override=api_key)
    if not candidates:
        logger.info(f"Apollo returned no leads for org {org_id}")
        return 0

    existing_result = await db.execute(
        select(Lead.email).where(Lead.org_id == org_id)
    )
    existing_emails = {row[0] for row in existing_result.fetchall() if row[0]}

    added = 0
    for c in candidates:
        if not c.get("email") or c["email"] in existing_emails:
            continue

        lead = Lead(
            org_id=org_id,
            first_name=c.get("first_name", ""),
            last_name=c.get("last_name", ""),
            title=c.get("title", ""),
            company=c.get("company", ""),
            email=c.get("email", ""),
            phone=c.get("phone", ""),
            linkedin_url=c.get("linkedin_url", ""),
            industry=c.get("industry", ""),
            location=c.get("location", ""),
            company_size=c.get("company_size", ""),
            source="apollo_auto",
            status="new",
        )
        db.add(lead)
        existing_emails.add(c["email"])
        added += 1

    await db.flush()
    logger.info(f"Auto-discovered {added} new leads from Apollo for org {org_id}")
    return added
