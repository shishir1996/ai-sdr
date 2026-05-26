from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.deal import Pipeline, DealStage, Deal
from app.models.lead import Lead
from app.utils.auth import get_current_user

router = APIRouter(prefix="/deals", tags=["deals"])


class PipelineCreate(BaseModel):
    name: str


class StageCreate(BaseModel):
    pipeline_id: str
    name: str
    stage_order: int
    probability: int = 0
    color: Optional[str] = None


class DealCreate(BaseModel):
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    stage_id: str
    name: str
    value: float = 0.0
    notes: Optional[str] = None


class DealUpdate(BaseModel):
    stage_id: Optional[str] = None
    value: Optional[float] = None
    name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("/pipelines")
async def list_pipelines(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Pipeline).where(Pipeline.org_id == user.org_id).order_by(Pipeline.created_at.desc())
    )
    return result.scalars().all()


@router.post("/pipelines")
async def create_pipeline(
    body: PipelineCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = Pipeline(org_id=user.org_id, name=body.name)
    db.add(pipeline)
    await db.flush()

    default_stages = [
        ("Lead Inbox", 0, 10, "#6B7280"),
        ("Contacted", 1, 20, "#3B82F6"),
        ("Qualified", 2, 40, "#8B5CF6"),
        ("Demo Scheduled", 3, 60, "#F59E0B"),
        ("Negotiation", 4, 80, "#F97316"),
        ("Closed Won", 5, 100, "#10B981"),
        ("Closed Lost", 6, 0, "#EF4444"),
    ]
    for name, order, prob, color in default_stages:
        db.add(DealStage(
            pipeline_id=pipeline.id,
            name=name,
            stage_order=order,
            probability=prob,
            color=color,
        ))
    await db.flush()
    return pipeline


@router.get("")
async def list_deals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    stage_id: Optional[str] = None,
):
    query = select(Deal).where(Deal.org_id == user.org_id)
    if stage_id:
        query = query.where(Deal.stage_id == stage_id)
    result = await db.execute(query.order_by(Deal.created_at.desc()))
    return result.scalars().all()


@router.post("")
async def create_deal(
    body: DealCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deal = Deal(org_id=user.org_id, **body.model_dump())
    db.add(deal)
    await db.flush()
    return deal


@router.get("/{deal_id}")
async def get_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.org_id == user.org_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}")
async def update_deal(
    deal_id: str,
    body: DealUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.org_id == user.org_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(deal, key, val)
    await db.flush()
    return deal


@router.get("/won")
async def get_won_deals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal, DealStage.name, Lead.first_name, Lead.last_name)
        .select_from(Deal)
        .join(DealStage, Deal.stage_id == DealStage.id)
        .outerjoin(Lead, Deal.lead_id == Lead.id)
        .where(Deal.org_id == user.org_id, Deal.status == "won")
        .order_by(Deal.won_at.desc().nullslast(), Deal.closed_at.desc().nullslast())
    )
    return [
        {
            "id": deal.id,
            "name": deal.name,
            "value": deal.value,
            "source": deal.source,
            "status": deal.status,
            "closed_at": deal.closed_at.isoformat() if deal.closed_at else None,
            "won_at": deal.won_at.isoformat() if deal.won_at else None,
            "lead_name": f"{first_name or ''} {last_name or ''}".strip() or None,
            "stage_name": stage_name,
        }
        for deal, stage_name, first_name, last_name in result
    ]


@router.delete("/{deal_id}")
async def delete_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.org_id == user.org_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    await db.delete(deal)
    return {"status": "deleted"}
