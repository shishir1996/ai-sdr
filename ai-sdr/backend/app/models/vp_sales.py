import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class VPSalesProfile(Base):
    __tablename__ = "vp_sales_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, unique=True)

    name = Column(String(255), nullable=False, default="VP Sales AI")
    product_name = Column(Text, nullable=True)
    product_description = Column(Text, nullable=True)
    service_description = Column(Text, nullable=True)
    business_goals = Column(Text, nullable=True)
    icp_description = Column(Text, nullable=True)
    target_country = Column(String(255), nullable=True)
    target_audience = Column(String(500), nullable=True)
    sales_objectives = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")


class LeadSourceControl(Base):
    __tablename__ = "lead_source_controls"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, unique=True)

    google_search = Column(Boolean, default=True)
    bing_search = Column(Boolean, default=True)
    web_research = Column(Boolean, default=True)
    business_directories = Column(Boolean, default=True)
    company_websites = Column(Boolean, default=True)
    google_maps_scraping = Column(Boolean, default=False)
    apollo = Column(Boolean, default=False)
    lusha = Column(Boolean, default=False)
    rocketreach = Column(Boolean, default=False)
    zoominfo = Column(Boolean, default=False)
    linkedin_data = Column(Boolean, default=False)
    news_sites = Column(Boolean, default=True)
    startup_directories = Column(Boolean, default=True)
    industry_listings = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")


class ResearchAgent(Base):
    __tablename__ = "research_agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    vp_id = Column(String, ForeignKey("vp_sales_profiles.id"), nullable=True)

    name = Column(String(255), nullable=False)
    search_queries = Column(Text, nullable=True)
    target_industry = Column(String(255), nullable=True)
    target_country = Column(String(255), nullable=True)
    target_audience = Column(String(500), nullable=True)
    max_leads = Column(Integer, default=50)
    status = Column(String(50), default="idle")
    enabled_sources = Column(JSON, default=list)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    leads_discovered = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    vp_profile = relationship("VPSalesProfile")


class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    research_agent_id = Column(String, ForeignKey("research_agents.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    source = Column(String(100), nullable=False)
    source_url = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    company_name = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_title = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)
    industry = Column(String(255), nullable=True)
    business_type = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    raw_data = Column(JSON, nullable=True)

    status = Column(String(50), default="new")
    enriched = Column(Boolean, default=False)
    converted_to_lead = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")
    agent = relationship("ResearchAgent")
    lead = relationship("Lead")


class VPActionLog(Base):
    __tablename__ = "vp_action_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    vp_id = Column(String, ForeignKey("vp_sales_profiles.id"), nullable=True)

    action_type = Column(String(100), nullable=False)
    reasoning = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")
    vp_profile = relationship("VPSalesProfile")
