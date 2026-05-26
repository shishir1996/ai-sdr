import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.utils.auth import get_current_user
from app.services.lead_extraction.csv_importer import parse_csv
from app.services.lead_extraction.apollo import search_leads
from app.services.lead_extraction.web_scraper import scrape_and_create_lead
from app.services.lead_extraction.lusha import enrich_lead as enrich_lusha
from app.services.lead_extraction.rocketreach import enrich_lead as enrich_rocketreach
from app.services.lead_extraction.google_places import search_places
from app.services.ai.lead_scoring import score_lead
from app.services.integrations.resolver import resolve_api_key

router = APIRouter(prefix="/leads", tags=["leads"])


SAMPLE_CSV_HEADERS = [
    "first_name", "last_name", "email", "phone", "title", "company",
    "linkedin_url", "website", "industry", "location", "city", "state",
    "country", "company_size", "revenue", "products_services", "notes",
]


@router.get("/stats")
async def leads_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    all_leads = await db.execute(select(Lead).where(Lead.org_id == user.org_id))
    leads = all_leads.scalars().all()
    total = len(leads)
    source_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    scored = 0
    for lead in leads:
        src = lead.source or "unknown"
        source_counts[src] = source_counts.get(src, 0) + 1
        st = lead.status or "new"
        status_counts[st] = status_counts.get(st, 0) + 1
        if lead.score and lead.score > 0:
            scored += 1
    return {
        "total": total,
        "by_source": source_counts,
        "by_status": status_counts,
        "scored": scored,
    }


@router.get("/sample-csv")
async def download_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(SAMPLE_CSV_HEADERS)
    writer.writerow([
        "John", "Doe", "john@acmecorp.com", "+1-555-0100", "CTO",
        "Acme Corp", "https://linkedin.com/in/johndoe", "https://acmecorp.com",
        "Technology", "San Francisco, CA", "San Francisco", "California",
        "United States", "51-200", "$10M-$50M", "Cloud software, APIs",
        "Met at TechConf 2025",
    ])
    writer.writerow([
        "Jane", "Smith", "jane@example.com", "+1-555-0200", "VP Engineering",
        "Example Inc", "", "https://example.com", "Healthcare",
        "New York, NY", "New York", "New York", "United States",
        "201-500", "$50M-$100M", "HealthTech platform", "",
    ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_sample.csv"},
    )


class LeadCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    company_size: Optional[str] = None
    products_services: Optional[str] = None
    source: Optional[str] = "manual"


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
async def list_leads(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    source: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    industry: Optional[str] = None,
    location: Optional[str] = None,
):
    conditions = [Lead.org_id == user.org_id]
    if search:
        conditions.append(
            or_(
                Lead.first_name.ilike(f"%{search}%"),
                Lead.last_name.ilike(f"%{search}%"),
                Lead.company.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
                Lead.title.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
            )
        )
    if source:
        conditions.append(Lead.source == source)
    if status:
        conditions.append(Lead.status == status)
    if min_score is not None:
        conditions.append(Lead.score >= min_score)
    if industry:
        conditions.append(Lead.industry.ilike(f"%{industry}%"))
    if location:
        conditions.append(
            or_(
                Lead.location.ilike(f"%{location}%"),
                Lead.city.ilike(f"%{location}%"),
                Lead.state.ilike(f"%{location}%"),
                Lead.country.ilike(f"%{location}%"),
            )
        )
    query = select(Lead).where(and_(*conditions)).order_by(Lead.created_at.desc())
    total_query = select(Lead).where(and_(*conditions))
    total_result = await db.execute(total_query)
    total = len(total_result.scalars().all())
    result = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
    leads = result.scalars().all()
    return {"items": leads, "total": total, "page": page, "per_page": per_page}


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.org_id == user.org_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("")
async def create_lead(
    body: LeadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.email:
        existing = await db.execute(
            select(Lead).where(Lead.email == body.email, Lead.org_id == user.org_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Lead with this email already exists")

    lead = Lead(
        org_id=user.org_id,
        **body.model_dump(exclude_none=True),
    )
    db.add(lead)
    await db.flush()

    try:
        ai_key = await resolve_api_key(db, user.org_id, "together_ai")
        scoring = score_lead(body.model_dump(exclude_none=True), api_key=ai_key)
        lead.score = scoring.get("score", 0)
    except Exception:
        pass

    await db.flush()
    return lead


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    body: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.org_id == user.org_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(lead, key, val)
    await db.flush()
    return lead


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.org_id == user.org_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    return {"status": "deleted"}


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    rows = parse_csv(content)
    created = []
    for row in rows:
        existing = await db.execute(
            select(Lead).where(Lead.email == row.get("email"), Lead.org_id == user.org_id)
        )
        if existing.scalar_one_or_none():
            continue
        lead = Lead(org_id=user.org_id, **row)
        db.add(lead)
        created.append(row.get("first_name", "") or row.get("email", ""))
    await db.flush()
    return {"imported": len(created), "total_in_file": len(rows)}


@router.get("/sources/apollo")
async def fetch_from_apollo(
    titles: str = "",
    locations: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    criteria = {
        "titles": [t.strip() for t in titles.split(",") if t.strip()],
        "locations": [l.strip() for l in locations.split(",") if l.strip()],
    }
    api_key = await resolve_api_key(db, user.org_id, "apollo")
    leads = await search_leads(criteria, api_key_override=api_key)
    created = []
    for lead_data in leads:
        if lead_data.get("email"):
            existing = await db.execute(
                select(Lead).where(Lead.email == lead_data["email"], Lead.org_id == user.org_id)
            )
            if existing.scalar_one_or_none():
                continue
        lead = Lead(org_id=user.org_id, **lead_data)
        db.add(lead)
        created.append(lead)
    await db.flush()
    return {"imported": len(created), "total_from_apollo": len(leads)}


@router.post("/scrape-website")
async def scrape_website(
    url: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead_data = await scrape_and_create_lead(url)
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
    return {
        "id": lead.id,
        "company": lead.company,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "phone": lead.phone,
        "source": lead.source,
        "pages_scraped": lead_data.get("pages_scraped", 0),
        "emails_found": lead_data.get("emails", []),
        "phones_found": lead_data.get("phones", []),
        "social_links": lead_data.get("social_links", []),
        "team_members": lead_data.get("team_members", []),
    }


class BatchScrapeRequest(BaseModel):
    urls: list[str]


@router.post("/scrape-batch")
async def scrape_batch(
    body: BatchScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = []
    for url in body.urls:
        try:
            lead_data = await scrape_and_create_lead(url)
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
            })
        except Exception as e:
            results.append({"url": url, "status": "error", "reason": str(e)})

    await db.flush()
    return {"results": results, "total": len(results), "imported": sum(1 for r in results if r["status"] == "imported")}


@router.post("/enrich/lusha")
async def enrich_with_lusha(
    email: str = "",
    phone: str = "",
    first_name: str = "",
    last_name: str = "",
    company: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key = await resolve_api_key(db, user.org_id, "lusha")
    if not api_key:
        raise HTTPException(status_code=400, detail="Lusha not configured. Add API key in Admin > Integrations.")
    result = await enrich_lusha(
        email=email or None,
        phone=phone or None,
        first_name=first_name or None,
        last_name=last_name or None,
        company=company or None,
        api_key=api_key,
    )
    return result


@router.post("/enrich/rocketreach")
async def enrich_with_rocketreach(
    email: str = "",
    linkedin_url: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key = await resolve_api_key(db, user.org_id, "rocketreach")
    if not api_key:
        raise HTTPException(status_code=400, detail="RocketReach not configured. Add API key in Admin > Integrations.")
    result = await enrich_rocketreach(
        email=email or None,
        linkedin_url=linkedin_url or None,
        api_key=api_key,
    )
    return result


@router.post("/enrich/lead/{lead_id}")
async def enrich_single_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.org_id == user.org_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    enriched = {}
    lusha_key = await resolve_api_key(db, user.org_id, "lusha")
    rr_key = await resolve_api_key(db, user.org_id, "rocketreach")

    if lusha_key:
        lusha_data = await enrich_lusha(
            email=lead.email or None,
            phone=lead.phone or None,
            first_name=lead.first_name or None,
            last_name=lead.last_name or None,
            company=lead.company or None,
            api_key=lusha_key,
        )
        if lusha_data.get("phone"):
            enriched["phone"] = lusha_data["phone"]
        if lusha_data.get("email") and not lead.email:
            enriched["email"] = lusha_data["email"]
        if not lead.title and lusha_data.get("title"):
            enriched["title"] = lusha_data["title"]

    if rr_key and not enriched.get("phone"):
        rr_data = await enrich_rocketreach(
            email=lead.email or None,
            linkedin_url=lead.linkedin_url or None,
            api_key=rr_key,
        )
        if rr_data.get("phone"):
            enriched["phone"] = rr_data["phone"]
        if rr_data.get("email") and not lead.email and not enriched.get("email"):
            enriched["email"] = rr_data["email"]
        if not lead.title and rr_data.get("title"):
            enriched["title"] = rr_data["title"]

    if enriched:
        for key, val in enriched.items():
            setattr(lead, key, val)
        lead.source = lead.source or "enriched"
        await db.flush()

    return {"lead_id": lead.id, "enriched": enriched, "source": "lusha+rocketreach"}


@router.get("/sources/google-places")
async def fetch_from_google_places(
    query: str = "",
    location: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key = await resolve_api_key(db, user.org_id, "google_places")
    if not api_key:
        raise HTTPException(status_code=400, detail="Google Places API not configured. Add API key in Admin > Integrations.")
    if not query or not location:
        raise HTTPException(status_code=400, detail="Both 'query' and 'location' parameters are required")

    businesses = await search_places(query, location, api_key)
    created = []
    for biz in businesses:
        if biz.get("name"):
            existing = await db.execute(
                select(Lead).where(
                    Lead.company == biz["name"],
                    Lead.org_id == user.org_id,
                )
            )
            if existing.scalar_one_or_none():
                continue
        lead = Lead(org_id=user.org_id, **biz)
        db.add(lead)
        created.append(lead)
    await db.flush()
    return {"imported": len(created), "total_from_places": len(businesses)}
