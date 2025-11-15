"""
CSPM (Cloud Security Posture Management) Models

Stores M365 tenant information, compliance scan runs, and individual check results.
"""

from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin
from sqlalchemy.orm import relationship


class CSPMBenchmark(Base, AuditMixin):
    """
    Compliance benchmark definition (e.g., CIS Microsoft 365 Foundations v5.0.0).
    """

    __tablename__ = "cspm_benchmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tech_type = Column(String(50), nullable=False)
    benchmark_key = Column(String(100), nullable=False)
    version = Column(String(50), nullable=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, default=dict)

    __table_args__ = (
        Index('idx_cspm_benchmarks_tech', 'tech_type'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tech_type": self.tech_type,
            "benchmark_key": self.benchmark_key,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "metadata": self.metadata_json or {},
            **self.get_audit_info()
        }


class CSPMTenantBenchmark(Base, AuditMixin):
    """Assignment of a benchmark to a specific platform tenant."""

    __tablename__ = "cspm_tenant_benchmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    benchmark_id = Column(String(36), ForeignKey("cspm_benchmarks.id", ondelete="CASCADE"), nullable=False, index=True)
    tech_type = Column(String(50), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    status = Column(String(50), default="active", nullable=False)
    config_json = Column("config", JSON, default=dict)

    benchmark = relationship("CSPMBenchmark", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "benchmark_id": self.benchmark_id,
            "tech_type": self.tech_type,
            "display_name": self.display_name,
            "status": self.status,
            "config": self.config_json or {},
            "benchmark": self.benchmark.to_dict() if self.benchmark else None,
            **self.get_audit_info()
        }


class M365Tenant(Base, AuditMixin):
    """
    Microsoft 365 tenant configuration.

    Stores M365 tenant details linked to platform tenants.
    Each platform tenant can have multiple M365 tenants to assess.
    """

    __tablename__ = "m365_tenants"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Platform tenant association (multi-tenant isolation)
    tenant_id = Column(String(64), nullable=False, index=True)
    tenant_benchmark_id = Column(String(36), ForeignKey("cspm_tenant_benchmarks.id"), nullable=False, index=True)

    # M365 tenant details
    m365_tenant_id = Column(String(100), nullable=False, index=True)
    m365_tenant_name = Column(String(255), nullable=False)
    m365_domain = Column(String(255), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, inactive, error

    # Last connection test
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(50), nullable=True)  # success, failed
    last_test_error = Column(Text, nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by_email, created_by_name, updated_by_email, updated_by_name

    __table_args__ = (
        Index('idx_m365_tenants_tenant_m365', 'tenant_id', 'm365_tenant_id'),
        Index('idx_m365_tenants_status', 'tenant_id', 'status'),
    )

    tenant_benchmark = relationship("CSPMTenantBenchmark", lazy="joined")

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "tenant_benchmark_id": self.tenant_benchmark_id,
            "m365_tenant_id": self.m365_tenant_id,
            "m365_tenant_name": self.m365_tenant_name,
            "m365_domain": self.m365_domain,
            "description": self.description,
            "status": self.status,
            "last_test_at": self.last_test_at.isoformat() if self.last_test_at else None,
            "last_test_status": self.last_test_status,
            "last_test_error": self.last_test_error,
            **self.get_audit_info()
        }


class CSPMComplianceScan(Base, AuditMixin):
    """
    Compliance scan job tracking.

    Tracks individual compliance scan runs, including progress, status, and summary metrics.
    """

    __tablename__ = "cspm_compliance_scans"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Unique scan identifier (used for grouping results)
    scan_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # Platform tenant association
    tenant_id = Column(String(64), nullable=False, index=True)
    tenant_benchmark_id = Column(String(36), ForeignKey("cspm_tenant_benchmarks.id"), nullable=False, index=True)

    # M365 tenant being scanned
    m365_tenant_id = Column(String(100), nullable=False, index=True)

    # Scan configuration
    tech_type = Column(String(50), default="M365", nullable=False)  # M365, Azure, AWS, etc.
    scan_options = Column(JSON, default=dict)  # {L1Only: true, CheckIds: [...], etc.}
    benchmark_id = Column(String(36), ForeignKey("cspm_benchmarks.id"), nullable=False)
    benchmark_key = Column(String(100), nullable=True)

    # Scan status
    status = Column(String(50), default="pending", nullable=False, index=True)
    # Status values: pending, running, completed, failed, cancelled

    # Progress tracking
    progress_percentage = Column(Integer, default=0, nullable=False)  # 0-100
    current_check = Column(String(255), nullable=True)  # Currently running check ID

    # Summary metrics
    total_checks = Column(Integer, default=0, nullable=False)
    passed = Column(Integer, default=0, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    errors = Column(Integer, default=0, nullable=False)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Background task tracking
    celery_task_id = Column(String(255), nullable=True, index=True)

    # Error information
    error_message = Column(Text, nullable=True)

    # AuditMixin provides: created_at, updated_at, created_by_email, created_by_name, updated_by_email, updated_by_name

    __table_args__ = (
        Index('idx_cspm_scans_tenant_status', 'tenant_id', 'status'),
        Index('idx_cspm_scans_m365_tenant', 'tenant_id', 'm365_tenant_id'),
        Index('idx_cspm_scans_created', 'tenant_id', 'created_at'),
    )

    benchmark = relationship("CSPMBenchmark", lazy="joined")
    tenant_benchmark = relationship("CSPMTenantBenchmark", lazy="joined")

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            "id": self.id,
            "scan_id": self.scan_id,
            "tenant_id": self.tenant_id,
            "tenant_benchmark_id": self.tenant_benchmark_id,
            "m365_tenant_id": self.m365_tenant_id,
            "tech_type": self.tech_type,
            "scan_options": self.scan_options,
            "benchmark_id": self.benchmark_id,
            "benchmark_key": self.benchmark_key,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "current_check": self.current_check,
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "celery_task_id": self.celery_task_id,
            "error_message": self.error_message,
            **self.get_audit_info()
        }


class CSPMComplianceResult(Base, AuditMixin):
    """
    Individual compliance check result.

    Stores one row per check execution with detailed results.
    """

    __tablename__ = "cspm_compliance_results"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Platform tenant association
    tenant_id = Column(String(64), nullable=False, index=True)

    # M365 tenant that was scanned
    m365_tenant_id = Column(String(100), nullable=False, index=True)

    # Link to parent scan
    scan_id = Column(String(36), nullable=False, index=True)
    tenant_benchmark_id = Column(String(36), ForeignKey("cspm_tenant_benchmarks.id"), nullable=False, index=True)

    # Check identification
    tech_type = Column(String(50), default="M365", nullable=False)
    benchmark_id = Column(String(36), ForeignKey("cspm_benchmarks.id"), nullable=False)
    benchmark_key = Column(String(100), nullable=True)
    check_id = Column(String(255), nullable=False, index=True)
    category = Column(String(50), nullable=True, index=True)  # L1, L2, etc.

    # Check result
    status = Column(String(50), nullable=False, index=True)  # Pass, Fail, Error
    status_id = Column(Integer, nullable=True)  # 1=Pass, 3=Fail/Error

    # Timing information
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds

    # Detailed results (JSONB for flexible querying)
    details = Column(JSON, default=list)
    # Format: [{"ResourceName": "...", "Property": "...", "IsCompliant": true/false, ...}]

    # Error information
    error = Column(Text, nullable=True)

    # CIS Metadata columns (from PowerShell check metadata)
    title = Column(String(500), nullable=True)
    level = Column(String(10), nullable=True, index=True)  # L1, L2 - indexed for filtering
    section = Column(String(100), nullable=True, index=True)  # Major section - indexed for grouping
    subsection = Column(String(200), nullable=True, index=True)  # Subsection - indexed for grouping
    recommendation_id = Column(String(20), nullable=True, index=True)  # CIS ID (e.g., "8.5.6") - indexed for lookups
    profile_applicability = Column(Text, nullable=True)  # License requirements (E3, E5, etc.)
    description = Column(Text, nullable=True)  # What the check does
    rationale = Column(Text, nullable=True)  # Why it matters
    impact = Column(Text, nullable=True)  # Effect of remediation
    remediation = Column(Text, nullable=True)  # How to fix
    audit_procedure = Column(Text, nullable=True)  # Manual audit steps
    default_value = Column(String(200), nullable=True)  # Microsoft's default setting
    references = Column(JSON, nullable=True)  # Documentation links (array)
    cis_controls = Column(JSON, nullable=True)  # CIS Controls v7/v8 mappings
    metadata_raw = Column(JSON, nullable=True)  # Full metadata object for future use

    # AuditMixin provides: created_at, updated_at, created_by_email, created_by_name, updated_by_email, updated_by_name

    __table_args__ = (
        Index('idx_cspm_results_scan', 'scan_id', 'check_id'),
        Index('idx_cspm_results_tenant_status', 'tenant_id', 'status'),
        Index('idx_cspm_results_check_status', 'check_id', 'status'),
        Index('idx_cspm_results_category', 'tenant_id', 'category'),
    )

    tenant_benchmark = relationship("CSPMTenantBenchmark", lazy="joined")

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "m365_tenant_id": self.m365_tenant_id,
            "scan_id": self.scan_id,
            "tenant_benchmark_id": self.tenant_benchmark_id,
            "tech_type": self.tech_type,
            "benchmark_id": self.benchmark_id,
            "benchmark_key": self.benchmark_key,
            "check_id": self.check_id,
            "category": self.category,
            "status": self.status,
            "status_id": self.status_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "details": self.details,
            "error": self.error,
            # CIS Metadata
            "title": self.title,
            "level": self.level,
            "section": self.section,
            "subsection": self.subsection,
            "recommendation_id": self.recommendation_id,
            "profile_applicability": self.profile_applicability,
            "description": self.description,
            "rationale": self.rationale,
            "impact": self.impact,
            "remediation": self.remediation,
            "audit_procedure": self.audit_procedure,
            "default_value": self.default_value,
            "references": self.references,
            "cis_controls": self.cis_controls,
            "metadata_raw": self.metadata_raw,
            **self.get_audit_info()
        }
