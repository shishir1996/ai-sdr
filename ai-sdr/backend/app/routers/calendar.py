from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.integrations.resolver import resolve_api_key

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/providers")
async def list_calendar_providers():
    return {
        "providers": [
            {
                "id": "calendly",
                "label": "Calendly",
                "description": "Meeting scheduling via Calendly API",
                "needs_auth": True,
            },
            {
                "id": "cal_com",
                "label": "Cal.com",
                "description": "Open-source scheduling via Cal.com API",
                "needs_auth": True,
            },
        ]
    }


@router.get("/calendly/event-types")
async def get_calendly_event_types(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.calendar.calendly_service import list_calendly_event_types
    api_key = await resolve_api_key(db, user.org_id, "calendly")
    if not api_key:
        raise HTTPException(status_code=400, detail="Calendly not configured")
    return {"event_types": await list_calendly_event_types(api_key)}


class CalendlyBookRequest(BaseModel):
    event_type_uri: str
    invitee_name: str
    invitee_email: str


@router.post("/calendly/book")
async def book_calendly(
    body: CalendlyBookRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.calendar.calendly_service import book_calendly_meeting
    api_key = await resolve_api_key(db, user.org_id, "calendly")
    if not api_key:
        raise HTTPException(status_code=400, detail="Calendly not configured")
    result = await book_calendly_meeting(
        event_type_uri=body.event_type_uri,
        invitee_name=body.invitee_name,
        invitee_email=body.invitee_email,
        api_key=api_key,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Booking failed"))

    await _update_lead_on_meeting(db, user.org_id, body.invitee_email)
    return result


@router.post("/calendly/scheduling-link")
async def create_calendly_link(
    event_type_uri: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.calendar.calendly_service import create_calendly_scheduling_link
    api_key = await resolve_api_key(db, user.org_id, "calendly")
    if not api_key:
        raise HTTPException(status_code=400, detail="Calendly not configured")
    return await create_calendly_scheduling_link(event_type_uri, api_key=api_key)


@router.get("/cal-com/event-types")
async def get_cal_com_event_types(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.calendar.cal_com_service import list_cal_com_event_types
    api_key = await resolve_api_key(db, user.org_id, "cal_com")
    if not api_key:
        raise HTTPException(status_code=400, detail="Cal.com not configured")
    return {"event_types": await list_cal_com_event_types(api_key)}


class CalComBookRequest(BaseModel):
    event_type_id: int
    attendee_name: str
    attendee_email: str
    start_time: str


@router.post("/cal-com/book")
async def book_cal_com(
    body: CalComBookRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.calendar.cal_com_service import book_cal_com_meeting
    api_key = await resolve_api_key(db, user.org_id, "cal_com")
    if not api_key:
        raise HTTPException(status_code=400, detail="Cal.com not configured")
    result = await book_cal_com_meeting(
        event_type_id=body.event_type_id,
        attendee_name=body.attendee_name,
        attendee_email=body.attendee_email,
        start_time=body.start_time,
        api_key=api_key,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Booking failed"))

    await _update_lead_on_meeting(db, user.org_id, body.attendee_email)
    return result


async def _update_lead_on_meeting(db: AsyncSession, org_id: str, email: str):
    from sqlalchemy import select
    from app.models.lead import Lead
    found = await db.execute(select(Lead).where(Lead.email == email, Lead.org_id == org_id))
    lead = found.scalar_one_or_none()
    if lead:
        lead.status = "meeting_scheduled"
        await db.flush()
