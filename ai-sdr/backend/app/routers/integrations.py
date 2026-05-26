from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_admin
from app.services.integrations.service import (
    set_integration, delete_integration, list_integrations,
    get_integration, INTEGRATION_META,
)

router = APIRouter(prefix="/admin/integrations", tags=["integrations"])


class IntegrationUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    is_active: bool = True
    label: Optional[str] = None


@router.get("/providers")
async def get_providers(
    admin: User = Depends(get_current_admin),
):
    return [
        {
            "provider": key,
            "label": meta["label"],
            "description": meta["description"],
            "fields": meta["fields"],
        }
        for key, meta in INTEGRATION_META.items()
    ]


@router.get("")
async def list_org_integrations(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await list_integrations(db, admin.org_id)


@router.put("/{provider}")
async def upsert_integration(
    provider: str,
    body: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if provider not in INTEGRATION_META:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    integration = await set_integration(
        db, admin.org_id, provider,
        api_key=body.api_key,
        api_secret=body.api_secret,
        is_active=body.is_active,
        label=body.label,
    )
    return {
        "provider": integration.provider,
        "is_active": integration.is_active,
        "has_api_key": bool(integration.api_key_encrypted),
        "has_api_secret": bool(integration.api_secret_encrypted),
    }


@router.delete("/{provider}")
async def remove_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await delete_integration(db, admin.org_id, provider)
    return {"status": "deleted"}
