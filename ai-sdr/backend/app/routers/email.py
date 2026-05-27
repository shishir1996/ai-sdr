import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from urllib.parse import urlencode

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.integrations.service import get_integration, set_integration, set_refresh_token, get_api_key, get_api_secret
from app.services.integrations.resolver import resolve_api_key, resolve_api_secret, resolve_refresh_token, get_google_oauth_flow
from app.services.sdr.credentials import encrypt_sdr_credentials, decrypt_sdr_credentials
from app.models.agent import SDRProfile

router = APIRouter(prefix="/email", tags=["email"])

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]


@router.get("/sdr-auth-url/{sdr_profile_id}")
async def get_sdr_gmail_auth_url(
    sdr_profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == sdr_profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    integration = await get_integration(db, user.org_id, "gmail")
    if not integration or not integration.api_key_encrypted or not integration.api_secret_encrypted:
        raise HTTPException(status_code=400, detail="Gmail API credentials not configured in Admin > Integrations")

    from app.utils.crypto import decrypt_value
    client_id = decrypt_value(integration.api_key_encrypted)
    redirect_uri = f"{'https://api.offdx.in' if __import__('app.config', fromlist=['get_settings']).get_settings().IS_PRODUCTION else 'http://localhost:8000'}/api/v1/email/sdr-oauth-callback/{sdr_profile_id}"

    flow = get_google_oauth_flow(client_id, redirect_uri, SCOPES)
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/sdr-oauth-callback/{sdr_profile_id}")
async def sdr_gmail_oauth_callback(
    sdr_profile_id: str,
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == sdr_profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    integration = await get_integration(db, profile.org_id, "gmail")
    if not integration:
        raise HTTPException(status_code=400, detail="Gmail integration not configured")

    from app.utils.crypto import decrypt_value
    client_id = decrypt_value(integration.api_key_encrypted)
    client_secret = decrypt_value(integration.api_secret_encrypted)
    redirect_uri = f"{'https://api.offdx.in' if __import__('app.config', fromlist=['get_settings']).get_settings().IS_PRODUCTION else 'http://localhost:8000'}/api/v1/email/sdr-oauth-callback/{sdr_profile_id}"

    flow = get_google_oauth_flow(client_id, redirect_uri, SCOPES)
    flow.fetch_token(code=code)

    credentials = flow.credentials
    if not credentials.refresh_token:
        existing = decrypt_sdr_credentials(profile.email_credentials_encrypted)
        refresh_token = existing.get("refresh_token") if existing else None
    else:
        refresh_token = credentials.refresh_token

    from google.oauth2.credentials import Credentials
    creds = Credentials(
        token=credentials.token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    gmail_profile = service.users().getProfile(userId="me").execute()
    sender_email = gmail_profile.get("emailAddress", "")

    email_creds = {
        "provider": "gmail",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "sender_email": sender_email,
        "sender_name": profile.name or "AI SDR",
    }
    profile.email_credentials_encrypted = encrypt_sdr_credentials(email_creds)
    await db.flush()

    html = f"""<html><body><script>
window.opener.postMessage({{type: 'sdr-gmail-connected', sdrId: '{sdr_profile_id}', email: '{sender_email}'}}, '*');
window.close();
</script><p>Gmail connected! You can close this window.</p></body></html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)


class SDRGmailStatus(BaseModel):
    connected: bool
    email: str = ""


@router.get("/sdr-status/{sdr_profile_id}")
async def get_sdr_email_status(
    sdr_profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == sdr_profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    creds = decrypt_sdr_credentials(profile.email_credentials_encrypted)
    if creds:
        return {"connected": True, "provider": creds.get("provider", ""), "email": creds.get("sender_email", ""), "sender_name": creds.get("sender_name", "")}
    return {"connected": False, "provider": "", "email": "", "sender_name": ""}


# ============================================================
# Outlook / Microsoft 365 OAuth (per-SDR)
# ============================================================

OUTLOOK_SCOPES = [
    "openid",
    "profile",
    "offline_access",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/User.Read",
]

OUTLOOK_AUTHORITY = "https://login.microsoftonline.com/common"
OUTLOOK_AUTH_URL = f"{OUTLOOK_AUTHORITY}/oauth2/v2.0/authorize"
OUTLOOK_TOKEN_URL = f"{OUTLOOK_AUTHORITY}/oauth2/v2.0/token"


def _get_redirect_uri(sdr_profile_id: str) -> str:
    from app.config import get_settings
    base = "https://api.offdx.in" if get_settings().IS_PRODUCTION else "http://localhost:8000"
    return f"{base}/api/v1/email/sdr-outlook-oauth-callback/{sdr_profile_id}"


@router.get("/sdr-outlook-auth-url/{sdr_profile_id}")
async def get_sdr_outlook_auth_url(
    sdr_profile_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == sdr_profile_id, SDRProfile.org_id == user.org_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    integration = await get_integration(db, user.org_id, "outlook")
    if not integration or not integration.api_key_encrypted or not integration.api_secret_encrypted:
        raise HTTPException(status_code=400, detail="Outlook API credentials not configured in Admin > Integrations")

    from app.utils.crypto import decrypt_value
    client_id = decrypt_value(integration.api_key_encrypted)
    redirect_uri = _get_redirect_uri(sdr_profile_id)

    params = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(OUTLOOK_SCOPES),
        "response_mode": "query",
        "prompt": "consent",
    })
    auth_url = f"{OUTLOOK_AUTH_URL}?{params}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/sdr-outlook-oauth-callback/{sdr_profile_id}")
async def sdr_outlook_oauth_callback(
    sdr_profile_id: str,
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SDRProfile).where(SDRProfile.id == sdr_profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="SDR profile not found")

    integration = await get_integration(db, profile.org_id, "outlook")
    if not integration:
        raise HTTPException(status_code=400, detail="Outlook integration not configured")

    from app.utils.crypto import decrypt_value
    client_id = decrypt_value(integration.api_key_encrypted)
    client_secret = decrypt_value(integration.api_secret_encrypted)
    redirect_uri = _get_redirect_uri(sdr_profile_id)

    import httpx
    async with httpx.AsyncClient() as http:
        token_resp = await http.post(
            OUTLOOK_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_resp.text}")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    async with httpx.AsyncClient() as http:
        user_resp = await http.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if user_resp.status_code != 200:
        sender_email = "unknown@outlook.com"
        sender_name = profile.name or "AI SDR"
    else:
        user_data = user_resp.json()
        sender_email = user_data.get("mail") or user_data.get("userPrincipalName", "unknown@outlook.com")
        sender_name = user_data.get("displayName") or profile.name or "AI SDR"

    email_creds = {
        "provider": "outlook",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token or "",
        "access_token": access_token or "",
        "sender_email": sender_email,
        "sender_name": sender_name,
    }
    profile.email_credentials_encrypted = encrypt_sdr_credentials(email_creds)
    await db.flush()

    html = f"""<html><body><script>
window.opener.postMessage({{type: 'sdr-outlook-connected', sdrId: '{sdr_profile_id}', email: '{sender_email}'}}, '*');
window.close();
</script><p>Outlook connected! You can close this window.</p></body></html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)
