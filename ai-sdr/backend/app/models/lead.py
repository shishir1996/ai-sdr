import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)
    industry = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    company_size = Column(String(50), nullable=True)
    revenue = Column(String(50), nullable=True)
    products_services = Column(Text, nullable=True)
    score = Column(Integer, default=0)
    status = Column(String(50), default="new")
    source = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(Text, nullable=True)
    is_blacklisted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="leads")
    deals = relationship("Deal", back_populates="lead")
    email_messages = relationship("EmailMessage", back_populates="lead")
    call_logs = relationship("CallLog", back_populates="lead")
