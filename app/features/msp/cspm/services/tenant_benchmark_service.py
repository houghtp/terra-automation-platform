"""
Tenant Benchmark Service

Manages benchmark assignments for platform tenants.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.core.sqlalchemy_imports import *
from app.features.msp.cspm.models import (
    CSPMBenchmark,
    CSPMComplianceScan,
    CSPMTenantBenchmark,
    M365Tenant,
)
from app.features.msp.cspm.schemas import (
    CSPMTenantBenchmarkCreate,
    CSPMTenantBenchmarkResponse,
    CSPMTenantBenchmarkUpdate,
)
from app.features.administration.tenants.db_models import Tenant


logger = get_logger(__name__)


class TenantBenchmarkService(BaseService[CSPMTenantBenchmark]):
    """Service for creating and managing tenant benchmark assignments."""

    async def list_assignments(self) -> List[CSPMTenantBenchmarkResponse]:
        """List benchmark assignments for the current tenant context."""
        stmt = (
            self.create_base_query(CSPMTenantBenchmark)
            .options(selectinload(CSPMTenantBenchmark.benchmark))
            .order_by(
                asc(CSPMTenantBenchmark.tech_type),
                asc(CSPMTenantBenchmark.display_name),
            )
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, CSPMTenantBenchmark)
        assignments = result.scalars().all()
        return [
            CSPMTenantBenchmarkResponse.model_validate(assignment)
            for assignment in assignments
        ]

    async def list_available_benchmarks(self) -> List[CSPMBenchmark]:
        """Return all registered benchmarks."""
        stmt = select(CSPMBenchmark).order_by(
            asc(CSPMBenchmark.tech_type), asc(CSPMBenchmark.display_name)
        )
        # Cross-tenant query - benchmarks are global resources
        result = await self.execute(
            stmt,
            CSPMBenchmark,
            allow_cross_tenant=True,
            reason="Listing all available benchmarks - benchmarks are global resources"
        )
        return list(result.scalars().all())

    async def get_available_tenants_for_forms(self) -> List[Dict[str, str]]:
        """Return active platform tenants for global admin selection."""
        stmt = (
            select(Tenant.id, Tenant.name)
            .where(Tenant.status == "active")
            .order_by(Tenant.name)
        )
        # Cross-tenant query - global admins need to see all platform tenants
        result = await self.execute(
            stmt,
            Tenant,
            allow_cross_tenant=True,
            reason="Global admin form dropdown - listing all active platform tenants"
        )
        tenants = result.fetchall()
        return [{"id": str(row.id), "name": row.name} for row in tenants]

    async def create_assignment(
        self,
        assignment_data: CSPMTenantBenchmarkCreate,
        created_by_user: Optional[Any] = None,
        target_tenant_id: Optional[str] = None,
    ) -> CSPMTenantBenchmarkResponse:
        """Assign a benchmark to a tenant."""
        effective_tenant_id = target_tenant_id or self.tenant_id
        if not effective_tenant_id:
            raise ValueError("Target tenant is required to create a benchmark assignment.")

        tenant_exists_stmt = select(func.count(Tenant.id)).where(
            cast(Tenant.id, String) == effective_tenant_id
        )
        # Cross-tenant query - global admin validating target tenant exists
        tenant_exists = await self.execute(
            tenant_exists_stmt,
            Tenant,
            allow_cross_tenant=True,
            reason="Global admin benchmark assignment - validating target platform tenant exists"
        )
        if (tenant_exists.scalar() or 0) == 0:
            raise ValueError("Selected tenant does not exist.")

        benchmark_stmt = (
            select(CSPMBenchmark)
            .where(CSPMBenchmark.id == assignment_data.benchmark_id)
            .limit(1)
        )
        # Cross-tenant query - benchmarks are global resources
        benchmark_result = await self.execute(
            benchmark_stmt,
            CSPMBenchmark,
            allow_cross_tenant=True,
            reason="Benchmark lookup for assignment creation - benchmarks are global resources"
        )
        benchmark = benchmark_result.scalar_one_or_none()
        if not benchmark:
            raise ValueError("Benchmark not found.")

        existing_stmt = (
            select(CSPMTenantBenchmark.id)
            .where(
                CSPMTenantBenchmark.tenant_id == effective_tenant_id,
                CSPMTenantBenchmark.benchmark_id == benchmark.id,
            )
            .limit(1)
        )
        # Tenant-scoped query with explicit tenant filter
        existing_result = await self.execute(existing_stmt, CSPMTenantBenchmark)
        if existing_result.scalar_one_or_none():
            raise ValueError("Benchmark already assigned to this tenant.")

        display_name = (
            assignment_data.display_name
            or benchmark.display_name
            or f"{benchmark.tech_type} Benchmark"
        )

        assignment = CSPMTenantBenchmark(
            id=str(uuid4()),
            tenant_id=effective_tenant_id,
            benchmark_id=benchmark.id,
            tech_type=benchmark.tech_type,
            display_name=display_name,
            status=assignment_data.status or "active",
            config_json=assignment_data.config or {},
        )

        audit_ctx = AuditContext.from_user(created_by_user)
        timestamp = datetime.now()
        assignment.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
        assignment.created_at = timestamp
        assignment.updated_at = timestamp

        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment, attribute_names=["benchmark"])

        logger.info(
            "Benchmark assigned to tenant",
            tenant_id=effective_tenant_id,
            benchmark_id=benchmark.id,
        )

        return CSPMTenantBenchmarkResponse.model_validate(assignment)

    async def get_assignment(
        self, assignment_id: str
    ) -> Optional[CSPMTenantBenchmarkResponse]:
        """Retrieve a benchmark assignment by ID."""
        stmt = (
            self.create_base_query(CSPMTenantBenchmark)
            .options(selectinload(CSPMTenantBenchmark.benchmark))
            .where(CSPMTenantBenchmark.id == assignment_id)
            .limit(1)
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, CSPMTenantBenchmark)
        assignment = result.scalar_one_or_none()
        return (
            CSPMTenantBenchmarkResponse.model_validate(assignment)
            if assignment
            else None
        )

    async def update_assignment(
        self,
        assignment_id: str,
        update_data: CSPMTenantBenchmarkUpdate,
        updated_by_user: Optional[Any] = None,
    ) -> CSPMTenantBenchmarkResponse:
        """Update assignment display name, status, or config."""
        stmt = (
            self.create_base_query(CSPMTenantBenchmark)
            .options(selectinload(CSPMTenantBenchmark.benchmark))
            .where(CSPMTenantBenchmark.id == assignment_id)
            .limit(1)
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, CSPMTenantBenchmark)
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ValueError("Benchmark assignment not found.")

        if update_data.display_name is not None:
            assignment.display_name = update_data.display_name
        if update_data.status is not None:
            assignment.status = update_data.status
        if update_data.config is not None:
            assignment.config_json = update_data.config

        audit_ctx = AuditContext.from_user(updated_by_user)
        assignment.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
        assignment.updated_at = datetime.now()

        await self.db.flush()
        await self.db.refresh(assignment, attribute_names=["benchmark"])

        logger.info(
            "Updated benchmark assignment",
            assignment_id=assignment_id,
            status=assignment.status,
        )

        return CSPMTenantBenchmarkResponse.model_validate(assignment)

    async def delete_assignment(
        self, assignment_id: str, deleted_by_user: Optional[Any] = None
    ) -> bool:
        """Delete or deactivate a benchmark assignment."""
        stmt = (
            self.create_base_query(CSPMTenantBenchmark)
            .where(CSPMTenantBenchmark.id == assignment_id)
            .limit(1)
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, CSPMTenantBenchmark)
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ValueError("Benchmark assignment not found.")

        # Check for dependent records
        tenant_count_stmt = select(func.count(M365Tenant.id)).where(
            M365Tenant.tenant_benchmark_id == assignment.id
        )
        # Tenant-scoped query - M365Tenants belong to same tenant as assignment
        tenant_count = await self.execute(tenant_count_stmt, M365Tenant)

        scan_count_stmt = select(func.count(CSPMComplianceScan.id)).where(
            CSPMComplianceScan.tenant_benchmark_id == assignment.id
        )
        # Tenant-scoped query - Scans belong to same tenant as assignment
        scan_count = await self.execute(scan_count_stmt, CSPMComplianceScan)

        has_dependencies = (tenant_count.scalar() or 0) > 0 or (
            scan_count.scalar() or 0
        ) > 0

        audit_ctx = AuditContext.from_user(deleted_by_user)
        timestamp = datetime.now()

        if has_dependencies:
            assignment.status = "inactive"
            assignment.set_deleted_by(audit_ctx.user_email, audit_ctx.user_name)
            assignment.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            assignment.updated_at = timestamp
            logger.info(
                "Marked benchmark assignment inactive due to dependencies",
                assignment_id=assignment_id,
            )
        else:
            await self.db.delete(assignment)
            logger.info(
                "Deleted benchmark assignment", assignment_id=assignment_id
            )

        await self.db.flush()

        return True
