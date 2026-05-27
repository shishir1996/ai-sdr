import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.integration import Integration
from app.utils.crypto import encrypt_value, decrypt_value


OAUTH_PROVIDERS = {
    "gmail": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        "requires_client_creds": True,
    },
    "outlook": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "https://outlook.office.com/mail.send",
            "https://outlook.office.com/mail.read",
            "offline_access",
            "openid",
            "profile",
            "email",
        ],
        "requires_client_creds": True,
    },
    "linkedin": {
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": ["r_liteprofile", "r_emailaddress", "w_member_social"],
        "requires_client_creds": True,
    },
    "apollo": {
        "auth_url": None,
        "token_url": None,
        "scopes": [],
        "requires_client_creds": False,
    },
    "lusha": {
        "auth_url": None,
        "token_url": None,
        "scopes": [],
        "requires_client_creds": False,
    },
    "rocketreach": {
        "auth_url": None,
        "token_url": None,
        "scopes": [],
        "requires_client_creds": False,
    },
}


async def initiate_oauth(db: AsyncSession, org_id: str, provider: str) -> dict:
    meta = OAUTH_PROVIDERS.get(provider)
    if not meta:
        return {"can_oauth": False, "reason": "Provider does not support OAuth"}

    integration = await _get_integration(db, org_id, provider)
    client_id = _decrypt(integration.api_key_encrypted) if integration else None

    if meta.get("requires_client_creds") and not client_id:
        return {
            "can_oauth": False,
            "reason": "Client ID not configured. Admin must configure provider credentials in Integrations panel first.",
            "setup_required": True,
        }

    state = secrets.token_urlsafe(32)
    if integration:
        integration.oauth_state = state
        await db.flush()

    redirect_uri = _get_redirect_uri(provider)

    auth_url = None
    if meta["auth_url"] and client_id:
        scopes = " ".join(meta["scopes"])
        auth_url = (
            f"{meta['auth_url']}?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"state={state}&"
            f"access_type=offline&"
            f"prompt=consent"
        )

    return {
        "can_oauth": True,
        "auth_url": auth_url,
        "state": state,
        "redirect_uri": redirect_uri,
        "setup_required": False,
    }


async def complete_oauth(
    db: AsyncSession,
    org_id: str,
    provider: str,
    code: str,
    state: str,
) -> dict:
    integration = await _get_integration(db, org_id, provider)
    if not integration:
        return {"status": "error", "error": "Integration not configured"}

    if integration.oauth_state and integration.oauth_state != state:
        return {"status": "error", "error": "OAuth state mismatch. Please try again."}

    meta = OAUTH_PROVIDERS.get(provider)
    if not meta or not meta["token_url"]:
        return {"status": "error", "error": "Provider does not support OAuth code exchange"}

    client_id = _decrypt(integration.api_key_encrypted) or ""
    client_secret = _decrypt(integration.api_secret_encrypted) or ""
    redirect_uri = _get_redirect_uri(provider)

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                meta["token_url"],
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_data = resp.json()
    except Exception as e:
        return {"status": "error", "error": f"Token exchange failed: {str(e)}"}

    if "error" in token_data:
        integration.oauth_error = json.dumps(token_data)
        await db.flush()
        return {"status": "error", "error": token_data.get("error_description", token_data["error"])}

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    scope = token_data.get("scope", "")

    now = datetime.now(timezone.utc)
    integration.access_token_encrypted = encrypt_value(access_token) if access_token else None
    if refresh_token:
        integration.refresh_token_encrypted = encrypt_value(refresh_token)
    integration.token_expires_at = now + timedelta(seconds=expires_in)
    integration.connection_status = "connected"
    integration.health_status = "healthy"
    integration.last_health_check_at = now
    integration.scopes = scope
    integration.oauth_state = None
    integration.oauth_error = None
    integration.is_active = True
    integration.account_email = token_data.get("email", "")
    integration.account_name = token_data.get("name", "")

    await _fetch_account_info(db, integration, provider, access_token)

    await db.flush()
    return {"status": "connected", "provider": provider, "account_email": integration.account_email}


async def check_connection_health(db: AsyncSession, org_id: str, provider: str) -> dict:
    integration = await _get_integration(db, org_id, provider)
    if not integration:
        return {"status": "not_configured", "connected": False}

    if integration.connection_status == "disconnected":
        return {"status": "disconnected", "connected": False}

    now = datetime.now(timezone.utc)
    if integration.token_expires_at and integration.token_expires_at < now:
        integration.connection_status = "expired"
        integration.health_status = "error"
        await db.flush()
        return {"status": "expired", "connected": False, "error": "Token expired"}

    access_token = _decrypt(integration.access_token_encrypted)
    if not access_token:
        refresh_success = await _refresh_token_if_needed(db, integration)
        if not refresh_success:
            return {"status": "no_token", "connected": False}
        access_token = _decrypt(integration.access_token_encrypted)

    healthy = await _ping_provider(provider, access_token)
    integration.last_health_check_at = now
    integration.health_status = "healthy" if healthy else "error"
    if not healthy:
        integration.connection_status = "error"
    await db.flush()

    return {
        "status": integration.connection_status,
        "connected": integration.connection_status == "connected",
        "health": integration.health_status,
        "account_email": integration.account_email,
        "last_checked": now.isoformat(),
    }


async def refresh_token_if_expired(db: AsyncSession, org_id: str, provider: str) -> bool:
    integration = await _get_integration(db, org_id, provider)
    if not integration:
        return False
    return await _refresh_token_if_needed(db, integration)


async def get_provider_status(db: AsyncSession, org_id: str, provider: str) -> dict:
    integration = await _get_integration(db, org_id, provider)
    if not integration:
        return {
            "provider": provider,
            "connected": False,
            "configured": False,
            "status": "not_configured",
        }
    return {
        "provider": provider,
        "connected": integration.connection_status == "connected",
        "configured": True,
        "status": integration.connection_status,
        "health": integration.health_status,
        "account_email": integration.account_email,
        "account_name": integration.account_name,
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "last_health_check": integration.last_health_check_at.isoformat() if integration.last_health_check_at else None,
        "has_refresh_token": bool(integration.refresh_token_encrypted),
        "token_expires_at": integration.token_expires_at.isoformat() if integration.token_expires_at else None,
    }


async def get_connected_accounts(db: AsyncSession, org_id: str) -> list[dict]:
    result = await db.execute(
        select(Integration).where(
            Integration.org_id == org_id,
            Integration.provider.in_(["gmail", "outlook", "linkedin", "apollo", "lusha", "rocketreach"]),
        )
    )
    accounts = []
    for integ in result.scalars().all():
        accounts.append({
            "id": integ.id,
            "provider": integ.provider,
            "connected": integ.connection_status == "connected",
            "status": integ.connection_status,
            "health": integ.health_status,
            "account_email": integ.account_email,
            "account_name": integ.account_name,
            "last_sync_at": integ.last_sync_at.isoformat() if integ.last_sync_at else None,
        })
    return accounts


async def _get_integration(db: AsyncSession, org_id: str, provider: str) -> Optional[Integration]:
    result = await db.execute(
        select(Integration).where(Integration.org_id == org_id, Integration.provider == provider)
    )
    return result.scalar_one_or_none()


async def _refresh_token_if_needed(db: AsyncSession, integration: Integration) -> bool:
    if not integration.refresh_token_encrypted:
        return False

    now = datetime.now(timezone.utc)
    if integration.token_expires_at and integration.token_expires_at > now:
        return True

    refresh_token = _decrypt(integration.refresh_token_encrypted)
    if not refresh_token:
        return False

    meta = OAUTH_PROVIDERS.get(integration.provider)
    if not meta or not meta["token_url"]:
        return False

    client_id = _decrypt(integration.api_key_encrypted) or ""
    client_secret = _decrypt(integration.api_secret_encrypted) or ""

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                meta["token_url"],
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Accept": "application/json"},
            )
            token_data = resp.json()
    except Exception:
        integration.connection_status = "error"
        integration.health_status = "error"
        return False

    if "error" in token_data:
        integration.connection_status = "expired"
        integration.health_status = "error"
        integration.oauth_error = json.dumps(token_data)
        return False

    new_access = token_data.get("access_token")
    new_refresh = token_data.get("refresh_token", refresh_token)
    expires_in = token_data.get("expires_in", 3600)

    integration.access_token_encrypted = encrypt_value(new_access) if new_access else None
    integration.refresh_token_encrypted = encrypt_value(new_refresh)
    integration.token_expires_at = now + timedelta(seconds=expires_in)
    integration.connection_status = "connected"
    integration.health_status = "healthy"
    return True


async def _fetch_account_info(db: AsyncSession, integration: Integration, provider: str, access_token: str) -> None:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            if provider == "gmail":
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    integration.account_email = data.get("email") or integration.account_email
                    integration.account_name = data.get("name") or integration.account_name
                    integration.account_id = data.get("id")
            elif provider == "outlook":
                resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    integration.account_email = data.get("mail") or data.get("userPrincipalName") or integration.account_email
                    integration.account_name = data.get("displayName") or integration.account_name
                    integration.account_id = data.get("id")
            elif provider == "linkedin":
                resp = await client.get(
                    "https://api.linkedin.com/v2/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    integration.account_id = data.get("id")
                    localized = data.get("localizedFirstName", "") + " " + data.get("localizedLastName", "")
                    integration.account_name = localized.strip() or integration.account_name
    except Exception:
        pass


async def _ping_provider(provider: str, access_token: str) -> bool:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            if provider == "gmail":
                resp = await client.get(
                    "https://www.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return resp.status_code == 200
            elif provider == "outlook":
                resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return resp.status_code == 200
            elif provider == "linkedin":
                resp = await client.get(
                    "https://api.linkedin.com/v2/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return resp.status_code == 200
            return True
    except Exception:
        return False


def _get_redirect_uri(provider: str) -> str:
    from app.config import settings
    base = settings.FRONTEND_URL or "http://localhost:3000"
    return f"{base}/auth/callback/{provider}"


def _decrypt(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    try:
        return decrypt_value(val)
    except Exception:
        return None
