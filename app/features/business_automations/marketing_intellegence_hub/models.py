"""Models for the Marketing Intelligence Hub (GA4 Phase 1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, String, Text, Date, DateTime, Boolean, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class Ga4Connection(Base, AuditMixin):
    __tablename__ = "ga4_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    client_id = Column(String(36), ForeignKey("ga4_clients.id", ondelete="SET NULL"), nullable=True, index=True)
    property_id = Column(String(128), nullable=False)
    property_name = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    last_synced_at = Column(DateTime, nullable=True)

    tokens = relationship("Ga4Token", back_populates="connection", cascade="all, delete-orphan", uselist=False)
    metrics = relationship("Ga4DailyMetric", back_populates="connection", cascade="all, delete-orphan")
    client = relationship("Ga4Client", back_populates="connections")

    __table_args__ = (
        Index("ix_ga4_connections_tenant_property", "tenant_id", "property_id", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "property_id": self.property_id,
            "property_name": self.property_name,
            "client_name": self.client_name,
            "status": self.status,
            "last_synced_at": self.last_synced_at,
        }
        data.update(self.get_audit_info())
        return data


class Ga4Token(Base):
    __tablename__ = "ga4_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_id = Column(String(36), ForeignKey("ga4_connections.id", ondelete="CASCADE"), nullable=False)
    encrypted_refresh_token = Column(Text, nullable=False)
    encrypted_access_token = Column(Text, nullable=True)
    access_token_expires_at = Column(DateTime, nullable=True)

    connection = relationship("Ga4Connection", back_populates="tokens")


class Ga4DailyMetric(Base, AuditMixin):
    __tablename__ = "ga4_daily_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    connection_id = Column(String(36), ForeignKey("ga4_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)

    sessions = Column(Numeric(18, 2), nullable=True)
    users = Column(Numeric(18, 2), nullable=True)
    pageviews = Column(Numeric(18, 2), nullable=True)
    bounce_rate = Column(Numeric(5, 2), nullable=True)
    engaged_sessions = Column(Numeric(18, 2), nullable=True)
    conversions = Column(Numeric(18, 2), nullable=True)
    engagement_rate = Column(Numeric(5, 2), nullable=True)

    new_users = Column(Numeric(18, 2), nullable=True)
    avg_engagement_time = Column(Numeric(18, 2), nullable=True)  # seconds
    conversion_rate = Column(Numeric(7, 4), nullable=True)  # 0-1 fraction
    conversions_per_1k = Column(Numeric(18, 4), nullable=True)

    channel_breakdown = Column(JSONB, nullable=True)
    device_breakdown = Column(JSONB, nullable=True)
    geo_breakdown = Column(JSONB, nullable=True)

    derived_changes = Column(JSONB, nullable=True)
    derived_moving_averages = Column(JSONB, nullable=True)

    connection = relationship("Ga4Connection", back_populates="metrics")

    __table_args__ = (
        Index("ix_ga4_daily_metrics_unique", "tenant_id", "connection_id", "date", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "connection_id": self.connection_id,
            "date": self.date,
            "sessions": float(self.sessions) if self.sessions is not None else None,
            "users": float(self.users) if self.users is not None else None,
            "pageviews": float(self.pageviews) if self.pageviews is not None else None,
            "bounce_rate": float(self.bounce_rate) if self.bounce_rate is not None else None,
            "engaged_sessions": float(self.engaged_sessions) if self.engaged_sessions is not None else None,
            "conversions": float(self.conversions) if self.conversions is not None else None,
            "engagement_rate": float(self.engagement_rate) if self.engagement_rate is not None else None,
            "new_users": float(self.new_users) if self.new_users is not None else None,
            "avg_engagement_time": float(self.avg_engagement_time) if self.avg_engagement_time is not None else None,
            "conversion_rate": float(self.conversion_rate) if self.conversion_rate is not None else None,
            "conversions_per_1k": float(self.conversions_per_1k) if self.conversions_per_1k is not None else None,
            "channel_breakdown": self.channel_breakdown,
            "device_breakdown": self.device_breakdown,
            "geo_breakdown": self.geo_breakdown,
            "derived_changes": self.derived_changes,
            "derived_moving_averages": self.derived_moving_averages,
        }
        data.update(self.get_audit_info())
        return data


class Ga4Insight(Base, AuditMixin):
    __tablename__ = "ga4_insights"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    connection_id = Column(String(36), ForeignKey("ga4_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(String(32), nullable=False)  # e.g., weekly, monthly
    summary_type = Column(String(32), nullable=False)  # exec, analyst
    content = Column(Text, nullable=False)
    source = Column(String(32), nullable=False, default="ai")
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    connection = relationship("Ga4Connection")


class Ga4Report(Base, AuditMixin):
    __tablename__ = "ga4_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    connection_id = Column(String(36), ForeignKey("ga4_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(String(32), nullable=False)  # weekly, monthly, test
    report_type = Column(String(32), nullable=False, default="weekly")
    html_url = Column(String(500), nullable=True)
    pdf_url = Column(String(500), nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    sent_at = Column(DateTime, nullable=True)

    connection = relationship("Ga4Connection")

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "connection_id": self.connection_id,
            "period": self.period,
            "report_type": self.report_type,
            "html_url": self.html_url,
            "pdf_url": self.pdf_url,
            "status": self.status,
            "sent_at": self.sent_at,
        }
        data.update(self.get_audit_info())
        return data
class Ga4Client(Base):
    __tablename__ = "ga4_clients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=True, onupdate=datetime.utcnow)

    connections = relationship("Ga4Connection", back_populates="client", cascade="all, delete-orphan")
