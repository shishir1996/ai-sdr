from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog, AiUsageLog, Notification
from app.utils.auth import get_current_admin

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: str = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    query = select(AuditLog).where(AuditLog.org_id == user.org_id)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "user_id": log.user_id,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/ai-usage")
async def list_ai_usage(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    query = (
        select(AiUsageLog)
        .where(AiUsageLog.org_id == user.org_id)
        .order_by(desc(AiUsageLog.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    total_tokens = sum(l.total_tokens for l in logs)
    total_cost = sum(l.cost for l in logs)

    return {
        "logs": [
            {
                "id": log.id,
                "provider": log.provider,
                "model": log.model,
                "action": log.action,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "total_tokens": log.total_tokens,
                "cost": log.cost,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "summary": {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        },
    }


@router.get("/notifications")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(desc(Notification.created_at))
        .limit(50)
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    from sqlalchemy import select
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    )
    notification = result.scalar_one_or_none()
    if notification:
        notification.is_read = True
        await db.flush()
    return {"status": "ok"}
