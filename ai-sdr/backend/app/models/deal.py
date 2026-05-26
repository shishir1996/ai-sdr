import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="pipelines")
    stages = relationship("DealStage", back_populates="pipeline", order_by="DealStage.stage_order")


class DealStage(Base):
    __tablename__ = "deal_stages"

    id = Column(String, primary_key=True, default=generate_uuid)
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=False)
    name = Column(String(255), nullable=False)
    stage_order = Column(Integer, nullable=False)
    probability = Column(Integer, default=0)
    color = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    pipeline = relationship("Pipeline", back_populates="stages")
    deals = relationship("Deal", back_populates="stage")


class Deal(Base):
    __tablename__ = "deals"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    stage_id = Column(String, ForeignKey("deal_stages.id"), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="open")
    source = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    won_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="deals")
    lead = relationship("Lead", back_populates="deals")
    stage = relationship("DealStage", back_populates="deals")
