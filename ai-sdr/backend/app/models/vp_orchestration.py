import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class Mission(Base):
    __tablename__ = "missions"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    vp_id = Column(String, ForeignKey("vp_sales_profiles.id"), nullable=True)
    name = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    kpi_target = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    vp_reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
    tasks = relationship("MissionTask", back_populates="mission", order_by="MissionTask.created_at")


class MissionTask(Base):
    __tablename__ = "mission_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)
    agent_id = Column(String, nullable=True)

    objective = Column(Text, nullable=False)
    execution_plan = Column(JSON, nullable=True)
    status = Column(String(50), default="pending")

    report = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    vp_feedback = Column(String(50), nullable=True)
    vp_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    mission = relationship("Mission", back_populates="tasks")


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)
    agent_id = Column(String, nullable=True)
    memory_type = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization")


class AgentPerformance(Base):
    __tablename__ = "agent_performance"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)
    agent_id = Column(String, nullable=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, default=0)
    period = Column(String(50), default="all_time")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization")
