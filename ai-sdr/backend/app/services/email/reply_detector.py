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
        rfc_message_id = headers.get("Message-ID", "").strip("<>")
        references = headers.get("References", "")

        if in_reply_to:
            replies.append({
                "message_id": msg["id"],
                "rfc_message_id": rfc_message_id or msg["id"],
                "subject": subject,
                "snippet": snippet,
                "in_reply_to": in_reply_to.strip("<>"),
                "references": references,
                "from": headers.get("From", lead_email),
                "date": headers.get("Date", ""),
                "thread_id": detail.get("threadId", ""),
            })

    return replies


def check_imap_replies_for_profile(
    sdr_creds: Optional[dict],
    lead_email: str,
    since: Optional[datetime] = None,
) -> list[dict]:
    if not sdr_creds or sdr_creds.get("provider") != "smtp":
        return []
    from app.services.email.imap_client import check_imap_replies, get_imap_settings

    stored_imap = None
    if sdr_creds.get("imap_host"):
        stored_imap = {
            "host": sdr_creds["imap_host"],
            "port": sdr_creds.get("imap_port", 993),
            "use_ssl": sdr_creds.get("imap_use_ssl", True),
        }

    host = sdr_creds.get("host", "")
    provider = sdr_creds.get("provider_name", "custom")
    imap_cfg = get_imap_settings(host, provider, stored_imap=stored_imap)
    if not imap_cfg:
        return []

    imap_username = sdr_creds.get("imap_username") or sdr_creds.get("username", "")
    imap_password = sdr_creds.get("imap_password") or sdr_creds.get("password", "")

    return check_imap_replies(
        host=imap_cfg["host"],
        port=imap_cfg["port"],
        use_ssl=imap_cfg["use_ssl"],
        username=imap_username,
        password=imap_password,
        lead_email=lead_email,
        since=since,
    )


def check_email_replies(
    lead_email: str,
    since: Optional[datetime] = None,
    gmail_client_id: Optional[str] = None,
    gmail_secret: Optional[str] = None,
    gmail_refresh: Optional[str] = None,
    sdr_email_creds: Optional[dict] = None,
) -> list[dict]:
    replies = []
    if gmail_client_id and gmail_refresh:
        try:
            replies = check_for_replies(gmail_client_id, gmail_secret or "", gmail_refresh, lead_email, since)
            if replies:
                return replies
        except Exception as e:
            logger.warning(f"Gmail reply check failed: {e}")

    if sdr_email_creds and sdr_email_creds.get("provider") == "smtp":
        try:
            replies = check_imap_replies_for_profile(sdr_email_creds, lead_email, since)
        except Exception as e:
            logger.warning(f"IMAP reply check failed: {e}")

    return replies
