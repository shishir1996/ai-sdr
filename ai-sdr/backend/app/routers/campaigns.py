from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.agent import SDRProfile, LeadState
from app.models.campaign import Campaign, CampaignStep, EmailTemplate, EmailMessage, CallScript
from app.models.lead import Lead
from sqlalchemy import func
from app.utils.auth import get_current_user
from app.services.ai.email_writer import draft_email
from app.services.integrations.resolver import resolve_api_key

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None


class StepCreate(BaseModel):
    step_order: int
    channel: str
    delay_days: int = 0


class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: str
    variables: Optional[dict] = None


@router.get("")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.org_id == user.org_id).order_by(Campaign.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.org_id == user.org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("")
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    campaign = Campaign(org_id=user.org_id, name=body.name, description=body.description)
    db.add(campaign)
    await db.flush()
    return campaign


@router.put("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.org_id == user.org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = status
    await db.flush()
    return campaign


@router.post("/{campaign_id}/steps")
async def add_campaign_step(
    campaign_id: str,
    body: StepCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.org_id == user.org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")
    step = CampaignStep(campaign_id=campaign_id, **body.model_dump())
    db.add(step)
    await db.flush()
    return step


@router.post("/templates")
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = EmailTemplate(org_id=user.org_id, **body.model_dump())
    db.add(template)
    await db.flush()
    return template


@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.org_id == user.org_id)
    )
    return result.scalars().all()


@router.post("/{campaign_id}/ai-generate-step")
async def ai_generate_step(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.org_id == user.org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    lead_info = {
        "first_name": "{{first_name}}",
        "last_name": "{{last_name}}",
        "title": "{{title}}",
        "company": "{{company}}",
    }
    ai_key = await resolve_api_key(db, user.org_id, "together_ai")
    email = draft_email(lead_info, campaign.name or "", "professional", api_key=ai_key)
    template = EmailTemplate(
        org_id=user.org_id,
        name=f"AI Generated - {campaign.name}",
        subject=email.get("subject", "Hello"),
        body_html=email.get("body", ""),
        variables=None,
    )
    db.add(template)
    await db.flush()

    step = CampaignStep(
        campaign_id=campaign_id,
        step_order=1,
        channel="email",
        template_id=template.id,
        delay_days=0,
    )
    db.add(step)
    await db.flush()
    return {"step": step, "template": template}


@router.get("/with-stats")
async def get_campaigns_with_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).where(Campaign.org_id == user.org_id).order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    output = []
    for c in campaigns:
        steps_result = await db.execute(
            select(CampaignStep).where(CampaignStep.campaign_id == c.id).order_by(CampaignStep.step_order)
        )
        steps = steps_result.scalars().all()

        total_sent = await db.scalar(
            select(func.count(EmailMessage.id)).where(
                EmailMessage.org_id == user.org_id,
                EmailMessage.campaign_id == c.id,
                EmailMessage.status == "sent",
            )
        )
        total_opened = await db.scalar(
            select(func.count(EmailMessage.id)).where(
                EmailMessage.org_id == user.org_id,
                EmailMessage.campaign_id == c.id,
                EmailMessage.opened_at.isnot(None),
            )
        )
        total_replied = await db.scalar(
            select(func.count(EmailMessage.id)).where(
                EmailMessage.org_id == user.org_id,
                EmailMessage.campaign_id == c.id,
                EmailMessage.replied_at.isnot(None),
            )
        )

        sdr_name = ""
        if c.sdr_profile_id:
            sdr_result = await db.execute(
                select(SDRProfile).where(SDRProfile.id == c.sdr_profile_id)
            )
            sdr = sdr_result.scalar_one_or_none()
            if sdr:
                sdr_name = sdr.name or "AI SDR"

        leads_count = 0
        if c.sdr_profile_id:
            ls_count = await db.scalar(
                select(func.count(LeadState.id)).where(
                    LeadState.org_id == user.org_id,
                    LeadState.sdr_profile_id == c.sdr_profile_id,
                )
            )
            leads_count = ls_count or 0

        output.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "status": c.status,
            "ai_generated": c.ai_generated,
            "sdr_profile_id": c.sdr_profile_id,
            "sdr_name": sdr_name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "steps": [
                {
                    "channel": s.channel,
                    "step_order": s.step_order,
                    "delay_days": s.delay_days,
                }
                for s in steps
            ],
            "leads_count": leads_count,
            "emails_sent": total_sent or 0,
            "emails_opened": total_opened or 0,
            "emails_replied": total_replied or 0,
        })

    return output
