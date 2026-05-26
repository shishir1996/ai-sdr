import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.scrape_profile import ScrapeProfile
from app.utils.auth import get_current_user
from app.services.lead_extraction.web_scraper import scrape_and_create_lead, deep_scrape_domain
from app.services.lead_extraction.persona_parser import parse_persona
from app.services.integrations.resolver import resolve_api_key

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeProfileCreate(BaseModel):
    name: str
    persona_description: str = ""
    business_category: str = ""
    country: str = ""
    directory_urls: str = ""
    selected_fields: str = ""


class ScrapeProfileUpdate(BaseModel):
    name: Optional[str] = None
    persona_description: Optional[str] = None
    business_category: Optional[str] = None
    country: Optional[str] = None
    directory_urls: Optional[str] = None
    selected_fields: Optional[str] = None


class ScrapeProfileResponse(BaseModel):
    id: str
    name: str
    persona_description: str
    country: str
    directory_urls: str
    selected_fields: str
    created_at: str
    updated_at: str


@router.get("/profiles")
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScrapeProfile).where(ScrapeProfile.org_id == user.org_id).order_by(ScrapeProfile.created_at.desc())
    )
    profiles = result.scalars().all()
    return [Sp(profile) for profile in profiles]


def Sp(profile: ScrapeProfile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name,
        "persona_description": profile.persona_description,
        "business_category": profile.business_category,
        "country": profile.country,
        "directory_urls": profile.directory_urls,
        "selected_fields": profile.selected_fields,
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }


@router.post("/profiles")
async def create_profile(
    body: ScrapeProfileCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = ScrapeProfile(
        org_id=user.org_id,
        name=body.name,
        persona_description=body.persona_description,
        business_category=body.business_category,
        country=body.country,
        directory_urls=body.directory_urls,
        selected_fields=body.selected_fields,
    )
    db.add(profile)
    await db.flush()
    return Sp(profile)


@router.get("/profiles/{profile_id}")
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScrapeProfile).where(ScrapeProfile.id == profile_id, ScrapeProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return Sp(profile)


@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: str,
    body: ScrapeProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScrapeProfile).where(ScrapeProfile.id == profile_id, ScrapeProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(profile, key, val)
    await db.flush()
    return Sp(profile)


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScrapeProfile).where(ScrapeProfile.id == profile_id, ScrapeProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    return {"status": "deleted"}


class ParsePersonaRequest(BaseModel):
    persona_text: str


@router.post("/parse-persona")
async def parse_persona_endpoint(
    body: ParsePersonaRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ai_key = await resolve_api_key(db, user.org_id, "together_ai")
    result = await parse_persona(body.persona_text, api_key=ai_key)
    return result


class ExecuteScrapeRequest(BaseModel):
    url: str
    country: str = ""
    business_category: str = ""
    selected_fields: str = ""


class GoogleBusinessSearchRequest(BaseModel):
    query: str
    location: str
    country: str = ""
    business_category: str = ""
    selected_fields: str = ""


class ProfileScrapeRequest(BaseModel):
    profile_id: str
    urls: list[str] = []


@router.post("/execute")
async def execute_scrape(
    body: ExecuteScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.lead import Lead

    lead_data = await scrape_and_create_lead(body.url, country=body.country)
    if lead_data.get("_blocked"):
        raise HTTPException(status_code=400, detail=lead_data.get("_reason", "Website blocked the scraper"))
    if not lead_data.get("company") and not lead_data.get("email"):
        raise HTTPException(status_code=400, detail="Could not extract meaningful data from URL")

    if lead_data.get("email"):
        existing = await db.execute(
            select(Lead).where(Lead.email == lead_data["email"], Lead.org_id == user.org_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Lead with this email already exists")

    lead = Lead(org_id=user.org_id, **lead_data)
    db.add(lead)
    await db.flush()

    fields = json.loads(body.selected_fields) if body.selected_fields else []
    return {
        "id": lead.id,
        "company": lead.company,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "phone": lead.phone,
        "title": lead.title,
        "industry": lead.industry,
        "location": lead.location,
        "linkedin_url": lead.linkedin_url,
        "source": lead.source,
        "country": body.country,
        "pages_scraped": lead_data.get("pages_scraped", 0),
        "emails_found": lead_data.get("emails", []),
        "phones_found": lead_data.get("phones", []),
        "social_links": lead_data.get("social_links", []),
        "team_members": lead_data.get("team_members", []),
    }


@router.get("/business-categories")
async def list_business_categories():
    from app.services.lead_extraction.google_business import BUSINESS_CATEGORIES
    return {"categories": BUSINESS_CATEGORIES}


@router.post("/search-google-maps")
async def search_google_maps(
    body: GoogleBusinessSearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.lead import Lead
    from app.models.settings import OrgSettings
    from app.services.lead_extraction.google_business import search_google_maps as search_gmb

    settings_result = await db.execute(select(OrgSettings).where(OrgSettings.org_id == user.org_id))
    org_settings = settings_result.scalar_one_or_none()
    if org_settings and org_settings.scraping_enabled is False:
        raise HTTPException(status_code=403, detail="Web scraping is not enabled for your organization. Contact your admin.")

    businesses = await search_gmb(body.query, body.location)
    if not businesses:
        return {
            "results": [],
            "total": 0,
            "imported": 0,
            "message": "No businesses found. Google Maps may have blocked automated access. For reliable Google Business Profile data, configure the Google Places API key in Admin > Integrations and use the Google Places API directly.",
        }

    fields = []
    try:
        fields = json.loads(body.selected_fields) if body.selected_fields else []
    except Exception:
        pass

    results = []
    for biz in businesses:
        try:
            existing = await db.execute(
                select(Lead).where(Lead.company == biz.get("name", ""), Lead.org_id == user.org_id)
            )
            if existing.scalar_one_or_none():
                results.append({"name": biz["name"], "status": "skipped", "reason": "Duplicate company"})
                continue

            notes_parts = []
            if biz.get("rating"):
                notes_parts.append(f"Rating: {biz['rating']}/5 ({biz.get('reviews', '0')} reviews)")
            if biz.get("category"):
                notes_parts.append(f"Category: {biz['category']}")
            if biz.get("phone"):
                notes_parts.append(f"Phone: {biz['phone']}")
            if body.country:
                notes_parts.append(f"Country: {body.country}")
            if biz.get("maps_url"):
                notes_parts.append(f"Maps: {biz['maps_url']}")

            website = biz.get("website", "")
            lead_data = {
                "company": biz["name"],
                "first_name": "",
                "last_name": "",
                "title": "",
                "email": "",
                "phone": biz.get("phone", ""),
                "website": website,
                "linkedin_url": "",
                "location": biz.get("address", ""),
                "industry": biz.get("category", body.business_category),
                "source": "google_business",
                "notes": " | ".join(notes_parts) if notes_parts else f"Imported from Google Business Profile. Query: {body.query} in {body.location}",
            }

            lead = Lead(org_id=user.org_id, **lead_data)
            db.add(lead)
            await db.flush()
            results.append({
                "name": biz["name"],
                "status": "imported",
                "lead_id": lead.id,
                "phone": biz.get("phone", ""),
                "location": biz.get("address", ""),
                "rating": biz.get("rating", ""),
                "category": biz.get("category", ""),
            })
        except Exception as e:
            results.append({"name": biz.get("name", "Unknown"), "status": "error", "reason": str(e)})

    await db.flush()
    return {
        "results": results,
        "total": len(results),
        "imported": sum(1 for r in results if r["status"] == "imported"),
    }


@router.post("/execute-batch")
async def execute_batch(
    body: ProfileScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.lead import Lead

    result = await db.execute(
        select(ScrapeProfile).where(ScrapeProfile.id == body.profile_id, ScrapeProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    urls = body.urls if body.urls else []
    if not urls and profile.directory_urls:
        urls = [u.strip() for u in profile.directory_urls.split("\n") if u.strip().startswith("http")]

    fields = []
    try:
        fields = json.loads(profile.selected_fields) if profile.selected_fields else []
    except Exception:
        pass

    results = []
    for url in urls:
        try:
            lead_data = await scrape_and_create_lead(url, country=profile.country)
            if not lead_data.get("company") and not lead_data.get("email"):
                results.append({"url": url, "status": "failed", "reason": "No data extracted"})
                continue

            if lead_data.get("email"):
                existing = await db.execute(
                    select(Lead).where(Lead.email == lead_data["email"], Lead.org_id == user.org_id)
                )
                if existing.scalar_one_or_none():
                    results.append({"url": url, "status": "skipped", "reason": "Duplicate email"})
                    continue

            lead = Lead(org_id=user.org_id, **lead_data)
            db.add(lead)
            await db.flush()
            results.append({
                "url": url,
                "status": "imported",
                "lead_id": lead.id,
                "company": lead.company,
                "email": lead.email,
                "contact": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                "title": lead.title,
                "location": lead.location,
                "industry": lead.industry,
            })
        except Exception as e:
            results.append({"url": url, "status": "error", "reason": str(e)})

    await db.flush()
    return {
        "results": results,
        "total": len(results),
        "imported": sum(1 for r in results if r["status"] == "imported"),
    }
