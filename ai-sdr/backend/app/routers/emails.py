from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.campaign import EmailMessage
from app.models.lead import Lead
from app.utils.auth import get_current_user
from app.services.email.gmail_client import send_email
from app.services.integrations.resolver import resolve_api_key, resolve_api_secret, resolve_refresh_token
from app.services.integrations.service import set_refresh_token

router = APIRouter(prefix="/email", tags=["email"])


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body_html: str


@router.post("/send")
async def send_email_endpoint(
    body: SendEmailRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client_id = await resolve_api_key(db, user.org_id, "gmail")
    client_secret = await resolve_api_secret(db, user.org_id, "gmail")
    refresh_token = await resolve_refresh_token(db, user.org_id, "gmail")
    result = send_email(
        body.to, body.subject, body.body_html,
        client_id=client_id or None,
        client_secret=client_secret or None,
        refresh_token=refresh_token or None,
    )
    if not result or result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Email send failed"))

    msg = EmailMessage(
        org_id=user.org_id,
        lead_id="",
        from_email=user.email,
        to_email=body.to,
        subject=body.subject,
        body_html=body.body_html,
        status="sent",
        message_id=result.get("message_id"),
    )
    db.add(msg)
    await db.flush()
    return result


@router.get("/auth-url")
async def gmail_auth_url_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client_id = await resolve_api_key(db, user.org_id, "gmail")
    if not client_id:
        raise HTTPException(status_code=400, detail="Gmail Client ID not configured. Add it in Integrations first.")
    client_secret = await resolve_api_secret(db, user.org_id, "gmail")

    redirect_uri = (get_settings().GOOGLE_REDIRECT_URI or
                    f"{get_settings().FRONTEND_URL}/api/v1/email/oauth-callback")

    from google_auth_oauthlib.flow import Flow
    import json

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret or "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"],
    )
    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
    return {"auth_url": auth_url}


class WebhookPayload(BaseModel):
    event: str = "reply"
    lead_email: str
    subject: str = ""
    snippet: str = ""
    message_id: str = ""


@router.post("/webhook/reply")
async def email_reply_webhook(
    body: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    leads_result = await db.execute(
        select(Lead).where(Lead.org_id != "", Lead.email == body.lead_email).limit(1)
    )
    lead = leads_result.scalar_one_or_none()
    if not lead:
        return {"status": "ignored", "reason": "lead not found"}

    from app.services.sdr.orchestrator import _log_action, _update_lead_state
    await _log_action(db, lead.org_id, lead.id, "reply_detected", "email", f"Webhook reply: {body.snippet[:100]}", body.snippet, status="success")
    await _update_lead_state(db, lead.org_id, lead.id, "follow_up", "email")
    await db.commit()
    return {"status": "processed"}


class OAuthCallbackRequest(BaseModel):
    code: str


@router.post("/oauth-callback")
async def gmail_oauth_callback(
    body: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client_id = await resolve_api_key(db, user.org_id, "gmail")
    client_secret = await resolve_api_secret(db, user.org_id, "gmail")
    if not client_id:
        raise HTTPException(status_code=400, detail="Gmail not configured")

    redirect_uri = (get_settings().GOOGLE_REDIRECT_URI or
                    f"{get_settings().FRONTEND_URL}/api/v1/email/oauth-callback")

    from google_auth_oauthlib.flow import Flow
    import json

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret or "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"],
    )
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=body.code)

    credentials = flow.credentials
    refresh_token = credentials.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token received. Try revoking access and reconnecting.")

    await set_refresh_token(db, user.org_id, "gmail", refresh_token)
    await db.commit()

    return {"status": "connected", "email": credentials.id_token.get("email", "") if credentials.id_token else "Gmail account"}
