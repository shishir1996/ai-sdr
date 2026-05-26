import imaplib
import email as email_lib
import logging
import re
from datetime import datetime, timezone, timedelta
from email.header import decode_header
from typing import Optional

logger = logging.getLogger(__name__)

IMAP_PROVIDERS = {
    "hostinger": {"host": "imap.hostinger.com", "port": 993, "use_ssl": True},
    "gmail": {"host": "imap.gmail.com", "port": 993, "use_ssl": True},
    "outlook": {"host": "outlook.office365.com", "port": 993, "use_ssl": True},
    "hotmail": {"host": "imap-mail.outlook.com", "port": 993, "use_ssl": True},
    "zoho": {"host": "imap.zoho.com", "port": 993, "use_ssl": True},
    "zoho_eu": {"host": "imap.zoho.eu", "port": 993, "use_ssl": True},
    "yahoo": {"host": "imap.mail.yahoo.com", "port": 993, "use_ssl": True},
    "yandex": {"host": "imap.yandex.com", "port": 993, "use_ssl": True},
}

API_ONLY_PROVIDERS = {
    "sendgrid", "mailgun", "postmark", "amazon_ses", "sendinblue", "elasticemail", "protonmail",
}


def get_imap_settings(smtp_host: str, provider: str = "custom", stored_imap: Optional[dict] = None) -> Optional[dict]:
    if stored_imap and stored_imap.get("host"):
        return stored_imap
    if provider in API_ONLY_PROVIDERS:
        return None
    if provider in IMAP_PROVIDERS:
        return dict(IMAP_PROVIDERS[provider])
    host = smtp_host.replace("smtp.", "imap.")
    if host == smtp_host:
        host = f"imap.{smtp_host}"
    return {"host": host, "port": 993, "use_ssl": True}


def test_imap_connection(
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
) -> dict:
    try:
        if use_ssl:
            conn = imaplib.IMAP4_SSL(host, port, timeout=10)
        else:
            conn = imaplib.IMAP4(host, port, timeout=10)
        conn.login(username, password)
        conn.select("INBOX")
        conn.close()
        conn.logout()
        return {"success": True, "message": f"IMAP connection to {host}:{port} successful"}
    except imaplib.IMAP4.error as e:
        return {"success": False, "error": f"IMAP login failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _decode_mime_header(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _parse_email_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def check_imap_replies(
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
    lead_email: str,
    since: Optional[datetime] = None,
    max_results: int = 10,
) -> list[dict]:
    if not username or not password:
        logger.warning("IMAP credentials missing")
        return []

    try:
        if use_ssl:
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)
        conn.login(username, password)
    except Exception as e:
        logger.warning(f"IMAP connection failed for {host}: {e}")
        return []

    replies = []
    try:
        conn.select("INBOX")

        since_date = (since or datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{lead_email}" SINCE "{since_date}")'
        typ, message_ids = conn.search(None, search_criteria)

        if typ != "OK" or not message_ids[0]:
            return replies

        ids = message_ids[0].split()[-max_results:]
        for mid in ids:
            typ, msg_data = conn.fetch(mid, "(BODY.PEEK[HEADER] BODY.PEEK[TEXT])")
            if typ != "OK":
                continue

            raw_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
            if not raw_bytes:
                continue

            msg = email_lib.message_from_bytes(raw_bytes)

            in_reply_to = msg.get("In-Reply-To", "")
            if not in_reply_to:
                continue

            subject = _decode_mime_header(msg.get("Subject", ""))
            from_addr = msg.get("From", lead_email)
            date_str = msg.get("Date", "")
            rfc_message_id = msg.get("Message-ID", "").strip("<>")
            references = msg.get("References", "")
            message_id = str(mid, "utf-8") if isinstance(mid, bytes) else str(mid)

            thread_id = None
            if references:
                refs = [r.strip() for r in references.replace("\r\n", " ").split() if r.strip()]
                if refs:
                    thread_id = refs[0].strip("<>")
            if not thread_id and in_reply_to:
                thread_id = in_reply_to.strip("<>")
            if not thread_id:
                thread_id = rfc_message_id

            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain":
                        try:
                            body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        except Exception:
                            pass
                        break
                    elif ctype == "text/html" and not body_text:
                        try:
                            body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        except Exception:
                            pass
            else:
                try:
                    body_text = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
            body_text = re.sub(r"<[^>]+>", "", body_text).strip()
            body_text = re.sub(r"\s+", " ", body_text).strip()

            replies.append({
                "message_id": message_id,
                "rfc_message_id": rfc_message_id,
                "subject": subject or "",
                "snippet": body_text[:200],
                "in_reply_to": in_reply_to.strip("<>") if in_reply_to else "",
                "references": references,
                "from": from_addr,
                "date": date_str,
                "thread_id": thread_id,
            })

    except Exception as e:
        logger.warning(f"IMAP search failed: {e}")
    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass

    return replies
