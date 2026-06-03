import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class CompanyIntelligence(Base):
    __tablename__ = "company_intelligence"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    research_result_id = Column(String, ForeignKey("research_results.id"), nullable=True)

    company_name = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    services = Column(Text, nullable=True)
    industry = Column(String(255), nullable=True)
    sub_industry = Column(String(255), nullable=True)
    company_size = Column(String(50), nullable=True)
    estimated_revenue = Column(String(50), nullable=True)
    technology_stack = Column(JSON, nullable=True)
    social_profiles = Column(JSON, nullable=True)
    location = Column(String(255), nullable=True)
    business_model = Column(String(100), nullable=True)
    founded_year = Column(String(10), nullable=True)

    source_url = Column(String(500), nullable=True)
    confidence = Column(Float, default=0.0)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    lead = relationship("Lead")


class DecisionMaker(Base):
    __tablename__ = "decision_makers"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    company_intelligence_id = Column(String, ForeignKey("company_intelligence.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    full_name = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    role_category = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=True)
    source_description = Column(Text, nullable=True)

    confidence = Column(Float, default=0.0)
    is_primary_decision_maker = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")
    company_intelligence = relationship("CompanyIntelligence")


class ContactDiscovery(Base):
    __tablename__ = "contact_discoveries"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    company_intelligence_id = Column(String, ForeignKey("company_intelligence.id"), nullable=True)

    contact_type = Column(String(50), nullable=False)
    value = Column(String(500), nullable=False)
    source = Column(String(100), nullable=True)
    confidence = Column(Float, default=0.0)
    verified = Column(Boolean, default=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    research_result_id = Column(String, ForeignKey("research_results.id"), nullable=True)

    validation_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    score = Column(Float, default=0.0)
    issues = Column(JSON, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")


class EnrichmentProfile(Base):
    __tablename__ = "enrichment_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    company_intelligence_id = Column(String, ForeignKey("company_intelligence.id"), nullable=True)

    industry = Column(String(255), nullable=True)
    sub_industry = Column(String(255), nullable=True)
    company_size = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    target_market = Column(Text, nullable=True)
    services = Column(Text, nullable=True)
    technology_stack = Column(JSON, nullable=True)
    business_model = Column(String(100), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    social_links = Column(JSON, nullable=True)

    enrichment_data = Column(JSON, nullable=True)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")


class BuyingSignal(Base):
    __tablename__ = "buying_signals"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    company_intelligence_id = Column(String, ForeignKey("company_intelligence.id"), nullable=True)

    signal_type = Column(String(100), nullable=False)
    signal_description = Column(Text, nullable=True)
    signal_source = Column(String(200), nullable=True)
    signal_url = Column(String(500), nullable=True)
    signal_date = Column(DateTime(timezone=True), nullable=True)
    signal_strength = Column(Float, default=0.0)
    intent_score = Column(Float, default=0.0)

    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True, unique=True)

    company_score = Column(Float, default=0.0)
    contact_score = Column(Float, default=0.0)
    icp_match_score = Column(Float, default=0.0)
    buying_signal_score = Column(Float, default=0.0)
    data_quality_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)

    scoring_breakdown = Column(JSON, nullable=True)
    scoring_version = Column(String(20), default="1.0")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    lead = relationship("Lead")


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    agent_type = Column(String(50), nullable=True)
    activity_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")
    lead = relationship("Lead")
