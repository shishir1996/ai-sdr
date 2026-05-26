from app.celery_app import celery_app
from app.services.email.gmail_client import send_email
from app.services.voice.vapi_client import make_call
from app.models.campaign import Campaign, CampaignStep, EmailTemplate, CallScript
from app.models.lead import Lead
from app.database import async_session_factory
from sqlalchemy import select


@celery_app.task
def execute_campaign_step(campaign_id: str, step_id: str, lead_ids: list[str]):
    import asyncio

    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(select(CampaignStep).where(CampaignStep.id == step_id))
            step = result.scalar_one_or_none()
            if not step:
                return {"error": "Step not found"}

            for lead_id in lead_ids:
                lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = lead_result.scalar_one_or_none()
                if not lead:
                    continue

                if step.channel == "email" and step.template_id:
                    tmpl_result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == step.template_id))
                    template = tmpl_result.scalar_one_or_none()
                    if template and lead.email:
                        subject = template.subject.replace("{{first_name}}", lead.first_name or "")
                        body = template.body_html.replace("{{first_name}}", lead.first_name or "")
                        body = body.replace("{{company}}", lead.company or "")
                        send_email(lead.email, subject, body)

                elif step.channel == "call" and lead.phone:
                    asyncio.create_task(make_call(lead.phone))

    asyncio.run(_run())
    return {"status": "completed", "step_id": step_id, "leads": len(lead_ids)}


@celery_app.task
def run_campaign(campaign_id: str):
    import asyncio

    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalar_one_or_none()
            if not campaign:
                return {"error": "Campaign not found"}

            lead_result = await db.execute(select(Lead).where(Lead.org_id == campaign.org_id, Lead.score >= 30))
            lead_ids = [str(row.id) for row in lead_result.scalars().all()]

            for step in campaign.steps:
                execute_campaign_step.delay(campaign_id, step.id, lead_ids)

    asyncio.run(_run())
    return {"campaign_id": campaign_id, "status": "started"}
