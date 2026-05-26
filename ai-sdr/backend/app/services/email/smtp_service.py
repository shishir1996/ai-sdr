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
    "hotmail": {
        "host": "smtp-mail.outlook.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "zoho": {
        "host": "smtp.zoho.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "zoho_eu": {
        "host": "smtp.zoho.eu",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "yahoo": {
        "host": "smtp.mail.yahoo.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "yandex": {
        "host": "smtp.yandex.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "protonmail": {
        "host": "127.0.0.1",
        "port": 1025,
        "use_ssl": False,
        "use_tls": False,
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
    "postmark": {
        "host": "smtp.postmarkapp.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "amazon_ses": {
        "host": "email-smtp.us-east-1.amazonaws.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "sendinblue": {
        "host": "smtp-relay.sendinblue.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True,
    },
    "elasticemail": {
        "host": "smtp.elasticemail.com",
        "port": 2525,
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
    "hotmail": "Hotmail/Outlook.com has strict sending limits (~300/day). Use Microsoft 365 for higher volumes.",
    "zoho": "Zoho Mail free plan: 5 emails/day. Paid plans: up to 500/day per mailbox.",
    "zoho_eu": "Same as Zoho Mail but on EU servers (smtp.zoho.eu).",
    "yahoo": "Yahoo Mail has strict anti-spam limits. Not recommended for high-volume outreach.",
    "yandex": "Yandex Mail supports up to 500 emails/day for paid plans.",
    "protonmail": "ProtonMail requires ProtonMail Bridge (desktop app) for SMTP. Set host to localhost:1025 after installing Bridge.",
    "sendgrid": "SendGrid free tier: 100 emails/day. Paid: higher limits available.",
    "mailgun": "Mailgun offers a flexible email API with high sending limits on paid plans.",
    "postmark": "Postmark is designed for transactional emails only. Use with dedicated sending IP.",
    "amazon_ses": "AWS SES requires domain verification and may need sending limit increase for new accounts.",
    "sendinblue": "Brevo (Sendinblue) free tier: 300 emails/day. Paid plans available.",
    "elasticemail": "Elastic Email offers competitive pricing with high daily limits on paid plans.",
}


def get_dns_guide(domain: str) -> dict:
    return {
        "mx": {
            "description": "Mail Exchange record for receiving emails and routing to your email provider",
            "records": [
                {"type": "MX", "host": "@", "value": f"mx1.hostinger.com", "priority": 10},
                {"type": "MX", "host": "@", "value": f"mx2.hostinger.com", "priority": 20},
            ],
            "providers": {
                "hostinger": "Set MX to mx1.hostinger.com (priority 10) and mx2.hostinger.com (priority 20)",
                "google": "Set MX to aspmx.l.google.com (priority 1), alt1.aspmx.l.google.com (priority 5), etc.",
                "cloudflare": "Add MX records in DNS → Add Record → Type MX. Leave proxy off (grey cloud).",
                "godaddy": "Go to DNS Records → Add → MX. Use @ host with your provider's mail server.",
            },
        },
        "spf": {
            "description": "Sender Policy Framework - authorizes which servers can send email for your domain",
            "record": {
                "type": "TXT",
                "host": "@",
                "value": f'v=spf1 include:_spf.hostinger.com include:_spf.google.com ~all',
            },
            "providers": {
                "hostinger": "Go to hPanel → DNS Zone Manager → Add TXT record. Host: @, Value: the SPF record above.",
                "cloudflare": "DNS → Add Record → Type TXT. Name: @. Value: the SPF record. Disable proxy (grey cloud).",
                "godaddy": "DNS Records → Add → TXT. Host: @. TXT Value: the SPF record. TTL: 1 hour.",
                "namecheap": "Advanced DNS → Add New Record → TXT Record. Host: @. Value: the SPF record above.",
            },
        },
        "dkim": {
            "description": "DomainKeys Identified Mail - cryptographic signing to prevent spoofing",
            "steps": [
                "1. Log into Hostinger hPanel → Email → Domain → DKIM",
                "2. Select your domain and toggle DKIM ON",
                "3. Copy the generated TXT record name (e.g., hostinger._domainkey) and value",
                "4. Add the TXT record to your domain DNS",
                "5. If using Cloudflare, ensure proxy is disabled (grey cloud) for DKIM records",
            ],
            "providers": {
                "hostinger": "hPanel → Email → Domain → DKIM → Enable. Copy the generated TXT record and add to DNS.",
                "cloudflare": "DNS → Add Record → TXT. Name: hostinger._domainkey. Paste the DKIM value from Hostinger.",
                "godaddy": "DNS Records → Add → TXT. Host: hostinger._domainkey. Value: DKIM key from Hostinger.",
                "google_workspace": "Google Admin → Apps → Gmail → Authenticate Email → Generate DKIM key.",
            },
        },
        "dmarc": {
            "description": "Domain-based Message Authentication, Reporting & Conformance - tells receivers how to handle unauthenticated email",
            "record": {
                "type": "TXT",
                "host": "_dmarc",
                "value": f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain}; pct=100",
            },
            "providers": {
                "hostinger": "hPanel → DNS Zone Manager → Add TXT record. Host: _dmarc. Value: the DMARC record above.",
                "cloudflare": "DNS → Add Record → TXT. Name: _dmarc. Value: the DMARC record. Grey cloud only.",
                "godaddy": "DNS Records → Add → TXT. Host: _dmarc. TXT Value: the DMARC record. TTL: 1 hour.",
                "namecheap": "Advanced DNS → Add New Record → TXT Record. Host: _dmarc. Value: DMARC record above.",
            },
        },
        "tracking": {
            "description": "Custom tracking domain for open/click tracking (required by SendGrid, Mailgun, etc.)",
            "record": {
                "type": "CNAME",
                "host": "track",
                "value": "{tracking_provider_target}",
            },
        },
    }
