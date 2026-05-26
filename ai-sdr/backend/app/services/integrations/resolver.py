from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.services.integrations.service import get_active_integration, decrypt_value

settings = get_settings()

FALLBACK_KEYS: dict[str, str] = {
    "together_ai": settings.TOGETHER_API_KEY,
    "apollo": settings.APOLLO_API_KEY,
    "vapi": settings.VAPI_API_KEY,
}


async def resolve_api_key(db: AsyncSession, org_id: str, provider: str) -> str:
    integration = await get_active_integration(db, org_id, provider)
    if integration and integration.api_key_encrypted:
        return decrypt_value(integration.api_key_encrypted) or ""
    return FALLBACK_KEYS.get(provider, "")


async def resolve_api_secret(db: AsyncSession, org_id: str, provider: str) -> str:
    integration = await get_active_integration(db, org_id, provider)
    if integration and integration.api_secret_encrypted:
        return decrypt_value(integration.api_secret_encrypted) or ""
    return ""


async def resolve_refresh_token(db: AsyncSession, org_id: str, provider: str) -> str:
    integration = await get_active_integration(db, org_id, provider)
    if integration and integration.refresh_token_encrypted:
        return decrypt_value(integration.refresh_token_encrypted) or ""
    return ""
