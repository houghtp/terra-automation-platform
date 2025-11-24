"""Pydantic schemas for Marketing Intelligence Hub (GA4 Phase 1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, constr


# Connections

class Ga4ConnectionCreate(BaseModel):
    property_id: constr(strip_whitespace=True, min_length=1, max_length=128)
    property_name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    client_name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    client_id: Optional[constr(strip_whitespace=True, max_length=36)] = None


class Ga4ConnectionUpdate(BaseModel):
    property_name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    client_name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    client_id: Optional[constr(strip_whitespace=True, max_length=36)] = None
    status: Optional[constr(strip_whitespace=True, max_length=32)] = None
    last_synced_at: Optional[datetime] = None


class Ga4ConnectionResponse(BaseModel):
    id: str
    tenant_id: str
    property_id: str
    property_name: Optional[str]
    client_name: Optional[str]
    client_id: Optional[str]
    status: str
    last_synced_at: Optional[datetime]

    class Config:
        orm_mode = True


# Metrics

class Ga4DailyMetricPayload(BaseModel):
    date: date
    sessions: Optional[float] = None
    users: Optional[float] = None
    pageviews: Optional[float] = None
    bounce_rate: Optional[float] = None
    engaged_sessions: Optional[float] = None
    conversions: Optional[float] = None
    engagement_rate: Optional[float] = None
    new_users: Optional[float] = None
    avg_engagement_time: Optional[float] = None
    conversion_rate: Optional[float] = None
    conversions_per_1k: Optional[float] = None
    channel_breakdown: Optional[Dict[str, Any]] = None
    device_breakdown: Optional[Dict[str, Any]] = None
    geo_breakdown: Optional[Dict[str, Any]] = None
    derived_changes: Optional[Dict[str, Any]] = None
    derived_moving_averages: Optional[Dict[str, Any]] = None


class Ga4DailyMetricResponse(Ga4DailyMetricPayload):
    id: str
    tenant_id: str
    connection_id: str

    class Config:
        orm_mode = True


class MetricsQueryRequest(BaseModel):
    start_date: date
    end_date: date
    compare_to_start: Optional[date] = None
    compare_to_end: Optional[date] = None


class MetricsKpiResponse(BaseModel):
    sessions: Optional[float]
    users: Optional[float]
    conversions: Optional[float]
    engagement_rate: Optional[float]
    bounce_rate: Optional[float]
    new_users: Optional[float] = None
    avg_engagement_time: Optional[float] = None
    conversion_rate: Optional[float] = None
    conversions_per_1k: Optional[float] = None
    deltas: Dict[str, Any] = Field(default_factory=dict)
    last_synced_at: Optional[datetime] = None
    available_start: Optional[date] = None
    available_end: Optional[date] = None


class MetricsTimeSeriesPoint(BaseModel):
    date: date
    sessions: Optional[float]
    users: Optional[float]
    conversions: Optional[float]
    engagement_rate: Optional[float]
    bounce_rate: Optional[float] = None
    new_users: Optional[float] = None
    avg_engagement_time: Optional[float] = None
    conversion_rate: Optional[float] = None
    conversions_per_1k: Optional[float] = None


class MetricsTimeSeriesResponse(BaseModel):
    points: List[MetricsTimeSeriesPoint]


# Insights

class Ga4InsightCreate(BaseModel):
    period: constr(strip_whitespace=True, max_length=32)
    summary_type: constr(strip_whitespace=True, max_length=32)
    content: constr(strip_whitespace=True, min_length=1)
    source: constr(strip_whitespace=True, max_length=32) = "ai"


class Ga4InsightResponse(BaseModel):
    id: str
    tenant_id: str
    connection_id: str
    period: str
    summary_type: str
    content: str
    source: str
    generated_at: datetime

    class Config:
        orm_mode = True


# Reports

class Ga4ReportCreate(BaseModel):
    period: constr(strip_whitespace=True, max_length=32)
    report_type: constr(strip_whitespace=True, max_length=32) = "weekly"
    html_url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    pdf_url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    status: constr(strip_whitespace=True, max_length=32) = "draft"


class Ga4ReportResponse(BaseModel):
    id: str
    tenant_id: str
    connection_id: str
    period: str
    report_type: str
    html_url: Optional[str]
    pdf_url: Optional[str]
    status: str
    sent_at: Optional[datetime]

    class Config:
        orm_mode = True
