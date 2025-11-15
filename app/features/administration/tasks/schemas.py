"""
Pydantic schemas for the administration tasks API.
"""
from typing import List

from pydantic import BaseModel, Field


class EmailTaskRequest(BaseModel):
    user_email: str
    user_name: str


class BulkEmailRequest(BaseModel):
    recipient_emails: List[str] = Field(..., min_length=1)
    subject: str
    message: str


class DataExportRequest(BaseModel):
    user_id: int
    export_format: str = "csv"


class AuditReportRequest(BaseModel):
    tenant_id: str
    start_date: str
    end_date: str


__all__ = [
    "AuditReportRequest",
    "BulkEmailRequest",
    "DataExportRequest",
    "EmailTaskRequest",
]
