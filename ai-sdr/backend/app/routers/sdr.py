import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.agent import SDRProfile, LeadState, AgentLog
from app.models.lead import Lead
from app.models.agent_activity import AgentActivity, SDRReasoningLog, CampaignEvent, LeadTimeline, SequenceExecutionLog, SDRStatus
from app.utils.auth import get_current_user
from app.utils.crypto import encrypt_value, decrypt_value
from app.services.sdr.credentials import (
    encrypt_sdr_credentials, decrypt_sdr_credentials,
    has_email_configured, has_linkedin_configured, get_email_sender,
)
from app.services.sdr.activity_service import (
    get_activity_feed, get_reasoning_logs, get_sdr_status_info,
    get_lead_timeline, get_activity_stages_summary,
)

router = APIRouter(prefix="/sdr", tags=["sdr"])


def serialize_sdr(profile: SDRProfile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name or "AI SDR",
        "region": profile.region or "",
        "sell_type": profile.sell_type,
        "product_name": profile.product_name,
        "product_description": profile.product_description,
        "payment_link": profile.payment_link,
        "service_description": profile.service_description,
        "calendar_link": profile.calendar_link,
        "target_titles": profile.target_titles or "",
        "target_industries": profile.target_industries or "",
        "target_locations": profile.target_locations or "",
        "target_company_size_min": profile.target_company_size_min,
        "target_company_size_max": profile.target_company_size_max,
        "lead_sources": profile.lead_sources or "",
        "sdr_personality": profile.sdr_personality or "",
        "outreach_tone": profile.outreach_tone or "professional",
        "max_daily_emails": profile.max_daily_emails or 20,
        "max_daily_calls": profile.max_daily_calls or 10,
        "max_daily_linkedin": profile.max_daily_linkedin or 15,
        "max_daily_likes": profile.max_daily_likes or 20,
        "max_daily_comments": profile.max_daily_comments or 10,
        "linkedin_connect_enabled": bool(profile.linkedin_connect_enabled),
        "linkedin_dm_enabled": bool(profile.linkedin_dm_enabled),
        "linkedin_like_enabled": bool(profile.linkedin_like_enabled),
        "linkedin_comment_enabled": bool(profile.linkedin_comment_enabled),
        "linkedin_engagement_feed": profile.linkedin_engagement_feed or "",
        "web_scrape_targets": profile.web_scrape_targets or "",
        "auto_scrape_enabled": bool(profile.auto_scrape_enabled),
        "scrape_business_category": profile.scrape_business_category or "",
        "scrape_country": profile.scrape_country or "",
        "scrape_directory_urls": profile.scrape_directory_urls or "",
        "campaign_sequence": profile.campaign_sequence or "",
        # Credential status (never expose actual creds to frontend)
        "has_email": has_email_configured(profile.email_credentials_encrypted),
        "email_sender": get_email_sender(profile.email_credentials_encrypted) or "",
        "email_provider": (decrypt_sdr_credentials(profile.email_credentials_encrypted) or {}).get("provider", "") if profile.email_credentials_encrypted else "",
        "has_linkedin": has_linkedin_configured(profile.linkedin_credentials_encrypted),
        "is_active": bool(profile.is_active),
        "leads_target": profile.leads_target or 100,
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
        "deleted_at": profile.deleted_at.isoformat() if profile.deleted_at else None,
    }


@router.get("/profiles")
async def list_sdr_profiles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id, SDRProfile.deleted_at == None).order_by(SDRProfile.created_at.desc())
    )
    return [serialize_sdr(p) for p in result.scalars().all()]


class SDRCreate(BaseModel):
    name: str = "AI SDR"
    region: str = ""
    sell_type: str = "product"
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    payment_link: Optional[str] = None
    service_description: Optional[str] = None
    calendar_link: Optional[str] = None
    target_titles: str = ""
    target_industries: str = ""
    target_locations: str = ""
    target_company_size_min: Optional[int] = None
    target_company_size_max: Optional[int] = None
    lead_sources: str = ""
    sdr_personality: str = ""
    outreach_tone: str = "professional"
    max_daily_emails: int = 20
    max_daily_calls: int = 10
    max_daily_linkedin: int = 15
    max_daily_likes: int = 20
    max_daily_comments: int = 10
    linkedin_connect_enabled: bool = True
    linkedin_dm_enabled: bool = True
    linkedin_like_enabled: bool = False
    linkedin_comment_enabled: bool = False
    linkedin_engagement_feed: str = ""
    web_scrape_targets: str = ""
    auto_scrape_enabled: bool = False
    scrape_business_category: str = ""
    scrape_country: str = ""
    scrape_directory_urls: str = ""
    campaign_sequence: str = ""
    leads_target: int = 100


@router.post("/profiles")
async def create_sdr_profile(
    body: SDRCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = SDRProfile(org_id=user.org_id, **body.model_dump())
    db.add(profile)
    await db.flush()
    return serialize_sdr(profile)


@router.get("/profiles/{profile_id}")
async def get_sdr_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    return serialize_sdr(profile)


@router.put("/profiles/{profile_id}")
async def update_sdr_profile(
    profile_id: str,
    body: SDRCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    for key, val in body.model_dump().items():
        setattr(profile, key, val)
    await db.flush()
    return serialize_sdr(profile)


@router.get("/profiles/{profile_id}/deletion-impact")
async def get_sdr_deletion_impact(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.campaign import Campaign
    from app.models.agent_activity import SDRStatus, AgentActivity

    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    campaigns = await db.execute(
        select(Campaign).where(Campaign.org_id == user.org_id, Campaign.sdr_profile_id == profile_id)
    )
    campaign_list = campaigns.scalars().all()
    active_campaigns = [c for c in campaign_list if c.status == "active"]
    total_campaigns = len(campaign_list)

    lead_states = await db.execute(
        select(LeadState).where(LeadState.org_id == user.org_id, LeadState.sdr_profile_id == profile_id)
    )
    ls_list = lead_states.scalars().all()

    total_leads = len(ls_list)
    active_leads = len([ls for ls in ls_list if ls.state not in ("closed_won", "closed_lost", "archived")])

    activities = await db.execute(
        select(AgentActivity).where(AgentActivity.org_id == user.org_id, AgentActivity.sdr_profile_id == profile_id).limit(1)
    )
    has_activity = activities.first() is not None

    email_configured = has_email_configured(profile.email_credentials_encrypted)
    linkedin_configured = has_linkedin_configured(profile.linkedin_credentials_encrypted)

    return {
        "sdr_name": profile.name or "AI SDR",
        "total_campaigns": total_campaigns,
        "active_campaigns": len(active_campaigns),
        "total_leads_associated": total_leads,
        "active_leads_in_pipeline": active_leads,
        "email_connected": email_configured,
        "linkedin_connected": linkedin_configured,
        "has_activity_history": has_activity,
        "is_active": profile.is_active,
    }


class SDRDeleteConfirm(BaseModel):
    confirmation: str


@router.post("/profiles/{profile_id}/delete")
async def delete_sdr_profile_secure(
    profile_id: str,
    body: SDRDeleteConfirm,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm deletion")

    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    from datetime import datetime, timezone
    profile.deleted_at = datetime.now(timezone.utc)
    profile.deleted_by = user.id
    profile.is_active = False

    from app.models.campaign import Campaign
    campaigns = await db.execute(
        select(Campaign).where(Campaign.org_id == user.org_id, Campaign.sdr_profile_id == profile_id)
    )
    for c in campaigns.scalars().all():
        c.sdr_profile_id = None

    from app.models.agent_activity import SDRStatus
    statuses = await db.execute(
        select(SDRStatus).where(SDRStatus.org_id == user.org_id, SDRStatus.sdr_profile_id == profile_id)
    )
    for s in statuses.scalars().all():
        await db.delete(s)

    from app.services.audit.service import log_audit
    await log_audit(db, user.org_id, user.id, "sdr_deleted",
                    f"SDR profile '{profile.name}' deleted by {user.name or user.email}",
                    extra={"profile_id": profile_id, "profile_name": profile.name})

    await db.flush()
    return {"status": "deleted", "sdr_name": profile.name}


# ============================================================
# Per-SDR Credential Management
# ============================================================

class EmailCredentialsSave(BaseModel):
    provider: str = "smtp"
    # Gmail fields
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    # SMTP fields
    host: Optional[str] = None
    port: Optional[int] = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    # IMAP fields (for incoming reply detection)
    imap_host: Optional[str] = None
    imap_port: Optional[int] = 993
    imap_use_ssl: bool = True
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    # Common
    sender_email: str
    sender_name: str = "AI SDR"


class LinkedInCredentialsSave(BaseModel):
    email: str
    password: str


@router.put("/profiles/{profile_id}/email-creds")
async def save_sdr_email_creds(
    profile_id: str,
    body: EmailCredentialsSave,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    creds = {"provider": body.provider, "sender_email": body.sender_email, "sender_name": body.sender_name}
    if body.provider == "gmail":
        creds["client_id"] = body.client_id
        creds["client_secret"] = body.client_secret
        creds["refresh_token"] = body.refresh_token
    else:
        creds["host"] = body.host
        creds["port"] = body.port
        creds["username"] = body.username
        creds["password"] = body.password
        creds["use_tls"] = body.use_tls
        creds["use_ssl"] = body.use_ssl
        creds["imap_host"] = body.imap_host
        creds["imap_port"] = body.imap_port
        creds["imap_use_ssl"] = body.imap_use_ssl
        creds["imap_username"] = body.imap_username or body.username
        creds["imap_password"] = body.imap_password or body.password

    profile.email_credentials_encrypted = encrypt_sdr_credentials(creds)
    await db.flush()
    return {"status": "saved", "sender_email": body.sender_email, "provider": body.provider}


@router.put("/profiles/{profile_id}/linkedin-creds")
async def save_sdr_linkedin_creds(
    profile_id: str,
    body: LinkedInCredentialsSave,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    creds = {"email": body.email, "password": body.password}
    profile.linkedin_credentials_encrypted = encrypt_sdr_credentials(creds)
    await db.flush()
    return {"status": "saved", "account_email": body.email}


# ============================================================
# Vapi Voice Credentials
# ============================================================
class VapiCredentialsSave(BaseModel):
    api_key: str
    phone_number: Optional[str] = None
    assistant_id: Optional[str] = None
    voice_id: Optional[str] = None
    script: Optional[str] = None
    first_message: Optional[str] = None


@router.put("/profiles/{profile_id}/vapi-creds")
async def save_sdr_vapi_creds(
    profile_id: str,
    body: VapiCredentialsSave,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    creds = {
        "api_key": body.api_key,
        "phone_number": body.phone_number,
        "assistant_id": body.assistant_id,
        "voice_id": body.voice_id,
        "script": body.script,
        "first_message": body.first_message,
    }
    profile.vapi_credentials_encrypted = encrypt_sdr_credentials(creds)
    profile.vapi_enabled = True
    await db.flush()
    return {"status": "saved", "phone_number": body.phone_number}


@router.delete("/profiles/{profile_id}/vapi-creds")
async def delete_sdr_vapi_creds(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.vapi_credentials_encrypted = None
    profile.vapi_enabled = False
    await db.flush()
    return {"status": "cleared"}


# ============================================================
# Channel toggles
# ============================================================
class ChannelTogglesSave(BaseModel):
    email_enabled: bool = True
    linkedin_enabled: bool = True
    vapi_enabled: bool = False


@router.put("/profiles/{profile_id}/channels")
async def save_sdr_channels(
    profile_id: str,
    body: ChannelTogglesSave,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    profile.email_enabled = body.email_enabled
    profile.linkedin_enabled = body.linkedin_enabled
    profile.vapi_enabled = body.vapi_enabled and bool(profile.vapi_credentials_encrypted)
    await db.flush()
    return {
        "email_enabled": profile.email_enabled,
        "linkedin_enabled": profile.linkedin_enabled,
        "vapi_enabled": profile.vapi_enabled,
    }


# ============================================================
# Reset SDR configuration
# ============================================================
@router.post("/profiles/{profile_id}/reset-config")
async def reset_sdr_config(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reset SDR credentials and configuration (keeps the SDR profile + lead assignments)."""
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.email_credentials_encrypted = None
    profile.linkedin_credentials_encrypted = None
    profile.vapi_credentials_encrypted = None
    profile.email_enabled = True
    profile.linkedin_enabled = True
    profile.vapi_enabled = False
    await db.flush()
    return {"status": "reset"}


@router.delete("/profiles/{profile_id}/email-creds")
async def delete_sdr_email_creds(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.email_credentials_encrypted = None
    await db.flush()
    return {"status": "deleted"}


@router.delete("/profiles/{profile_id}/linkedin-creds")
async def delete_sdr_linkedin_creds(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.linkedin_credentials_encrypted = None
    await db.flush()
    return {"status": "deleted"}


# Test email config
class TestEmailSend(BaseModel):
    to_email: str
    subject: str = "Test email from AI SDR"
    body_html: str = "<h2>Test</h2><p>If you receive this, email is configured correctly.</p>"


@router.post("/profiles/{profile_id}/test-email")
async def test_sdr_email(
    profile_id: str,
    body: TestEmailSend,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    creds = decrypt_sdr_credentials(profile.email_credentials_encrypted)
    if not creds:
        raise HTTPException(status_code=400, detail="No email credentials configured for this SDR")

    if creds.get("provider") == "gmail":
        from app.services.email.gmail_client import send_email as gmail_send
        result = gmail_send(
            to=body.to_email,
            subject=body.subject,
            body_html=body.body_html,
            client_id=creds.get("client_id"),
            client_secret=creds.get("client_secret"),
            refresh_token=creds.get("refresh_token"),
        )
        return result or {"status": "error", "error": "Gmail send failed"}
    else:
        from app.services.email.smtp_service import SMTPSender
        from app.models.smtp import SMTPConfig
        import uuid
        test_config = SMTPConfig(
            id=str(uuid.uuid4()),
            org_id=user.org_id,
            host=creds.get("host", ""),
            port=creds.get("port", 587),
            use_tls=creds.get("use_tls", True),
            use_ssl=creds.get("use_ssl", False),
            username=creds.get("username", ""),
            password_encrypted=encrypt_value(creds.get("password", "")),
            sender_name=creds.get("sender_name", "AI SDR"),
            sender_email=creds.get("sender_email", ""),
            is_active=False,
        )
        sender = SMTPSender(test_config)
        return await sender.send(body.to_email, body.subject, body.body_html)


# Test LinkedIn config
@router.post("/profiles/{profile_id}/test-linkedin")
async def test_sdr_linkedin(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    creds = decrypt_sdr_credentials(profile.linkedin_credentials_encrypted)
    if not creds:
        raise HTTPException(status_code=400, detail="No LinkedIn credentials configured for this SDR")

    from app.services.linkedin.linkedin_client import login_and_save_cookies
    success = await login_and_save_cookies(
        email=creds.get("email", ""),
        password=creds.get("password", ""),
        headless=True,
    )
    return {"status": "connected" if success else "failed"}


@router.post("/profiles/{profile_id}/activate")
async def activate_sdr(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.is_active = True
    await db.flush()

    from app.services.sdr.sdr_orchestrator import start_sdr_cycle
    import asyncio
    asyncio.create_task(start_sdr_cycle(user.org_id, sdr_profile_id=profile_id))

    return {"status": "activated", "sdr_id": profile_id, "name": profile.name}


@router.post("/profiles/{profile_id}/deactivate")
async def deactivate_sdr(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")
    profile.is_active = False
    await db.flush()
    return {"status": "deactivated"}


@router.get("/activity")
async def get_agent_activity(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
    limit: int = 50,
):
    query = select(AgentLog).where(AgentLog.org_id == user.org_id)
    if sdr_profile_id:
        query = query.where(AgentLog.sdr_profile_id == sdr_profile_id)
    query = query.order_by(AgentLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "sdr_profile_id": log.sdr_profile_id,
            "lead_id": log.lead_id,
            "action": log.action,
            "channel": log.channel,
            "reasoning": log.reasoning,
            "result": log.result,
            "status": log.status,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/activity/feed")
async def get_structured_activity(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return await get_activity_feed(db, user.org_id, sdr_profile_id, stage, limit, offset)


@router.get("/activity/reasoning")
async def get_reasoning(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    limit: int = 50,
):
    return await get_reasoning_logs(db, user.org_id, sdr_profile_id, lead_id, limit)


@router.get("/activity/stages")
async def get_activity_stages(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
):
    return await get_activity_stages_summary(db, user.org_id, sdr_profile_id)


@router.get("/activity/lead-timeline/{lead_id}")
async def get_lead_activity_timeline(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
):
    return await get_lead_timeline(db, user.org_id, lead_id, limit)


@router.get("/status")
async def get_sdr_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
):
    if sdr_profile_id:
        info = await get_sdr_status_info(db, user.org_id, sdr_profile_id)
        return info or {"current_status": "inactive", "leads_processed": 0}
    profiles = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id)
    )
    results = []
    for p in profiles.scalars().all():
        info = await get_sdr_status_info(db, user.org_id, p.id)
        if info:
            info["sdr_name"] = p.name
            info["sdr_id"] = p.id
            results.append(info)
    return results or [{"current_status": "inactive", "leads_processed": 0}]


@router.get("/activity/performance")
async def get_sdr_performance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
):
    if sdr_profile_id:
        info = await get_sdr_status_info(db, user.org_id, sdr_profile_id)
        if info:
            return info
        return {"leads_processed": 0, "campaigns_created": 0, "emails_drafted": 0,
                "linkedin_invites_sent": 0, "replies_detected": 0, "meetings_booked": 0}
    profiles = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id)
    )
    totals = {"leads_processed": 0, "campaigns_created": 0, "emails_drafted": 0,
              "linkedin_invites_sent": 0, "replies_detected": 0, "meetings_booked": 0}
    for p in profiles.scalars().all():
        info = await get_sdr_status_info(db, user.org_id, p.id)
        if info:
            for k in totals:
                totals[k] += info.get(k, 0)
    return totals


@router.get("/leads")
async def get_all_lead_states(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
):
    query = select(LeadState).where(LeadState.org_id == user.org_id)
    if sdr_profile_id:
        query = query.where(LeadState.sdr_profile_id == sdr_profile_id)
    query = query.order_by(LeadState.updated_at.desc())
    result = await db.execute(query)
    states = result.scalars().all()
    leads_by_id = {}
    lead_ids = [s.lead_id for s in states]
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        for lead in leads_result.scalars().all():
            leads_by_id[lead.id] = lead
    return [
        {
            "lead_id": s.lead_id,
            "sdr_profile_id": s.sdr_profile_id,
            "lead_name": f"{leads_by_id.get(s.lead_id, Lead()).first_name or ''} {leads_by_id.get(s.lead_id, Lead()).last_name or ''}".strip(),
            "lead_email": leads_by_id.get(s.lead_id, Lead()).email or "",
            "lead_company": leads_by_id.get(s.lead_id, Lead()).company or "",
            "lead_source": leads_by_id.get(s.lead_id, Lead()).source or "",
            "state": s.state,
            "is_paused": s.is_paused,
            "contact_count": s.contact_count or 0,
            "channels_used": list(s.channels_used) if s.channels_used else [],
            "last_contacted_at": s.last_contacted_at.isoformat() if s.last_contacted_at else None,
        }
        for s in states
    ]


@router.get("/leads/progress")
async def get_lead_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id))
    states = result.scalars().all()
    progress: dict[str, int] = {}
    for s in states:
        state_key = s.state or "unknown"
        progress[state_key] = progress.get(state_key, 0) + 1
    return progress


@router.get("/rate-limits")
async def get_rate_limits(user: User = Depends(get_current_user)):
    from app.services.sdr.rate_limiter import rate_limiter
    return await rate_limiter.get_usage(user.org_id)


@router.post("/rate-limits/reset")
async def reset_rate_limits(user: User = Depends(get_current_user)):
    from app.services.sdr.rate_limiter import rate_limiter
    await rate_limiter.reset_org(user.org_id)
    return {"status": "reset"}


@router.post("/leads/{lead_id}/pause")
async def pause_lead(lead_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id, LeadState.lead_id == lead_id))
    ls = result.scalar_one_or_none()
    if not ls:
        raise HTTPException(status_code=404, detail="Lead state not found")
    ls.is_paused = True
    await db.flush()
    return {"status": "paused"}


@router.post("/leads/{lead_id}/resume")
async def resume_lead(lead_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id, LeadState.lead_id == lead_id))
    ls = result.scalar_one_or_none()
    if not ls:
        raise HTTPException(status_code=404, detail="Lead state not found")
    ls.is_paused = False
    await db.flush()
    return {"status": "resumed"}


@router.post("/leads/{lead_id}/stop")
async def stop_lead(lead_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadState).where(LeadState.org_id == user.org_id, LeadState.lead_id == lead_id))
    ls = result.scalar_one_or_none()
    if not ls:
        raise HTTPException(status_code=404, detail="Lead state not found")
    ls.state = "archived"
    ls.is_paused = False
    await db.flush()
    return {"status": "stopped"}


# ============================================================
# Campaign Dashboard & AI Reasoning Endpoints
# ============================================================

@router.get("/campaign-dashboard")
async def get_sdr_campaign_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    sdr_profile_id: Optional[str] = None,
):
    from app.models.campaign import Campaign, CampaignStep, EmailMessage
    from sqlalchemy import func

    query = select(Campaign).where(Campaign.org_id == user.org_id)
    if sdr_profile_id:
        query = query.where(Campaign.sdr_profile_id == sdr_profile_id)
    query = query.order_by(Campaign.created_at.desc())
    result = await db.execute(query)
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

        lead_states_result = await db.execute(
            select(LeadState).where(LeadState.org_id == user.org_id)
        )
        lead_states = lead_states_result.scalars().all()
        pipeline = {}
        for ls in lead_states:
            s = ls.state or "new"
            pipeline[s] = pipeline.get(s, 0) + 1

        latest_logs_result = await db.execute(
            select(AgentLog).where(
                AgentLog.org_id == user.org_id,
                AgentLog.sdr_profile_id == c.sdr_profile_id,
            ).order_by(AgentLog.created_at.desc()).limit(10)
        )
        logs = latest_logs_result.scalars().all()

        sdr_name = ""
        if c.sdr_profile_id:
            sdr_result = await db.execute(select(SDRProfile).where(SDRProfile.id == c.sdr_profile_id))
            sdr = sdr_result.scalar_one_or_none()
            if sdr:
                sdr_name = sdr.name or "AI SDR"

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
            "emails_sent": total_sent or 0,
            "emails_opened": total_opened or 0,
            "emails_replied": total_replied or 0,
            "pipeline": pipeline,
            "recent_reasoning": [
                {
                    "action": log.action,
                    "channel": log.channel,
                    "reasoning": log.reasoning,
                    "result": log.result,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        })

    return output


@router.get("/reasoning/{sdr_profile_id}")
async def get_sdr_reasoning(
    sdr_profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
):
    result = await db.execute(
        select(AgentLog).where(
            AgentLog.org_id == user.org_id,
            AgentLog.sdr_profile_id == sdr_profile_id,
        ).order_by(AgentLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "lead_id": log.lead_id,
            "action": log.action,
            "channel": log.channel,
            "reasoning": log.reasoning,
            "result": log.result,
            "status": log.status,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.post("/pause-all")
async def pause_all_sdr(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id)
    )
    profiles = result.scalars().all()
    for p in profiles:
        p.is_active = False
    await db.flush()
    return {"status": "all_paused"}


@router.post("/emergency-stop")
async def emergency_stop(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id)
    )
    profiles = result.scalars().all()
    for p in profiles:
        p.is_active = False

    lead_states = await db.execute(
        select(LeadState).where(LeadState.org_id == user.org_id, LeadState.is_paused == False)
    )
    for ls in lead_states.scalars().all():
        ls.is_paused = True

    await db.flush()

    log = AgentLog(
        org_id=user.org_id,
        action="emergency_stop",
        channel=None,
        reasoning="Admin triggered emergency stop",
        result="All SDRs paused, all leads paused",
        status="completed",
    )
    db.add(log)
    await db.flush()

    return {"status": "emergency_stop_executed"}


@router.get("/diagnostics")
async def sdr_diagnostics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.org_id == user.org_id)
    )
    profiles = result.scalars().all()
    profile_data = []
    for p in profiles:
        profile_data.append({
            "id": p.id,
            "name": p.name,
            "is_active": p.is_active,
            "lead_sources": p.lead_sources,
            "has_email_creds": bool(p.email_credentials_encrypted),
        })

    lead_count = await db.scalar(select(func.count(Lead.id)).where(Lead.org_id == user.org_id))
    lead_sources_q = await db.execute(
        select(Lead.source, func.count(Lead.id)).where(Lead.org_id == user.org_id).group_by(Lead.source)
    )
    lead_sources = {row[0]: row[1] for row in lead_sources_q.fetchall()}

    state_count = await db.scalar(select(func.count(LeadState.id)).where(LeadState.org_id == user.org_id))
    state_breakdown_q = await db.execute(
        select(LeadState.state, func.count(LeadState.id)).where(LeadState.org_id == user.org_id).group_by(LeadState.state)
    )
    state_breakdown = {row[0]: row[1] for row in state_breakdown_q.fetchall()}

    return {
        "profiles": profile_data,
        "leads": {
            "total": lead_count or 0,
            "by_source": lead_sources,
        },
        "lead_states": {
            "total": state_count or 0,
            "by_state": state_breakdown,
        },
    }
