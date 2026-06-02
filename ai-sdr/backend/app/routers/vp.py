import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.vp_sales import VPSalesProfile, ResearchAgent, VPActionLog
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.vp.decision_engine import (
    decide_and_execute, get_vp_dashboard, get_vp_decisions, log_vp_action, assess_lead_situation
)
from app.services.research.agent_service import create_research_agent, execute_research, get_agent_results

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vp", tags=["vp"])


class VPCreateRequest(BaseModel):
    name: str = "VP Sales AI"
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    service_description: Optional[str] = None
    business_goals: Optional[str] = None
    icp_description: Optional[str] = None
    target_country: Optional[str] = None
    target_audience: Optional[str] = None
    sales_objectives: Optional[str] = None
    target_titles: Optional[str] = None
    target_business_types: Optional[str] = None
    outreach_active: Optional[bool] = None


class ResearchAgentCreateRequest(BaseModel):
    name: str
    search_queries: Optional[str] = None
    target_industry: Optional[str] = None
    target_country: Optional[str] = None
    target_audience: Optional[str] = None
    max_leads: int = 50


@router.get("/profile")
async def get_vp_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        return None
    return {
        "id": vp.id,
        "org_id": vp.org_id,
        "name": vp.name,
        "product_name": vp.product_name,
        "product_description": vp.product_description,
        "service_description": vp.service_description,
        "business_goals": vp.business_goals,
        "icp_description": vp.icp_description,
        "target_country": vp.target_country,
        "target_audience": vp.target_audience,
        "sales_objectives": vp.sales_objectives,
        "target_titles": vp.target_titles,
        "target_business_types": vp.target_business_types,
        "outreach_active": bool(vp.outreach_active),
        "is_active": vp.is_active,
        "created_at": vp.created_at.isoformat() if vp.created_at else None,
        "updated_at": vp.updated_at.isoformat() if vp.updated_at else None,
    }


@router.post("/profile")
async def create_vp_profile(
    req: VPCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="VP profile already exists for this organization")

    vp = VPSalesProfile(
        org_id=user.org_id,
        name=req.name,
        product_name=req.product_name,
        product_description=req.product_description,
        service_description=req.service_description,
        business_goals=req.business_goals,
        icp_description=req.icp_description,
        target_country=req.target_country,
        target_audience=req.target_audience,
        sales_objectives=req.sales_objectives,
        target_titles=req.target_titles,
        target_business_types=req.target_business_types,
        outreach_active=bool(req.outreach_active) if req.outreach_active is not None else False,
    )
    db.add(vp)
    await db.flush()

    await log_vp_action(db, user.org_id, vp.id, "vp_created",
                        f"VP Sales '{req.name}' created and configured")

    return {"id": vp.id, "message": "VP Sales profile created"}


@router.put("/profile")
async def update_vp_profile(
    req: VPCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail="VP profile not found. Create one first.")

    for field in ["name", "product_name", "product_description", "service_description",
                  "business_goals", "icp_description", "target_country", "target_audience",
                  "sales_objectives", "target_titles", "target_business_types"]:
        value = getattr(req, field, None)
        if value is not None:
            setattr(vp, field, value)
    if req.outreach_active is not None:
        vp.outreach_active = req.outreach_active
    await db.flush()
    return {"message": "VP profile updated"}


@router.get("/dashboard")
async def vp_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        return {"error": "no_vp", "message": "Create a VP Sales profile first"}

    data = await get_vp_dashboard(db, user.org_id, vp.id)
    data["vp_id"] = vp.id
    data["vp_name"] = vp.name
    return data


@router.get("/decisions")
async def vp_decisions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        return {"decisions": []}

    decisions = await get_vp_decisions(db, user.org_id, vp.id)
    return {"decisions": decisions}


@router.post("/decide")
async def vp_decide(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail="Create VP profile first")

    result = await decide_and_execute(db, user.org_id, vp)
    return result


@router.get("/agents")
async def list_research_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchAgent)
        .where(ResearchAgent.org_id == user.org_id)
        .order_by(ResearchAgent.created_at.desc())
    )
    agents = result.scalars().all()
    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "search_queries": a.search_queries,
                "target_industry": a.target_industry,
                "target_country": a.target_country,
                "target_audience": a.target_audience,
                "max_leads": a.max_leads,
                "status": a.status,
                "leads_discovered": a.leads_discovered,
                "last_run_at": a.last_run_at.isoformat() if a.last_run_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in agents
        ]
    }


@router.post("/agents")
async def create_research_agent_endpoint(
    req: ResearchAgentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()

    agent = await create_research_agent(
        db=db,
        org_id=user.org_id,
        vp_id=vp.id if vp else None,
        name=req.name,
        search_queries=req.search_queries,
        target_industry=req.target_industry,
        target_country=req.target_country,
        target_audience=req.target_audience,
        max_leads=req.max_leads,
    )

    if vp:
        await log_vp_action(db, user.org_id, vp.id, "agent_created",
                            f"Research agent '{req.name}' created",
                            {"agent_id": agent.id, "queries": req.search_queries})

    return {"id": agent.id, "message": "Research agent created"}


@router.post("/agents/{agent_id}/run")
async def run_research_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    leads_found = await execute_research(db, agent_id)
    return {"leads_found": leads_found, "message": f"Research completed. {leads_found} leads discovered."}


@router.get("/agents/{agent_id}/results")
async def get_agent_results_endpoint(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = await get_agent_results(db, agent_id)
    return {
        "results": [
            {
                "id": r.id,
                "source": r.source,
                "source_url": r.source_url,
                "title": r.title,
                "snippet": r.snippet,
                "company_name": r.company_name,
                "contact_name": r.contact_name,
                "contact_title": r.contact_title,
                "contact_email": r.contact_email,
                "website": r.website,
                "industry": r.industry,
                "location": r.location,
                "status": r.status,
                "converted_to_lead": r.converted_to_lead,
                "lead_id": r.lead_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ]
    }


@router.post("/agents/results/{result_id}/convert")
async def convert_result_to_lead(
    result_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.research.agent_service import convert_to_lead
    lead_id = await convert_to_lead(db, user.org_id, result_id)
    if not lead_id:
        raise HTTPException(status_code=400, detail="Result already converted or not found")
    return {"lead_id": lead_id, "message": "Research result converted to lead"}


@router.get("/situation")
async def vp_situation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        return {"error": "no_vp"}
    situation = await assess_lead_situation(db, user.org_id, vp)
    return situation


@router.post("/toggle-outreach")
async def toggle_outreach(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VPSalesProfile).where(VPSalesProfile.org_id == user.org_id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail="VP profile not found")
    vp.outreach_active = not vp.outreach_active
    await db.flush()
    await log_vp_action(db, user.org_id, vp.id, "outreach_toggled",
                        f"AI Sales Team {'ACTIVATED' if vp.outreach_active else 'DEACTIVATED'}")
    return {"outreach_active": bool(vp.outreach_active), "message": f"AI Sales Team {'activated' if vp.outreach_active else 'deactivated'}"}


@router.delete("/agents/{agent_id}")
async def delete_research_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchAgent).where(
            ResearchAgent.id == agent_id,
            ResearchAgent.org_id == user.org_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Research agent not found")
    await db.delete(agent)
    await db.flush()
    return {"message": f"Research agent '{agent.name}' deleted"}


@router.delete("/sdrs/{sdr_id}")
async def remove_sdr(
    sdr_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.agent import SDRProfile
    result = await db.execute(
        select(SDRProfile).where(
            SDRProfile.id == sdr_id,
            SDRProfile.org_id == user.org_id,
        )
    )
    sdr = result.scalar_one_or_none()
    if not sdr:
        raise HTTPException(status_code=404, detail="SDR not found")
    sdr.is_active = False
    sdr.deleted_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.flush()
    return {"message": f"SDR '{sdr.name}' removed"}
