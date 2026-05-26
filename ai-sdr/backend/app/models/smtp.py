import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class SMTPConfig(Base):
    __tablename__ = "smtp_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    provider = Column(String(50), default="custom")
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=587)
    use_tls = Column(Boolean, default=True)
    use_ssl = Column(Boolean, default=False)
    username = Column(String(255), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    sender_name = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=False)
    reply_to = Column(String(255), nullable=True)
    daily_limit = Column(Integer, default=300)
    hourly_limit = Column(Integer, default=30)
    warmup_enabled = Column(Boolean, default=False)
    warmup_daily_increment = Column(Integer, default=5)
    warmup_current_daily = Column(Integer, default=10)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
