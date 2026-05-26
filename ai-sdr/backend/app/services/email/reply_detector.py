import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _build_service(client_id: str, client_secret: str, refresh_token: str):
    if not _GOOGLE_AVAILABLE:
        raise ImportError("google-api-python-client not installed")
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
    return build("gmail", "v1", credentials=creds)


def check_for_replies(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    lead_email: str,
    since: Optional[datetime] = None,
) -> list[dict]:
    if not client_id or not refresh_token:
        return []

    try:
        service = _build_service(client_id, client_secret, refresh_token)
    except Exception as e:
        logger.warning(f"Failed to build Gmail service: {e}")
        return []

    query = f"from:{lead_email} after:{(since or datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y/%m/%d')}"
    try:
        results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
    except HttpError as e:
        logger.warning(f"Gmail API error checking replies: {e}")
        return []

    messages = results.get("messages", [])
    replies = []
    for msg in messages:
        detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        in_reply_to = headers.get("In-Reply-To", "")
        subject = headers.get("Subject", "")
        snippet = detail.get("snippet", "")

        if in_reply_to:
            replies.append({
                "message_id": msg["id"],
                "subject": subject,
                "snippet": snippet,
                "in_reply_to": in_reply_to,
                "from": headers.get("From", lead_email),
                "date": headers.get("Date", ""),
                "thread_id": detail.get("threadId", ""),
            })

    return replies
