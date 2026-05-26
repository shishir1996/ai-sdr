import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="campaigns")
    steps = relationship("CampaignStep", back_populates="campaign", order_by="CampaignStep.step_order")


class CampaignStep(Base):
    __tablename__ = "campaign_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    channel = Column(String(50), nullable=False)
    template_id = Column(String, ForeignKey("email_templates.id"), nullable=True)
    call_script_id = Column(String, ForeignKey("call_scripts.id"), nullable=True)
    delay_days = Column(Integer, default=0)
    conditions = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    campaign = relationship("Campaign", back_populates="steps")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    template_id = Column(String, ForeignKey("email_templates.id"), nullable=True)
    from_email = Column(String(255), nullable=False)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    direction = Column(String(20), default="outbound")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    message_id = Column(String(255), nullable=True)
    in_reply_to = Column(String(255), nullable=True)
    references = Column(Text, nullable=True)
    thread_id = Column(String(255), nullable=True)
    rfc_message_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead", back_populates="email_messages")


class CallScript(Base):
    __tablename__ = "call_scripts"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    script_id = Column(String, ForeignKey("call_scripts.id"), nullable=True)
    status = Column(String(50), default="scheduled")
    duration_seconds = Column(Integer, nullable=True)
    recording_url = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    outcome = Column(String(50), nullable=True)
    called_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead", back_populates="call_logs")
