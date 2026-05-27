from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.integrations.resolver import resolve_api_key, resolve_api_secret

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentLinkRequest(BaseModel):
    amount: float
    description: str = ""
    customer_name: str
    customer_email: str
    customer_phone: str = ""
    currency: str = "INR"


@router.post("/create-link")
async def create_payment_link(
    body: PaymentLinkRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key_id = await resolve_api_key(db, user.org_id, "razorpay")
    api_key_secret = await resolve_api_secret(db, user.org_id, "razorpay")
    if not api_key_id or not api_key_secret:
        raise HTTPException(status_code=400, detail="Razorpay not configured. Add credentials in Admin > Integrations.")

    from app.services.payments.razorpay_service import create_payment_link as rp_create
    result = await rp_create(
        amount=body.amount,
        description=body.description or f"Payment for {body.customer_name}",
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
        currency=body.currency,
        api_key_id=api_key_id,
        api_key_secret=api_key_secret,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Payment link creation failed"))

    lead_id = None
    if body.customer_email:
        from sqlalchemy import select
        from app.models.lead import Lead
        found = await db.execute(select(Lead).where(Lead.email == body.customer_email, Lead.org_id == user.org_id))
        lead = found.scalar_one_or_none()
        if lead:
            lead_id = lead.id
            lead.status = "payment_sent"
            await db.flush()

    return {
        "success": True,
        "payment_link_id": result.get("payment_link_id"),
        "short_url": result.get("short_url"),
        "status": result.get("status"),
        "amount": body.amount,
        "currency": body.currency,
        "lead_id": lead_id,
    }


@router.get("/link-status/{payment_link_id}")
async def get_payment_status(
    payment_link_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key_id = await resolve_api_key(db, user.org_id, "razorpay")
    api_key_secret = await resolve_api_secret(db, user.org_id, "razorpay")
    if not api_key_id or not api_key_secret:
        raise HTTPException(status_code=400, detail="Razorpay not configured")

    from app.services.payments.razorpay_service import get_payment_link_status
    return await get_payment_link_status(payment_link_id, api_key_id, api_key_secret)


@router.get("/links")
async def list_payment_links(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key_id = await resolve_api_key(db, user.org_id, "razorpay")
    api_key_secret = await resolve_api_secret(db, user.org_id, "razorpay")
    if not api_key_id or not api_key_secret:
        return {"items": [], "total": 0}

    from app.services.payments.razorpay_service import list_payment_links
    links = await list_payment_links(page, per_page, api_key_id, api_key_secret)
    return {"items": links, "total": len(links), "page": page}
