import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.integration import Integration, INTEGRATION_PROVIDERS
from app.utils.crypto import encrypt_value, decrypt_value


async def get_integration(db: AsyncSession, org_id: str, provider: str) -> Optional[Integration]:
    result = await db.execute(
        select(Integration).where(
            Integration.org_id == org_id,
            Integration.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def get_active_integration(db: AsyncSession, org_id: str, provider: str) -> Optional[Integration]:
    result = await db.execute(
        select(Integration).where(
            Integration.org_id == org_id,
            Integration.provider == provider,
            Integration.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_api_key(db: AsyncSession, org_id: str, provider: str) -> Optional[str]:
    integration = await get_active_integration(db, org_id, provider)
    if integration and integration.api_key_encrypted:
        return decrypt_value(integration.api_key_encrypted)
    return None


async def get_api_secret(db: AsyncSession, org_id: str, provider: str) -> Optional[str]:
    integration = await get_active_integration(db, org_id, provider)
    if integration and integration.api_secret_encrypted:
        return decrypt_value(integration.api_secret_encrypted)
    return None


async def get_refresh_token(db: AsyncSession, org_id: str, provider: str) -> Optional[str]:
    integration = await get_active_integration(db, org_id, provider)
    if integration and integration.refresh_token_encrypted:
        return decrypt_value(integration.refresh_token_encrypted)
    return None


async def set_refresh_token(
    db: AsyncSession,
    org_id: str,
    provider: str,
    refresh_token: str,
) -> None:
    integration = await get_integration(db, org_id, provider)
    if integration:
        integration.refresh_token_encrypted = encrypt_value(refresh_token)
        await db.flush()


async def set_integration(
    db: AsyncSession,
    org_id: str,
    provider: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    extra_config: Optional[dict] = None,
    is_active: bool = True,
    label: Optional[str] = None,
) -> Integration:
    integration = await get_integration(db, org_id, provider)
    if integration:
        if api_key is not None:
            integration.api_key_encrypted = encrypt_value(api_key) if api_key else None
        if api_secret is not None:
            integration.api_secret_encrypted = encrypt_value(api_secret) if api_secret else None
        if extra_config is not None:
            integration.extra_config = json.dumps(extra_config)
        integration.is_active = is_active
        if label:
            integration.label = label
    else:
        integration = Integration(
            org_id=org_id,
            provider=provider,
            label=label or provider,
            api_key_encrypted=encrypt_value(api_key) if api_key else None,
            api_secret_encrypted=encrypt_value(api_secret) if api_secret else None,
            extra_config=json.dumps(extra_config) if extra_config else None,
            is_active=is_active,
        )
        db.add(integration)
    await db.flush()
    return integration


async def delete_integration(db: AsyncSession, org_id: str, provider: str):
    integration = await get_integration(db, org_id, provider)
    if integration:
        await db.delete(integration)
        await db.flush()


async def list_integrations(db: AsyncSession, org_id: str) -> list[dict]:
    result = await db.execute(
        select(Integration).where(Integration.org_id == org_id).order_by(Integration.provider)
    )
    integrations = result.scalars().all()
    return [
        {
            "id": i.id,
            "provider": i.provider,
            "label": i.label or i.provider,
            "is_active": i.is_active,
            "has_api_key": bool(i.api_key_encrypted),
            "has_api_secret": bool(i.api_secret_encrypted),
            "has_refresh_token": bool(i.refresh_token_encrypted),
            "extra_config": json.loads(i.extra_config) if i.extra_config else None,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in integrations
    ]


INTEGRATION_META = {
    "together_ai": {
        "label": "Together AI",
        "description": "AI model inference for lead scoring, email drafting, and call scripts",
        "fields": [{"key": "api_key", "label": "API Key", "type": "password", "placeholder": "tgp_..."}],
    },
    "openai": {
        "label": "OpenAI",
        "description": "GPT-4o and GPT-3.5 Turbo for AI-powered features",
        "fields": [{"key": "api_key", "label": "API Key", "type": "password", "placeholder": "sk-..."}],
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "description": "Claude 3.5 Sonnet and Claude 3 Haiku for AI tasks",
        "fields": [{"key": "api_key", "label": "API Key", "type": "password", "placeholder": "sk-ant-..."}],
    },
    "google_ai": {
        "label": "Google AI (Gemini)",
        "description": "Gemini 1.5 Pro and Flash models",
        "fields": [{"key": "api_key", "label": "API Key", "type": "password", "placeholder": "AIza..."}],
    },
    "gmail": {
        "label": "Gmail API",
        "description": "Send and track emails via Google Gmail",
        "fields": [
            {"key": "api_key", "label": "Client ID", "type": "text", "placeholder": "xxx.apps.googleusercontent.com"},
            {"key": "api_secret", "label": "Client Secret", "type": "password", "placeholder": "GOCSPX-..."},
        ],
    },
    "vapi": {
        "label": "VAPI.ai",
        "description": "AI-powered phone calls",
        "fields": [{"key": "api_key", "label": "API Key", "type": "password", "placeholder": "sk-..."}],
    },
    "linkedin": {
        "label": "LinkedIn",
        "description": "Browser automation for connection requests, DMs, likes, and comments",
        "fields": [
            {"key": "api_key", "label": "Email", "type": "email", "placeholder": "your@email.com"},
            {"key": "api_secret", "label": "Password", "type": "password", "placeholder": "Your LinkedIn password"},
        ],
        "warning": "LinkedIn automation may violate their terms of service. Use at your own risk. Credentials are encrypted and only used for browser automation.",
    },
    "apollo": {
        "label": "Apollo.io",
        "description": "B2B lead database and enrichment",
        "fields": [{"key": "api_key", "label": "API Key", "type": "password", "placeholder": "..."}],
    },
    "aws": {
        "label": "AWS S3",
        "description": "File storage for uploads, recordings, and exports",
        "fields": [
            {"key": "api_key", "label": "Access Key ID", "type": "text", "placeholder": "AKIA..."},
            {"key": "api_secret", "label": "Secret Access Key", "type": "password", "placeholder": "..."},
        ],
    },
}
