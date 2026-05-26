import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.smtp import SMTPConfig
from app.utils.crypto import decrypt_value
from app.services.audit.service import log_audit


class SMTPSender:
    def __init__(self, config: SMTPConfig):
        self.config = config
        self.password = decrypt_value(config.password_encrypted)

    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        reply_to: Optional[str] = None,
    ) -> dict:
        def _sync_send():
            msg = MIMEMultipart("alternative")
            sender_name = self.config.sender_name or self.config.sender_email
            msg["From"] = formataddr((sender_name, self.config.sender_email))
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            if reply_to or self.config.reply_to:
                msg["Reply-To"] = reply_to or self.config.reply_to

            msg.attach(MIMEText(body_html, "html"))

            if self.config.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config.host, self.config.port, context=context) as server:
                    server.login(self.config.username, self.password)
                    server.sendmail(self.config.sender_email, to_email, msg.as_string())
            else:
                with smtplib.SMTP(self.config.host, self.config.port) as server:
                    if self.config.use_tls:
                        server.starttls()
                    server.login(self.config.username, self.password)
                    server.sendmail(self.config.sender_email, to_email, msg.as_string())

            return {"success": True, "to": to_email, "subject": subject}

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, _sync_send)
            return result
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "error": "SMTP authentication failed"}
        except smtplib.SMTPRecipientsRefused:
            return {"success": False, "error": "Recipient refused"}
        except smtplib.SMTPSenderRefused:
            return {"success": False, "error": "Sender refused"}
        except smtplib.SMTPDataError as e:
            return {"success": False, "error": f"SMTP data error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def get_active_smtp_config(db: AsyncSession, org_id: str) -> Optional[SMTPConfig]:
    result = await db.execute(
        select(SMTPConfig).where(
            SMTPConfig.org_id == org_id,
            SMTPConfig.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def send_email_via_smtp(
    db: AsyncSession,
    org_id: str,
    to_email: str,
    subject: str,
    body_html: str,
    smtp_config_id: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    if smtp_config_id:
        result = await db.execute(
            select(SMTPConfig).where(SMTPConfig.id == smtp_config_id, SMTPConfig.org_id == org_id)
        )
        config = result.scalar_one_or_none()
    else:
        config = await get_active_smtp_config(db, org_id)

    if not config:
        return {"success": False, "error": "No active SMTP configuration found"}

    sender = SMTPSender(config)
    result = await sender.send(to_email, subject, body_html, reply_to)

    await log_audit(
        db=db,
        org_id=org_id,
        action="email_sent",
        resource_type="email",
        details={
            "to": to_email,
            "subject": subject,
            "smtp_provider": config.provider,
            "success": result.get("success"),
        },
    )

    return result


SMTP_PROVIDERS = {
    "hostinger": {
        "host": "smtp.hostinger.com",
        "port": 465,
        "use_ssl": True,
        "use_tls": False,
    },
    "gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "outlook": {
        "host": "smtp.office365.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "sendgrid": {
        "host": "smtp.sendgrid.net",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "mailgun": {
        "host": "smtp.mailgun.org",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "custom": {
        "host": "",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
}


SMTP_WARNINGS = {
    "gmail": "Gmail has strict sending limits (500/day for personal, 2000/day for Workspace). "
             "Use Hostinger or a dedicated SMTP provider for high-volume outreach.",
    "hostinger": "Hostinger Business Email supports up to 300 emails/day per mailbox. "
                 "For higher volumes, consider using multiple sender inboxes.",
}


def get_dns_guide(domain: str) -> dict:
    return {
        "mx": {
            "description": "Mail Exchange record for receiving emails",
            "records": [
                {"type": "MX", "host": "@", "value": f"mx1.hostinger.com", "priority": 10},
                {"type": "MX", "host": "@", "value": f"mx2.hostinger.com", "priority": 20},
            ],
        },
        "spf": {
            "description": "Sender Policy Framework - authorizes SMTP servers",
            "record": {
                "type": "TXT",
                "host": "@",
                "value": f'v=spf1 include:_spf.hostinger.com include:_spf.google.com ~all',
            },
        },
        "dkim": {
            "description": "DomainKeys Identified Mail - cryptographic email signing",
            "steps": [
                "1. Log into Hostinger hPanel → Email → Domain",
                "2. Select your domain and go to DKIM settings",
                "3. Enable DKIM and copy the generated TXT record value",
                "4. Add the TXT record to your domain DNS",
            ],
        },
        "dmarc": {
            "description": "Domain-based Message Authentication - policy for unauthenticated email",
            "record": {
                "type": "TXT",
                "host": "_dmarc",
                "value": "v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain}; pct=100",
            },
        },
        "tracking": {
            "description": "Custom tracking domain for open/click tracking",
            "record": {
                "type": "CNAME",
                "host": "track",
                "value": "{tracking_provider_target}",
            },
        },
    }
