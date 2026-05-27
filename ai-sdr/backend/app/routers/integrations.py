from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_admin
from app.services.integrations.service import set_integration, list_integrations, delete_integration, INTEGRATION_META
from app.services.ai.provider import AVAILABLE_MODELS

router = APIRouter(prefix="/admin/integrations", tags=["admin-integrations"])
OAUTH_PROVIDERS = ["gmail", "outlook", "linkedin"]


class IntegrationSave(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


@router.get("")
async def get_integrations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    return await list_integrations(db, user.org_id)


@router.put("/{provider}")
async def save_integration(
    provider: str,
    body: IntegrationSave,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    if provider not in INTEGRATION_META:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")
    extra = {}
    if body.model:
        extra["model"] = body.model
    await set_integration(
        db=db,
        org_id=user.org_id,
        provider=provider,
        api_key=body.api_key,
        api_secret=body.api_secret,
        extra_config=extra if extra else None,
        is_active=body.is_active,
    )
    return {"status": "saved"}


@router.delete("/{provider}")
async def remove_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    await delete_integration(db, user.org_id, provider)
    return {"status": "deleted"}


@router.get("/providers")
async def list_providers():
    return [
        {
            "provider": key,
            "label": meta["label"],
            "description": meta["description"],
            "fields": meta["fields"],
            "warning": meta.get("warning"),
        }
        for key, meta in INTEGRATION_META.items()
    ]


INTEGRATION_TO_AI_PROVIDER = {
    "openai": "openai",
    "anthropic": "claude",
    "google_ai": "gemini",
    "together_ai": "together",
    "openrouter": "openrouter",
}


@router.get("/ai/models")
async def list_ai_models(
    provider: str = Query(..., description="Integration provider name e.g. openai, anthropic, google_ai, together_ai, openrouter"),
    user: User = Depends(get_current_admin),
):
    ai_provider = INTEGRATION_TO_AI_PROVIDER.get(provider)
    if not ai_provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown AI provider: {provider}")
    models = [
        {
            "model_id": mid,
            "display_name": m.display_name,
            "provider": m.provider,
            "max_tokens": m.max_tokens,
            "cost_per_1k_input": m.cost_per_1k_input,
            "cost_per_1k_output": m.cost_per_1k_output,
        }
        for mid, m in AVAILABLE_MODELS.items()
        if m.provider == ai_provider
    ]
    return models


# ============================================================
# OAuth Flows
# ============================================================


@router.get("/{provider}/oauth/init")
async def initiate_oauth_flow(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"OAuth not supported for {provider}")
    from app.services.integrations.oauth_service import initiate_oauth
    result = await initiate_oauth(db, user.org_id, provider)
    return result


class OAuthComplete(BaseModel):
    code: str
    state: str


@router.post("/{provider}/oauth/callback")
async def complete_oauth_flow(
    provider: str,
    body: OAuthComplete,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"OAuth not supported for {provider}")
    from app.services.integrations.oauth_service import complete_oauth
    result = await complete_oauth(db, user.org_id, provider, body.code, body.state)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "OAuth failed"))
    return result


@router.get("/{provider}/status")
async def get_provider_connection_status(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    from app.services.integrations.oauth_service import get_provider_status
    return await get_provider_status(db, user.org_id, provider)


@router.post("/{provider}/refresh")
async def refresh_provider_token(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    from app.services.integrations.oauth_service import refresh_token_if_expired
    success = await refresh_token_if_expired(db, user.org_id, provider)
    return {"refreshed": success}


@router.get("/oauth/connected-accounts")
async def list_connected_accounts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    from app.services.integrations.oauth_service import get_connected_accounts
    return await get_connected_accounts(db, user.org_id)


@router.post("/{provider}/test")
async def test_provider_connection(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    from app.services.integrations.oauth_service import check_connection_health
    return await check_connection_health(db, user.org_id, provider)
