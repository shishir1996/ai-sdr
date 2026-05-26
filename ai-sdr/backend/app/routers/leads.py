from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.utils.auth import get_current_user
from app.services.lead_extraction.csv_importer import parse_csv
from app.services.lead_extraction.apollo import search_leads
from app.services.lead_extraction.web_scraper import scrape_and_create_lead
from app.services.ai.lead_scoring import score_lead
from app.services.integrations.resolver import resolve_api_key

router = APIRouter(prefix="/leads", tags=["leads"])


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
    page: int = 1,
    per_page: int = 25,
    search: Optional[str] = None,
):
    query = select(Lead).where(Lead.org_id == user.org_id).order_by(Lead.created_at.desc())
    if search:
        query = query.where(
            Lead.first_name.ilike(f"%{search}%") |
            Lead.last_name.ilike(f"%{search}%") |
            Lead.company.ilike(f"%{search}%") |
            Lead.email.ilike(f"%{search}%")
        )
    result = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
    leads = result.scalars().all()
    total_query = await db.execute(select(Lead).where(Lead.org_id == user.org_id))
    total = len(total_query.scalars().all())
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
