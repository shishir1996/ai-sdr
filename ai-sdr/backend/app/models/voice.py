import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class VoiceAgent(Base):
    __tablename__ = "voice_agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=True)
    name = Column(String(255), nullable=False)
    vapi_assistant_id = Column(String(255), nullable=True, unique=True)
    ai_model = Column(String(100), default="gpt-4o-mini")
    voice_provider = Column(String(100), default="11labs")
    voice_id = Column(String(100), default="default")
    transcriber_provider = Column(String(100), default="deepgram")
    system_prompt = Column(Text, nullable=True)
    first_message = Column(String(500), nullable=True)
    temperature = Column(Float, default=0.7)
    max_duration_seconds = Column(Integer, default=300)
    is_active = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")


class CallCampaign(Base):
    __tablename__ = "call_campaigns"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    sdr_profile_id = Column(String, nullable=True)
    voice_agent_id = Column(String, ForeignKey("voice_agents.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    schedule_start = Column(DateTime(timezone=True), nullable=True)
    schedule_end = Column(DateTime(timezone=True), nullable=True)
    timezone_restrictions = Column(JSON, nullable=True)
    business_hours_start = Column(String(10), default="09:00")
    business_hours_end = Column(String(10), default="18:00")
    business_days = Column(JSON, default=list)
    max_concurrent_calls = Column(Integer, default=3)
    max_calls_per_day = Column(Integer, default=50)
    retry_on_no_answer = Column(Boolean, default=True)
    max_retries = Column(Integer, default=2)
    retry_delay_minutes = Column(Integer, default=30)
    voicemail_detection = Column(Boolean, default=True)
    voicemail_action = Column(String(50), default="leave_message")
    call_timeout_seconds = Column(Integer, default=60)
    lead_filter_criteria = Column(JSON, nullable=True)
    total_calls = Column(Integer, default=0)
    total_connected = Column(Integer, default=0)
    total_positive = Column(Integer, default=0)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    voice_agent = relationship("VoiceAgent")


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    campaign_id = Column(String, ForeignKey("call_campaigns.id"), nullable=True)
    voice_agent_id = Column(String, ForeignKey("voice_agents.id"), nullable=True)
    sdr_profile_id = Column(String, nullable=True)
    vapi_call_id = Column(String(255), nullable=True, unique=True)
    phone_number = Column(String(50), nullable=False)
    direction = Column(String(20), default="outbound")
    status = Column(String(50), default="queued")
    duration_seconds = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    outcome = Column(String(50), nullable=True)
    sentiment = Column(String(50), nullable=True)
    lead_qualified = Column(Boolean, nullable=True)
    lead_intent = Column(String(100), nullable=True)
    ai_summary = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    transcript_url = Column(String(500), nullable=True)
    recording_url = Column(String(500), nullable=True)
    recording_duration = Column(Integer, nullable=True)
    voicemail_detected = Column(Boolean, nullable=True)
    answered_by = Column(String(50), nullable=True)
    next_action = Column(String(100), nullable=True)
    followup_scheduled = Column(Boolean, default=False)
    followup_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    called_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    lead = relationship("Lead")
    campaign = relationship("CallCampaign")
    voice_agent = relationship("VoiceAgent")


class CallQueue(Base):
    __tablename__ = "call_queue"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    campaign_id = Column(String, ForeignKey("call_campaigns.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    voice_agent_id = Column(String, ForeignKey("voice_agents.id"), nullable=True)
    phone_number = Column(String(50), nullable=False)
    priority = Column(Integer, default=50)
    status = Column(String(50), default="pending")
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
    last_error = Column(Text, nullable=True)
    idempotency_key = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    lead = relationship("Lead")
    campaign = relationship("CallCampaign")


class CallAnalytics(Base):
    __tablename__ = "call_analytics"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    date = Column(String(10), nullable=False)
    total_calls = Column(Integer, default=0)
    connected_calls = Column(Integer, default=0)
    voicemail_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    no_answer_calls = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    positive_outcomes = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)
    qualified_leads = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")


class AiSummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    call_record_id = Column(String, ForeignKey("call_records.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    summary = Column(Text, nullable=False)
    transcript_summary = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True)
    action_items = Column(JSON, nullable=True)
    next_steps = Column(Text, nullable=True)
    sentiment_analysis = Column(JSON, nullable=True)
    qualification_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")
