import json
import base64
from email.mime.text import MIMEText
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]


def _build_service(credentials: Credentials):
    return build("gmail", "v1", credentials=credentials)


def get_credentials_from_tokens(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> Optional[Credentials]:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def create_email(
    to: str,
    subject: str,
    body_html: str,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> dict[str, Any]:
    message = MIMEText(body_html, "html")
    message["to"] = to
    message["subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = references or in_reply_to
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_email(
    to: str,
    subject: str,
    body_html: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not client_id or not refresh_token:
        return {"status": "error", "error": "Gmail not fully configured. Complete OAuth flow in Integrations."}

    try:
        creds = get_credentials_from_tokens(client_id, client_secret or "", refresh_token)
        if not creds:
            return {"status": "error", "error": "Failed to create Gmail credentials"}
        service = _build_service(creds)
        message = create_email(to, subject, body_html, in_reply_to=in_reply_to, references=references)
        body = message
        if thread_id:
            body["threadId"] = thread_id
        sent = service.users().messages().send(userId="me", body=body).execute()
        return {"message_id": sent["id"], "thread_id": sent.get("threadId", ""), "status": "sent"}
    except HttpError as error:
        return {"status": "error", "error": str(error)}


def get_profile_email(client_id: str, client_secret: str, refresh_token: str) -> Optional[str]:
    try:
        creds = get_credentials_from_tokens(client_id, client_secret, refresh_token)
        if not creds:
            return None
        service = _build_service(creds)
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except HttpError:
        return None
