import logging
import httpx
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY

AUTH_BASE = f"{SUPABASE_URL}/auth/v1"


async def _request(method: str, path: str, body: Optional[dict] = None, use_service_role: bool = False) -> dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Supabase URL and Anon Key must be configured")

    key = SUPABASE_SERVICE_KEY if use_service_role else SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{AUTH_BASE}{path}", json=body, headers=headers)

    if resp.status_code >= 400:
        error_detail = resp.text
        try:
            error_json = resp.json()
            error_detail = error_json.get("error_description") or error_json.get("msg") or error_json.get("error", resp.text)
        except Exception:
            pass
        logger.warning(f"Supabase Auth API error {resp.status_code}: {error_detail}")
        raise Exception(error_detail)

    return resp.json() if resp.text else {}


async def supabase_signup(email: str, password: str, redirect_to: str = "") -> dict:
    body: dict = {"email": email, "password": password}
    if redirect_to:
        body["gotrue_meta_security"] = {"redirect_to": redirect_to}
    body["data"] = {"email_redirect_to": redirect_to or f"{settings.FRONTEND_URL}/login?verified=true"}
    return await _request("POST", "/signup", body)


async def supabase_login(email: str, password: str) -> dict:
    return await _request("POST", "/token?grant_type=password", {"email": email, "password": password})


async def supabase_send_password_reset(email: str, redirect_to: str = "") -> dict:
    body = {"email": email}
    if redirect_to:
        body["redirect_to"] = redirect_to
    return await _request("POST", "/recover", body)


async def supabase_reset_password(access_token: str, new_password: str) -> dict:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(
            f"{AUTH_BASE}/user",
            json={"password": new_password},
            headers=headers,
        )
    if resp.status_code >= 400:
        error_detail = resp.text
        try:
            error_json = resp.json()
            error_detail = error_json.get("error_description") or error_json.get("msg") or resp.text
        except Exception:
            pass
        raise Exception(error_detail)
    return resp.json()


async def supabase_get_user(access_token: str) -> dict:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{AUTH_BASE}/user", headers=headers)
    if resp.status_code >= 400:
        raise Exception("Failed to get user")
    return resp.json()


async def supabase_admin_get_user_by_email(email: str) -> Optional[dict]:
    if not SUPABASE_SERVICE_KEY:
        logger.warning("Supabase service key not configured, cannot admin lookup user")
        return None
    try:
        data = await _request("GET", f"/admin/users?filter%5Bemail%5D=eq.{email}", use_service_role=True)
        users = data.get("users", [])
        return users[0] if users else None
    except Exception as e:
        logger.warning(f"Failed to admin lookup user by email: {e}")
        return None
