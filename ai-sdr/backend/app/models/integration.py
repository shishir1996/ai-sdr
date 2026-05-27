import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


INTEGRATION_PROVIDERS = [
    "together_ai", "openai", "anthropic", "google_ai", "openrouter",
    "gmail", "outlook",
    "vapi", "twilio",
    "apollo", "linkedin", "lusha", "rocketreach",
    "aws",
    "razorpay",
    "calendly", "cal_com",
    "google_places",
]


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    provider = Column(String(100), nullable=False)
    label = Column(String(255), nullable=True)

    # Credentials (encrypted)
    api_key_encrypted = Column(Text, nullable=True)
    api_secret_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    access_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Connection health
    connection_status = Column(String(50), default="disconnected")
    health_status = Column(String(50), default="unknown")
    last_health_check_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), default="never")

    # Account info
    account_email = Column(String(255), nullable=True)
    account_name = Column(String(255), nullable=True)
    account_id = Column(String(255), nullable=True)
    scopes = Column(Text, nullable=True)

    # OAuth state tracking
    oauth_state = Column(String(255), nullable=True)
    oauth_error = Column(Text, nullable=True)

    # Extra
    extra_config = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
