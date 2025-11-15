"""
CSPM (Cloud Security Posture Management) Pydantic Schemas

Request and response schemas for M365 compliance scanning.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# M365 Tenant Schemas
# ============================================================================

class M365TenantCreate(BaseModel):
    """Schema for creating M365 tenant."""

    m365_tenant_id: str = Field(..., min_length=1, max_length=100, description="M365 Tenant ID (GUID)")
    m365_tenant_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional display name. When omitted, the assigned platform tenant name is used."
    )
    m365_domain: Optional[str] = Field(None, max_length=255, description="Primary domain (e.g., contoso.onmicrosoft.com)")
    description: Optional[str] = Field(None, description="Description of the tenant")

    # Credentials (stored separately in tenant_secrets)
    client_id: Optional[str] = Field(None, description="M365 App Registration Client ID")
    client_secret: Optional[str] = Field(None, description="M365 App Registration Client Secret")
    certificate_thumbprint: Optional[str] = Field(None, description="Certificate thumbprint for cert-based auth")
    certificate_pfx: Optional[str] = Field(None, description="Certificate PFX file (base64 encoded)")
    certificate_password: Optional[str] = Field(None, description="Certificate PFX password")
    username: Optional[str] = Field(None, description="Username for username/password auth")
    password: Optional[str] = Field(None, description="Password for username/password auth")

    model_config = {
        "json_schema_extra": {
            "example": {
                "m365_tenant_id": "660636d5-cb4e-4816-b1b8-f5afc446f583",
                "m365_domain": "contoso.onmicrosoft.com",
                "description": "Production M365 tenant",
                "client_id": "12345678-1234-1234-1234-123456789012",
                "client_secret": "your-client-secret-here"
            }
        }
    }


class M365TenantCreateRequest(M365TenantCreate):
    """Extended create schema allowing global admins to assign target tenant."""

    target_tenant_id: Optional[str] = Field(
        None,
        description="Target platform tenant ID (global admin only)"
    )


class M365TenantUpdate(BaseModel):
    """Schema for updating M365 tenant."""

    m365_domain: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|error)$")

    # Optional credential updates
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    certificate_thumbprint: Optional[str] = None
    certificate_pfx: Optional[str] = None
    certificate_password: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class M365TenantResponse(BaseModel):
    """Schema for M365 tenant response."""

    id: str
    tenant_id: str
    tenant_benchmark_id: str
    tenant_benchmark_display_name: Optional[str] = None
    tenant_benchmark_status: Optional[str] = None
    tech_type: Optional[str] = None
    benchmark_id: Optional[str] = None
    benchmark_display_name: Optional[str] = None
    benchmark_key: Optional[str] = None
    m365_tenant_id: str
    m365_tenant_name: str
    m365_domain: Optional[str]
    description: Optional[str]
    status: str
    last_test_at: Optional[datetime]
    last_test_status: Optional[str]
    last_test_error: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    updated_by_email: Optional[str]
    updated_by_name: Optional[str]
    deleted_at: Optional[datetime] = None
    deleted_by_email: Optional[str] = None
    deleted_by_name: Optional[str] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class M365TenantCredentials(BaseModel):
    """Schema for viewing M365 tenant credentials (masked)."""

    has_client_secret: bool
    has_certificate: bool
    has_username_password: bool
    client_id: Optional[str]
    certificate_thumbprint: Optional[str]
    username: Optional[str]


class TestConnectionRequest(BaseModel):
    """Schema for testing M365 connection."""

    test_type: Optional[str] = Field("basic", pattern="^(basic|full)$", description="Basic or full connection test")


class TestConnectionResponse(BaseModel):
    """Schema for test connection result."""

    success: bool
    message: str
    error: Optional[str] = None
    tested_at: datetime
    modules_available: Optional[List[str]] = None


# ============================================================================
# Compliance Scan Schemas
# ============================================================================

class ComplianceScanRequest(BaseModel):
    """Schema for starting a compliance scan."""

    m365_tenant_id: str = Field(..., description="ID of M365 tenant to scan")
    tenant_benchmark_id: Optional[str] = Field(None, description="Tenant benchmark assignment identifier")
    l1_only: bool = Field(False, description="Run only Level 1 checks")
    check_ids: Optional[List[str]] = Field(None, description="Filter to specific check IDs (optional)")
    output_format: str = Field("json", pattern="^(json|csv)$", description="Output format")
    tech_type: str = Field("M365", description="Technology type associated with the benchmark (e.g., M365, Azure)")
    benchmark_id: Optional[str] = Field(None, description="Benchmark identifier to associate with the scan")
    benchmark_key: Optional[str] = Field(None, description="Benchmark key (e.g., cis_microsoft_365_foundations_v5_0_0)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "m365_tenant_id": "660636d5-cb4e-4816-b1b8-f5afc446f583",
                "l1_only": False,
                "check_ids": None,
                "output_format": "json",
                "tech_type": "M365",
                "benchmark_id": "cis-m365-v5-0-0"
            }
        }
    }


class ComplianceScanResponse(BaseModel):
    """Schema for scan response."""

    id: int
    scan_id: str
    tenant_id: str
    tenant_benchmark_id: str
    assignment_display_name: Optional[str] = None
    tech_type: str
    scan_options: Dict[str, Any]
    benchmark_id: str
    benchmark_key: Optional[str]
    benchmark_display_name: Optional[str] = None
    target_identifier: Optional[str] = None
    target_display_name: Optional[str] = None
    m365_tenant_id: Optional[str] = None
    status: str
    progress_percentage: int
    current_check: Optional[str]
    total_checks: int
    passed: int
    failed: int
    errors: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    celery_task_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    updated_by_email: Optional[str]
    updated_by_name: Optional[str]
    tenant_display_name: Optional[str] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class ScanProgressUpdate(BaseModel):
    """Schema for scan progress updates from PowerShell webhook."""

    scan_id: str
    progress_percentage: int = Field(..., ge=0, le=100)
    current_check: Optional[str] = None
    status: Optional[str] = None  # Pass, Fail, Error
    total_checks: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    errors: Optional[int] = None


class ScanStatusResponse(BaseModel):
    """Schema for scan status query response."""

    scan_id: str
    status: str
    progress_percentage: int
    current_check: Optional[str]
    total_checks: int
    passed: int
    failed: int
    errors: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    tenant_benchmark_id: Optional[str] = None
    assignment_display_name: Optional[str] = None
    tech_type: Optional[str] = None
    benchmark_id: Optional[str] = None
    benchmark_key: Optional[str] = None
    benchmark_display_name: Optional[str] = None
    target_identifier: Optional[str] = None
    target_display_name: Optional[str] = None
    m365_tenant_id: Optional[str] = None


# ============================================================================
# Compliance Result Schemas
# ============================================================================

class ComplianceResultResponse(BaseModel):
    """Schema for individual compliance result."""

    id: int
    tenant_id: str
    m365_tenant_id: Optional[str] = None
    scan_id: str
    tenant_benchmark_id: str
    assignment_display_name: Optional[str] = None
    tech_type: str
    benchmark_id: str
    benchmark_key: Optional[str]
    benchmark_display_name: Optional[str] = None
    target_identifier: Optional[str] = None
    check_id: str
    category: Optional[str]
    status: str
    status_id: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: Optional[int]
    details: List[Dict[str, Any]]
    error: Optional[str]

    # CIS Metadata fields
    title: Optional[str] = None
    level: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    recommendation_id: Optional[str] = None
    profile_applicability: Optional[str] = None
    description: Optional[str] = None
    rationale: Optional[str] = None
    impact: Optional[str] = None
    remediation: Optional[str] = None
    audit_procedure: Optional[str] = None
    default_value: Optional[str] = None
    references: Optional[Any] = None  # Can be list or dict from JSON
    cis_controls: Optional[Any] = None  # Can be list or dict from JSON
    metadata_raw: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime]
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    updated_by_email: Optional[str]
    updated_by_name: Optional[str]

    model_config = {"from_attributes": True}


class CSPMBenchmarkResponse(BaseModel):
    """Schema for benchmark metadata."""

    id: str
    tech_type: str
    benchmark_key: str
    version: Optional[str]
    display_name: str
    description: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_json", serialization_alias="metadata")
    created_at: datetime
    updated_at: Optional[datetime]
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    updated_by_email: Optional[str]
    updated_by_name: Optional[str]

    model_config = {"from_attributes": True, "populate_by_name": True}


class CSPMTenantBenchmarkCreate(BaseModel):
    """Schema for assigning a benchmark to a tenant."""

    benchmark_id: str = Field(..., description="Benchmark identifier")
    display_name: Optional[str] = Field(None, max_length=255, description="Custom display name for the assignment")
    status: Optional[str] = Field("active", pattern="^(active|inactive)$", description="Assignment status")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Technology-specific configuration")
    target_tenant_id: Optional[str] = Field(
        None,
        description="Platform tenant to assign the benchmark to (global admin only)"
    )


class CSPMTenantBenchmarkUpdate(BaseModel):
    """Schema for updating a tenant benchmark assignment."""

    display_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    config: Optional[Dict[str, Any]] = None


class CSPMTenantBenchmarkResponse(BaseModel):
    """Schema for tenant benchmark assignments."""

    id: str
    tenant_id: str
    benchmark_id: str
    tech_type: str
    display_name: str
    status: str
    config: Optional[Dict[str, Any]] = Field(default=None, alias="config_json", serialization_alias="config")
    created_at: datetime
    updated_at: Optional[datetime]
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    updated_by_email: Optional[str]
    updated_by_name: Optional[str]
    benchmark: Optional[CSPMBenchmarkResponse] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class ComplianceResultsListResponse(BaseModel):
    """Schema for list of compliance results."""

    total: int
    results: List[ComplianceResultResponse]


class ComplianceSummaryResponse(BaseModel):
    """Schema for compliance summary statistics."""

    scan_id: str
    m365_tenant_id: str
    total_checks: int
    passed: int
    failed: int
    errors: int
    pass_percentage: float
    l1_passed: int
    l1_failed: int
    l2_passed: int
    l2_failed: int
    completed_at: Optional[datetime]


# ============================================================================
# Utility Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
