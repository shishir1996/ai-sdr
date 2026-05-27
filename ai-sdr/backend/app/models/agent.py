import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


LEAD_STATES = [
    "new",
    "researching",
    "researched",
    "contacting_email",
    "contacted_email",
    "contacting_linkedin",
    "contacted_linkedin",
    "contacting_call",
    "contacted_call",
    "follow_up",
    "meeting_scheduled",
    "payment_sent",
    "negotiating",
    "closed_won",
    "closed_lost",
    "archived",
]


class SDRProfile(Base):
    __tablename__ = "sdr_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)

    # SDR Identity
    name = Column(String(255), nullable=False, default="AI SDR")
    region = Column(String(255), nullable=True)

    # What to sell
    sell_type = Column(String(50), nullable=False)
    product_name = Column(String(255), nullable=True)
    product_description = Column(Text, nullable=True)
    payment_link = Column(String(500), nullable=True)
    service_description = Column(Text, nullable=True)
    calendar_link = Column(String(500), nullable=True)

    # ICP
    target_titles = Column(Text, nullable=True)
    target_industries = Column(Text, nullable=True)
    target_locations = Column(Text, nullable=True)
    target_company_size_min = Column(Integer, nullable=True)
    target_company_size_max = Column(Integer, nullable=True)

    # Lead sources
    lead_sources = Column(Text, nullable=True)

    # Outreach settings
    sdr_personality = Column(Text, nullable=True)
    outreach_tone = Column(String(50), default="professional")
    max_daily_emails = Column(Integer, default=20)
    max_daily_calls = Column(Integer, default=10)
    max_daily_linkedin = Column(Integer, default=15)
    max_daily_likes = Column(Integer, default=20)
    max_daily_comments = Column(Integer, default=10)
    linkedin_connect_enabled = Column(Boolean, default=True)
    linkedin_dm_enabled = Column(Boolean, default=True)
    linkedin_like_enabled = Column(Boolean, default=False)
    linkedin_comment_enabled = Column(Boolean, default=False)
    linkedin_engagement_feed = Column(Text, nullable=True)
    web_scrape_targets = Column(Text, nullable=True)

    # Auto-scrape
    auto_scrape_enabled = Column(Boolean, default=False)
    scrape_business_category = Column(String(255), nullable=True)
    scrape_country = Column(String(100), nullable=True)
    scrape_directory_urls = Column(Text, nullable=True)

    # Campaign sequence
    campaign_sequence = Column(Text, nullable=True)

    # ============================================================
    # Per-SDR Credentials (encrypted JSON blobs)
    # ============================================================
    # Email credentials
    # For Gmail: {"provider":"gmail","client_id":"...","client_secret":"...","refresh_token":"...","sender_email":"...","sender_name":"..."}
    # For SMTP:  {"provider":"smtp","host":"...","port":587,"username":"...","password":"...","sender_email":"...","sender_name":"..."}
    email_credentials_encrypted = Column(Text, nullable=True)

    # LinkedIn credentials: {"email":"...","password":"..."}
    linkedin_credentials_encrypted = Column(Text, nullable=True)
    # ============================================================

    # Status
    is_active = Column(Boolean, default=False)
    leads_target = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Soft-delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String, nullable=True)

    organization = relationship("Organization")


class LeadState(Base):
    __tablename__ = "lead_states"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=True)
    state = Column(String(50), default="new")
    is_paused = Column(Boolean, default=False)
    priority = Column(Integer, default=50)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    contact_count = Column(Integer, default=0)
    channels_used = Column(JSON, default=list)
    engagement_score = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    lead = relationship("Lead")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    sdr_profile_id = Column(String, nullable=True)
    action = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=True)
    reasoning = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead")
