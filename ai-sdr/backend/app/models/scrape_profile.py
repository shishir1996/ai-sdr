from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from app.database import Base
import uuid


class ScrapeProfile(Base):
    __tablename__ = "scrape_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    persona_description = Column(Text, nullable=False, default="")
    business_category = Column(String(255), nullable=False, default="")
    country = Column(String(100), nullable=False, default="")
    directory_urls = Column(Text, nullable=False, default="")
    selected_fields = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
