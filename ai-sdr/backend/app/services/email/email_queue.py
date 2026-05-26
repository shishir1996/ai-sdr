import asyncio
import json
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email.smtp_service import send_email_via_smtp


EMAIL_QUEUE: list[dict] = []
QUEUE_LOCK = asyncio.Lock()
MAX_QUEUE_SIZE = 1000


async def enqueue_email(
    db: AsyncSession,
    org_id: str,
    to_email: str,
    subject: str,
    body_html: str,
    smtp_config_id: Optional[str] = None,
    reply_to: Optional[str] = None,
    priority: int = 50,
) -> dict:
    async with QUEUE_LOCK:
        if len(EMAIL_QUEUE) >= MAX_QUEUE_SIZE:
            return {"success": False, "error": "Email queue is full"}

        task = {
            "id": f"{datetime.now(timezone.utc).timestamp()}-{org_id[:8]}",
            "org_id": org_id,
            "to_email": to_email,
            "subject": subject,
            "body_html": body_html,
            "smtp_config_id": smtp_config_id,
            "reply_to": reply_to,
            "priority": priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        EMAIL_QUEUE.append(task)
        return {"success": True, "queue_id": task["id"], "position": len(EMAIL_QUEUE)}


async def process_email_queue(db_factory):
    while True:
        try:
            async with QUEUE_LOCK:
                if not EMAIL_QUEUE:
                    await asyncio.sleep(1)
                    continue
                task = EMAIL_QUEUE.pop(0)

            async with db_factory() as db:
                result = await send_email_via_smtp(
                    db=db,
                    org_id=task["org_id"],
                    to_email=task["to_email"],
                    subject=task["subject"],
                    body_html=task["body_html"],
                    smtp_config_id=task.get("smtp_config_id"),
                    reply_to=task.get("reply_to"),
                )
                if result.get("success"):
                    task["status"] = "sent"
                else:
                    task["status"] = "failed"
                    task["error"] = result.get("error")
                    if task.get("retries", 0) < 3:
                        task["retries"] = task.get("retries", 0) + 1
                        async with QUEUE_LOCK:
                            EMAIL_QUEUE.append(task)

            await asyncio.sleep(0.5)
        except Exception:
            await asyncio.sleep(1)
