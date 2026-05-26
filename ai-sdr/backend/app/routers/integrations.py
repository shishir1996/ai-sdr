from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_admin
from app.services.integrations.service import set_integration, list_integrations, delete_integration, INTEGRATION_META

router = APIRouter(prefix="/admin/integrations", tags=["admin-integrations"])


class IntegrationSave(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
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
    await set_integration(
        db=db,
        org_id=user.org_id,
        provider=provider,
        api_key=body.api_key,
        api_secret=body.api_secret,
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
