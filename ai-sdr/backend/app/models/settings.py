import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class OrgSettings(Base):
    __tablename__ = "org_settings"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, unique=True)
    sell_type = Column(String(50), default="product")
    product_name = Column(String(255), nullable=True)
    product_description = Column(Text, nullable=True)
    payment_link = Column(String(500), nullable=True)
    service_description = Column(Text, nullable=True)
    calendar_link = Column(String(500), nullable=True)
    knowledge_base = Column(Text, nullable=True)
    scraping_enabled = Column(Boolean, default=False)
    approved_countries = Column(Text, nullable=True)
    approved_categories = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
