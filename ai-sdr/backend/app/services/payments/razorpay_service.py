import httpx
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def create_payment_link(
    amount: float,
    description: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str = "",
    currency: str = "INR",
    api_key_id: str = "",
    api_key_secret: str = "",
) -> dict:
    if not api_key_id or not api_key_secret:
        logger.warning("Razorpay not configured")
        return {"success": False, "error": "Razorpay not configured"}

    auth = (api_key_id, api_key_secret)
    payload = {
        "amount": int(round(amount * 100)),
        "currency": currency,
        "description": description[:255],
        "customer": {
            "name": customer_name[:255],
            "email": customer_email,
            "contact": customer_phone,
        },
        "notify": {
            "sms": bool(customer_phone),
            "email": True,
        },
        "callback_url": "",
        "callback_method": "get",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.razorpay.com/v1/payment_links",
                json=payload,
                auth=auth,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "payment_link_id": data.get("id", ""),
                    "short_url": data.get("short_url", ""),
                    "status": data.get("status", ""),
                    "amount": amount,
                    "currency": currency,
                }
            else:
                error_body = resp.text
                logger.error("Razorpay error: %s — %s", resp.status_code, error_body)
                return {"success": False, "error": f"Razorpay API error: {error_body}"}
        except Exception as e:
            logger.error("Razorpay request failed: %s", e)
            return {"success": False, "error": str(e)}


async def get_payment_link_status(
    payment_link_id: str,
    api_key_id: str = "",
    api_key_secret: str = "",
) -> dict:
    if not api_key_id or not api_key_secret:
        return {"success": False, "error": "Razorpay not configured"}

    auth = (api_key_id, api_key_secret)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"https://api.razorpay.com/v1/payment_links/{payment_link_id}",
                auth=auth,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "payment_link_id": data.get("id", ""),
                    "short_url": data.get("short_url", ""),
                    "status": data.get("status", ""),
                    "paid": data.get("paid", False),
                    "amount_paid": float(data.get("amount_paid", 0)) / 100,
                    "payments": data.get("payments", []),
                }
            return {"success": False, "error": f"Status check failed: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def list_payment_links(
    page: int = 1,
    per_page: int = 25,
    api_key_id: str = "",
    api_key_secret: str = "",
) -> list[dict]:
    if not api_key_id or not api_key_secret:
        return []
    auth = (api_key_id, api_key_secret)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.razorpay.com/v1/payment_links",
                params={"count": per_page, "skip": (page - 1) * per_page},
                auth=auth,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "id": item.get("id", ""),
                        "short_url": item.get("short_url", ""),
                        "amount": float(item.get("amount", 0)) / 100,
                        "status": item.get("status", ""),
                        "paid": item.get("paid", False),
                        "created_at": item.get("created_at", 0),
                        "customer": (item.get("customer") or {}).get("name", ""),
                    }
                    for item in data.get("payment_links", [])
                ]
        except Exception as e:
            logger.error("Failed to list Razorpay links: %s", e)
    return []
