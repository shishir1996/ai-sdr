from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.smtp import SMTPConfig
from app.utils.auth import get_current_admin
from app.utils.crypto import encrypt_value, decrypt_value
from app.services.email.smtp_service import send_email_via_smtp, SMTP_PROVIDERS, SMTP_WARNINGS, get_dns_guide
from app.services.email.smtp_service import get_active_smtp_config

router = APIRouter(prefix="/smtp", tags=["smtp"])


class SMTPConfigCreate(BaseModel):
    provider: str = "custom"
    host: str
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    username: str
    password: str
    sender_name: str
    sender_email: str
    reply_to: Optional[str] = None
    daily_limit: int = 300
    hourly_limit: int = 30
    warmup_enabled: bool = False
    is_active: bool = False


class SMTPConfigUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    reply_to: Optional[str] = None
    daily_limit: Optional[int] = None
    hourly_limit: Optional[int] = None
    warmup_enabled: Optional[bool] = None
    warmup_daily_increment: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/configs")
async def list_smtp_configs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(SMTPConfig).where(SMTPConfig.org_id == user.org_id).order_by(SMTPConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return [
        {
            "id": c.id,
            "provider": c.provider,
            "host": c.host,
            "port": c.port,
            "use_tls": c.use_tls,
            "use_ssl": c.use_ssl,
            "username": c.username,
            "sender_name": c.sender_name,
            "sender_email": c.sender_email,
            "reply_to": c.reply_to,
            "daily_limit": c.daily_limit,
            "hourly_limit": c.hourly_limit,
            "warmup_enabled": c.warmup_enabled,
            "warmup_current_daily": c.warmup_current_daily,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in configs
    ]


@router.post("/configs")
async def create_smtp_config(
    body: SMTPConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    provider_config = SMTP_PROVIDERS.get(body.provider)
    if provider_config:
        host = provider_config["host"]
        port = provider_config["port"]
        use_ssl = provider_config["use_ssl"]
        use_tls = provider_config["use_tls"]
    else:
        host = body.host
        port = body.port
        use_ssl = body.use_ssl
        use_tls = body.use_tls

    if body.is_active:
        existing = await db.execute(
            select(SMTPConfig).where(
                SMTPConfig.org_id == user.org_id,
                SMTPConfig.is_active == True,
            )
        )
        for cfg in existing.scalars().all():
            cfg.is_active = False

    config = SMTPConfig(
        org_id=user.org_id,
        provider=body.provider,
        host=host,
        port=port,
        use_tls=use_tls,
        use_ssl=use_ssl,
        username=body.username,
        password_encrypted=encrypt_value(body.password),
        sender_name=body.sender_name,
        sender_email=body.sender_email,
        reply_to=body.reply_to,
        daily_limit=body.daily_limit,
        hourly_limit=body.hourly_limit,
        warmup_enabled=body.warmup_enabled,
        is_active=body.is_active,
    )
    db.add(config)
    await db.flush()
    return {
        "id": config.id,
        "provider": config.provider,
        "sender_email": config.sender_email,
        "is_active": config.is_active,
        "warning": SMTP_WARNINGS.get(body.provider),
    }


@router.put("/configs/{config_id}")
async def update_smtp_config(
    config_id: str,
    body: SMTPConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(SMTPConfig).where(SMTPConfig.id == config_id, SMTPConfig.org_id == user.org_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP config not found")

    if body.is_active:
        existing = await db.execute(
            select(SMTPConfig).where(
                SMTPConfig.org_id == user.org_id,
                SMTPConfig.is_active == True,
                SMTPConfig.id != config_id,
            )
        )
        for cfg in existing.scalars().all():
            cfg.is_active = False

    update_data = body.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["password_encrypted"] = encrypt_value(update_data.pop("password"))
    for key, value in update_data.items():
        setattr(config, key, value)
    await db.flush()
    return {"status": "updated"}


@router.delete("/configs/{config_id}")
async def delete_smtp_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(SMTPConfig).where(SMTPConfig.id == config_id, SMTPConfig.org_id == user.org_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP config not found")
    await db.delete(config)
    await db.flush()
    return {"status": "deleted"}


@router.post("/test")
async def test_smtp_config(
    body: SMTPConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    provider_config = SMTP_PROVIDERS.get(body.provider)
    if provider_config:
        host = provider_config["host"]
        port = provider_config["port"]
    else:
        host = body.host
        port = body.port

    from app.services.email.smtp_service import SMTPSender
    from app.models.smtp import SMTPConfig

    test_config = SMTPConfig(
        org_id=user.org_id,
        provider=body.provider,
        host=host,
        port=port,
        use_tls=body.use_tls,
        use_ssl=body.use_ssl,
        username=body.username,
        password_encrypted=encrypt_value(body.password),
        sender_name=body.sender_name,
        sender_email=body.sender_email,
        is_active=False,
    )
    sender = SMTPSender(test_config)
    result = await sender.send(
        to_email=user.email,
        subject="AI SDR - SMTP Test",
        body_html=f"<h2>SMTP Configuration Test</h2><p>If you receive this, your SMTP settings for {body.sender_email} are working.</p>",
    )
    return result


@router.get("/providers")
async def list_smtp_providers():
    return [
        {
            "id": key,
            "name": key.capitalize() if key != "sendgrid" else "SendGrid",
            "config": value,
            "warning": SMTP_WARNINGS.get(key),
        }
        for key, value in SMTP_PROVIDERS.items()
    ]


@router.get("/dns-guide")
async def dns_guide():
    return get_dns_guide("offdx.in")
