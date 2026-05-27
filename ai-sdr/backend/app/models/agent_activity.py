import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


ACTIVITY_STAGES = [
    "leads_analyzed",
    "icp_identified",
    "campaign_strategy_created",
    "outreach_sequence_planned",
    "email_drafted",
    "linkedin_invite_generated",
    "followup_scheduled",
    "ai_call_planned",
    "followup_email_triggered",
    "reply_detected",
    "next_action_decided",
    "campaign_optimized",
    "lead_researched",
    "lead_analyzed",
    "message_sent",
    "call_made",
    "meeting_booked",
    "payment_sent",
    "lead_won",
    "lead_lost",
]

SDR_STATUSES = [
    "thinking",
    "researching",
    "drafting",
    "waiting_for_response",
    "sending_followup",
    "optimizing_campaign",
    "idle",
    "paused",
    "analyzing",
    "planning",
    "personalizing",
    "executing",
]


class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=True, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True, index=True)
    campaign_id = Column(String, nullable=True, index=True)

    stage = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="completed")
    summary = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    channel = Column(String(50), nullable=True)
    next_planned_action = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    is_expandable = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead")


class SDRReasoningLog(Base):
    __tablename__ = "sdr_reasoning_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=True, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    decision_type = Column(String(100), nullable=False)
    human_readable_reasoning = Column(Text, nullable=True)
    detailed_reasoning = Column(JSON, nullable=True)
    ai_confidence_score = Column(Integer, nullable=True)
    alternatives_considered = Column(JSON, nullable=True)

    context_summary = Column(Text, nullable=True)
    channel_selected = Column(String(50), nullable=True)
    timing_explanation = Column(Text, nullable=True)
    personalization_strategy = Column(Text, nullable=True)
    industry_context = Column(Text, nullable=True)
    country_context = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead")


class CampaignEvent(Base):
    __tablename__ = "campaign_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    campaign_id = Column(String, nullable=False, index=True)
    sdr_profile_id = Column(String, nullable=True)

    event_type = Column(String(100), nullable=False)
    summary = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    progress_before = Column(Integer, nullable=True)
    progress_after = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)


class LeadTimeline(Base):
    __tablename__ = "lead_timeline"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    sdr_profile_id = Column(String, nullable=True)

    event_type = Column(String(100), nullable=False)
    summary = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    message_preview = Column(Text, nullable=True)
    channel = Column(String(50), nullable=True)
    response_received = Column(Text, nullable=True)

    sdr_status_before = Column(String(50), nullable=True)
    sdr_status_after = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead")


class SequenceExecutionLog(Base):
    __tablename__ = "sequence_execution_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    campaign_id = Column(String, nullable=False, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    sdr_profile_id = Column(String, nullable=True)

    step_order = Column(Integer, nullable=False)
    channel = Column(String(50), nullable=False)
    delay_days = Column(Integer, default=0)

    status = Column(String(50), default="pending")
    executed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead")


class SDRStatus(Base):
    __tablename__ = "sdr_status"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=False, index=True)

    current_status = Column(String(50), default="idle")
    current_action = Column(String(200), nullable=True)
    current_lead_id = Column(String, nullable=True)
    current_campaign_id = Column(String, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    next_planned_action = Column(Text, nullable=True)

    heartbeat_at = Column(DateTime(timezone=True), default=utcnow)
    last_active_at = Column(DateTime(timezone=True), default=utcnow)

    leads_processed = Column(Integer, default=0)
    campaigns_created = Column(Integer, default=0)
    emails_drafted = Column(Integer, default=0)
    linkedin_invites_sent = Column(Integer, default=0)
    replies_detected = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
