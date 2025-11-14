"""
CSPM Scan Service

Orchestrates compliance scans and manages scan lifecycle.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from datetime import datetime
import uuid
from typing import Optional, Any, List, Dict
from sqlalchemy.orm import selectinload

from app.features.msp.cspm.models import (
    CSPMComplianceScan,
    CSPMComplianceResult,
    M365Tenant,
    CSPMBenchmark,
    CSPMTenantBenchmark,
)
from app.features.msp.cspm.schemas import (
    ComplianceScanRequest,
    ComplianceScanResponse,
    ScanProgressUpdate,
    ScanStatusResponse,
    ComplianceResultResponse
)
from app.features.core.audit_mixin import AuditContext
from app.features.msp.cspm.services.websocket_manager import websocket_manager

logger = get_logger(__name__)


class CSPMScanService(BaseService[CSPMComplianceScan]):
    """
    Service for managing CSPM compliance scans.

    Handles scan creation, status tracking, progress updates, and result storage.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def _resolve_benchmark(
        self,
        tech_type: Optional[str],
        benchmark_id: Optional[str],
        benchmark_key: Optional[str]
    ) -> CSPMBenchmark:
        """
        Resolve the benchmark metadata for a scan, falling back to the default for the tech.
        """
        resolved_tech = tech_type or "M365"
        stmt = select(CSPMBenchmark)

        if benchmark_id:
            stmt = stmt.where(CSPMBenchmark.id == benchmark_id)
        elif benchmark_key:
            stmt = stmt.where(
                and_(
                    CSPMBenchmark.benchmark_key == benchmark_key,
                    CSPMBenchmark.tech_type == resolved_tech
                )
            )
        else:
            stmt = stmt.where(CSPMBenchmark.tech_type == resolved_tech).order_by(asc(CSPMBenchmark.created_at))

        stmt = stmt.limit(1)
        # Cross-tenant query - benchmarks are global resources
        result = await self.execute(
            stmt,
            CSPMBenchmark,
            allow_cross_tenant=True,
            reason="Benchmark lookup - benchmarks are global resources shared across tenants"
        )
        benchmark = result.scalar_one_or_none()

        if not benchmark:
            raise ValueError(f"Benchmark not found for tech '{resolved_tech}'")

        return benchmark

    async def create_scan(
        self,
        scan_request: ComplianceScanRequest,
        celery_task_id: str,
        created_by_user: Optional[Any] = None
    ) -> ComplianceScanResponse:
        """
        Create new compliance scan record.

        Args:
            scan_request: Scan request parameters
            celery_task_id: Celery task ID for tracking
            created_by_user: User creating the scan (for audit)

        Returns:
            Created scan response
        """
        scan_id = str(uuid.uuid4())

        logger.info(
            "Creating compliance scan",
            scan_id=scan_id,
            m365_tenant_id=scan_request.m365_tenant_id
        )

        assignment = None
        benchmark = None

        if scan_request.tenant_benchmark_id:
            assignment_stmt = (
                select(CSPMTenantBenchmark)
                .options(selectinload(CSPMTenantBenchmark.benchmark))
                .where(CSPMTenantBenchmark.id == scan_request.tenant_benchmark_id)
                .limit(1)
            )
            # Tenant-scoped query - assignment belongs to tenant
            assignment_result = await self.execute(assignment_stmt, CSPMTenantBenchmark)
            assignment = assignment_result.scalar_one_or_none()
            if not assignment:
                raise ValueError(f"Tenant benchmark {scan_request.tenant_benchmark_id} not found")
        else:
            tenant_stmt = (
                select(M365Tenant)
                .options(
                    selectinload(M365Tenant.tenant_benchmark)
                    .selectinload(CSPMTenantBenchmark.benchmark)
                )
                .where(M365Tenant.id == scan_request.m365_tenant_id)
                .limit(1)
            )
            # Tenant-scoped query - M365Tenant belongs to platform tenant
            tenant_result = await self.execute(tenant_stmt, M365Tenant)
            tenant = tenant_result.scalar_one_or_none()
            if not tenant or not tenant.tenant_benchmark:
                raise ValueError("Tenant benchmark assignment not found for selected M365 tenant")
            assignment = tenant.tenant_benchmark

        if assignment.status and assignment.status.lower() != "active":
            raise ValueError(
                f"Benchmark assignment '{assignment.display_name}' is inactive. Reactivate it before scanning."
            )

        if assignment.benchmark:
            benchmark = assignment.benchmark
        else:
            benchmark = await self._resolve_benchmark(
                assignment.tech_type,
                assignment.benchmark_id,
                scan_request.benchmark_key
            )
            assignment.benchmark_id = benchmark.id
            assignment.tech_type = benchmark.tech_type
            assignment.updated_at = datetime.now()
            audit_ctx_assignment = AuditContext.from_user(created_by_user)
            assignment.set_updated_by(audit_ctx_assignment.user_email, audit_ctx_assignment.user_name)

        if scan_request.benchmark_id and scan_request.benchmark_id != assignment.benchmark_id:
            benchmark = await self._resolve_benchmark(
                scan_request.tech_type or assignment.tech_type,
                scan_request.benchmark_id,
                scan_request.benchmark_key
            )
            assignment.benchmark_id = benchmark.id
            assignment.tech_type = benchmark.tech_type
            assignment.updated_at = datetime.now()
            audit_ctx_assignment = AuditContext.from_user(created_by_user)
            assignment.set_updated_by(audit_ctx_assignment.user_email, audit_ctx_assignment.user_name)

        tech_type = assignment.tech_type or benchmark.tech_type or scan_request.tech_type or "M365"
        assignment.benchmark = benchmark

        # Build scan options
        scan_options = {
            "l1_only": scan_request.l1_only,
            "check_ids": scan_request.check_ids or [],
            "output_format": scan_request.output_format
        }

        # Create scan record
        scan = CSPMComplianceScan(
            scan_id=scan_id,
            tenant_id=self.tenant_id,
            m365_tenant_id=scan_request.m365_tenant_id,
            tenant_benchmark_id=assignment.id,
            tech_type=tech_type,
            scan_options=scan_options,
            benchmark_id=benchmark.id,
            benchmark_key=benchmark.benchmark_key,
            status="pending",
            progress_percentage=0,
            total_checks=0,
            passed=0,
            failed=0,
            errors=0,
            celery_task_id=celery_task_id,
        )

        audit_ctx = AuditContext.from_user(created_by_user)
        scan.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
        timestamp = datetime.now()
        scan.created_at = timestamp
        scan.updated_at = timestamp

        self.db.add(scan)
        await self.db.flush()
        await self.db.refresh(scan)

        self.log_operation("cspm_scan_creation", {"scan_id": scan_id})

        setattr(scan, "benchmark_display_name", benchmark.display_name)
        setattr(scan, "assignment_display_name", assignment.display_name)

        return ComplianceScanResponse.model_validate(self._attach_scan_metadata(scan))

    async def update_scan_status(
        self,
        scan_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> ComplianceScanResponse:
        """
        Update scan status.

        Args:
            scan_id: Scan ID
            status: New status (pending, running, completed, failed, cancelled)
            error_message: Optional error message

        Returns:
            Updated scan response

        Raises:
            ValueError: If scan not found
        """
        logger.info("Updating scan status", scan_id=scan_id, status=status)

        scan = await self._get_scan_by_scan_id(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        scan.status = status
        now_utc = datetime.now()
        scan.updated_at = now_utc
        system_ctx = AuditContext.system()
        scan.set_updated_by(system_ctx.user_email, system_ctx.user_name)

        if status == "running" and not scan.started_at:
            scan.started_at = now_utc

        if status in ["completed", "failed", "cancelled"]:
            scan.completed_at = now_utc
            scan.current_check = None  # Clear current_check on terminal status

        if error_message:
            scan.error_message = error_message

        await self.db.flush()

        self.log_operation("cspm_scan_status_update", {"scan_id": scan_id, "status": status})

        # Broadcast status change to WebSocket clients
        await websocket_manager.broadcast(
            scan_id,
            {
                "event": "status",
                "scan_id": scan_id,
                "status": status,
                "progress_percentage": scan.progress_percentage or 0,
                "current_check": None,  # Clear current_check on status change
                "error_message": error_message
            }
        )

        return ComplianceScanResponse.model_validate(self._attach_scan_metadata(scan))

    async def update_scan_progress(
        self,
        scan_id: str,
        progress_update: ScanProgressUpdate
    ) -> ComplianceScanResponse:
        """
        Update scan progress from webhook.

        Args:
            scan_id: Scan ID
            progress_update: Progress update data

        Returns:
            Updated scan response

        Raises:
            ValueError: If scan not found
        """
        logger.debug(
            "Updating scan progress",
            scan_id=scan_id,
            progress=progress_update.progress_percentage
        )

        scan = await self._get_scan_by_scan_id(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        # Update progress fields
        scan.progress_percentage = progress_update.progress_percentage
        scan.updated_at = datetime.now()
        system_ctx = AuditContext.system()
        scan.set_updated_by(system_ctx.user_email, system_ctx.user_name)

        # Clear current_check if progress is 100% (scan finishing)
        if progress_update.progress_percentage >= 100:
            scan.current_check = None
        elif progress_update.current_check:
            scan.current_check = progress_update.current_check

        if progress_update.total_checks is not None:
            scan.total_checks = progress_update.total_checks

        if progress_update.passed is not None:
            scan.passed = progress_update.passed

        if progress_update.failed is not None:
            scan.failed = progress_update.failed

        if progress_update.errors is not None:
            scan.errors = progress_update.errors

        await self.db.flush()

        return ComplianceScanResponse.model_validate(self._attach_scan_metadata(scan))

    async def get_scan_status(self, scan_id: str) -> Optional[ScanStatusResponse]:
        """
        Get current scan status.

        Args:
            scan_id: Scan ID

        Returns:
            Scan status response or None if not found
        """
        scan = await self._get_scan_by_scan_id(scan_id)
        if not scan:
            return None

        assignment = scan.tenant_benchmark
        benchmark_display = None
        assignment_display = None

        if assignment:
            assignment_display = assignment.display_name
            if not scan.tech_type:
                scan.tech_type = assignment.tech_type
            if assignment.benchmark:
                benchmark_display = assignment.benchmark.display_name
                scan.benchmark_key = scan.benchmark_key or assignment.benchmark.benchmark_key
                scan.benchmark_id = scan.benchmark_id or assignment.benchmark.id

        if not benchmark_display and scan.benchmark_id:
            # Cross-tenant query - benchmarks are global resources
            result = await self.execute(
                select(CSPMBenchmark.display_name).where(CSPMBenchmark.id == scan.benchmark_id).limit(1),
                CSPMBenchmark,
                allow_cross_tenant=True,
                reason="Benchmark display name lookup - benchmarks are global resources"
            )
            benchmark_display = result.scalar_one_or_none()

        config = assignment.config_json if assignment else {}
        target_identifier = None
        target_display = assignment_display
        if config:
            target_identifier = (
                config.get("target_identifier")
                or config.get("m365_tenant_id")
                or config.get("azure_subscription_id")
                or config.get("aws_account_id")
            )
            target_display = (
                config.get("target_display_name")
                or config.get("m365_tenant_name")
                or config.get("azure_subscription_name")
                or assignment_display
            )

        return ScanStatusResponse(
            scan_id=scan.scan_id,
            status=scan.status,
            progress_percentage=scan.progress_percentage,
            current_check=scan.current_check,
            total_checks=scan.total_checks,
            passed=scan.passed,
            failed=scan.failed,
            errors=scan.errors,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            error_message=scan.error_message,
            tech_type=scan.tech_type,
            benchmark_id=scan.benchmark_id,
            benchmark_key=scan.benchmark_key,
            benchmark_display_name=benchmark_display,
            tenant_benchmark_id=assignment.id if assignment else None,
            assignment_display_name=assignment_display,
            target_identifier=target_identifier,
            target_display_name=target_display,
            m365_tenant_id=scan.m365_tenant_id
        )

    async def list_scans(
        self,
        m365_tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ComplianceScanResponse]:
        """
        List scans with optional filters.

        Args:
            m365_tenant_id: Filter by M365 tenant
            status: Filter by status
            limit: Maximum results
            offset: Results offset

        Returns:
            List of scan responses
        """
        logger.debug("Listing scans", m365_tenant_id=m365_tenant_id, status=status)

        stmt = (
            self.create_base_query(CSPMComplianceScan)
            .options(
                selectinload(CSPMComplianceScan.tenant_benchmark)
                .selectinload(CSPMTenantBenchmark.benchmark)
            )
        )

        if m365_tenant_id:
            stmt = stmt.where(CSPMComplianceScan.m365_tenant_id == m365_tenant_id)

        if status:
            stmt = stmt.where(CSPMComplianceScan.status == status)

        stmt = stmt.order_by(desc(CSPMComplianceScan.created_at)).limit(limit).offset(offset)

        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, CSPMComplianceScan)
        scans = result.scalars().all()

        if not scans:
            return []

        tenant_ids = {scan.m365_tenant_id for scan in scans if scan.m365_tenant_id}
        tenant_mapping: dict[str, tuple[str, str]] = {}
        benchmark_ids = {scan.benchmark_id for scan in scans if getattr(scan, "benchmark_id", None)}
        benchmark_mapping: dict[str, tuple[str, str]] = {}

        if tenant_ids:
            # Tenant-scoped query - M365Tenants belong to platform tenant
            tenant_rows = await self.execute(
                select(
                    M365Tenant.id,
                    M365Tenant.m365_tenant_name,
                    M365Tenant.m365_tenant_id
                ).where(
                    or_(
                        M365Tenant.id.in_(tenant_ids),
                        M365Tenant.m365_tenant_id.in_(tenant_ids)
                    )
                ),
                M365Tenant
            )
            for row in tenant_rows:
                tenant_mapping[str(row.id)] = (
                    row.m365_tenant_name,
                    row.m365_tenant_id
                )
                tenant_mapping[str(row.m365_tenant_id)] = (
                    row.m365_tenant_name,
                    row.m365_tenant_id
                )

        if benchmark_ids:
            # Cross-tenant query - benchmarks are global resources
            benchmark_rows = await self.execute(
                select(
                    CSPMBenchmark.id,
                    CSPMBenchmark.display_name,
                    CSPMBenchmark.benchmark_key
                ).where(CSPMBenchmark.id.in_(benchmark_ids)),
                CSPMBenchmark,
                allow_cross_tenant=True,
                reason="Benchmark lookup for scan enrichment - benchmarks are global resources"
            )
            for row in benchmark_rows:
                benchmark_mapping[str(row.id)] = (
                    row.display_name,
                    row.benchmark_key
                )

        enriched = []
        for scan in scans:
            display_name = None
            if scan.m365_tenant_id and scan.m365_tenant_id in tenant_mapping:
                display_name, _ = tenant_mapping[scan.m365_tenant_id]

            setattr(scan, "tenant_display_name", display_name)

            assignment = scan.tenant_benchmark
            benchmark = assignment.benchmark if assignment and assignment.benchmark else None

            if benchmark is None and scan.benchmark_id and scan.benchmark_id in benchmark_mapping:
                bench_display, bench_key = benchmark_mapping[scan.benchmark_id]
            else:
                bench_display = benchmark.display_name if benchmark else None
                bench_key = benchmark.benchmark_key if benchmark else scan.benchmark_key

            setattr(scan, "benchmark_display_name", bench_display)
            if not getattr(scan, "benchmark_key", None) and bench_key:
                scan.benchmark_key = bench_key

            if assignment:
                setattr(scan, "assignment_display_name", assignment.display_name)
                if not getattr(scan, "tech_type", None):
                    scan.tech_type = assignment.tech_type
                config = assignment.config_json or {}
            else:
                setattr(scan, "assignment_display_name", None)
                config = {}

            target_identifier = (
                config.get("target_identifier")
                or config.get("m365_tenant_id")
                or config.get("azure_subscription_id")
                or config.get("aws_account_id")
            )
            target_display = (
                config.get("target_display_name")
                or config.get("m365_tenant_name")
                or config.get("azure_subscription_name")
            )
            if not target_display:
                target_display = assignment.display_name if assignment else display_name

            if not target_identifier and scan.m365_tenant_id and scan.m365_tenant_id in tenant_mapping:
                _, tenant_identifier = tenant_mapping[scan.m365_tenant_id]
                target_identifier = tenant_identifier
            if not target_display:
                target_display = display_name or (assignment.display_name if assignment else None)

            setattr(scan, "target_identifier", target_identifier)
            setattr(scan, "target_display_name", target_display)

            enriched.append(ComplianceScanResponse.model_validate(scan))

        return enriched

    async def cancel_scan(self, scan_id: str) -> bool:
        """
        Cancel running scan.

        Args:
            scan_id: Scan ID

        Returns:
            True if cancelled

        Raises:
            ValueError: If scan not found or not cancellable
        """
        logger.info("Cancelling scan", scan_id=scan_id)

        scan = await self._get_scan_by_scan_id(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        if scan.status not in ["pending", "running"]:
            raise ValueError(f"Cannot cancel scan with status {scan.status}")

        scan.status = "cancelled"
        now_utc = datetime.now()
        scan.completed_at = now_utc
        scan.updated_at = now_utc
        system_ctx = AuditContext.system()
        scan.set_updated_by(system_ctx.user_email, system_ctx.user_name)

        await self.db.flush()

        self.log_operation("cspm_scan_cancellation", {"scan_id": scan_id})

        return True

    async def bulk_insert_results(
        self,
        scan_id: str,
        results: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk insert compliance check results.

        Args:
            scan_id: Scan ID for grouping results
            results: List of result dictionaries from PowerShell

        Returns:
            Number of results inserted
        """
        logger.info("Bulk inserting results", scan_id=scan_id, count=len(results))

        # Get scan to get tenant info
        scan = await self._get_scan_by_scan_id(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        config = getattr(scan.tenant_benchmark, "config_json", {}) or {}
        target_identifier = (
            config.get("target_identifier")
            or config.get("m365_tenant_id")
            or config.get("azure_subscription_id")
            or config.get("aws_account_id")
        )

        # Prepare result records
        result_records = []
        for result_data in results:
            # Parse datetime strings if present
            start_time = None
            end_time = None

            if result_data.get("StartTime"):
                try:
                    # Parse ISO timestamp and convert to naive UTC datetime
                    start_time = datetime.fromisoformat(result_data["StartTime"].replace("Z", ""))
                    # Remove timezone info if present to get naive UTC
                    if start_time.tzinfo is not None:
                        start_time = start_time.replace(tzinfo=None)
                except Exception:
                    pass

            if result_data.get("EndTime"):
                try:
                    # Parse ISO timestamp and convert to naive UTC datetime
                    end_time = datetime.fromisoformat(result_data["EndTime"].replace("Z", ""))
                    # Remove timezone info if present to get naive UTC
                    if end_time.tzinfo is not None:
                        end_time = end_time.replace(tzinfo=None)
                except Exception:
                    pass

            # Extract CIS metadata if present
            metadata = result_data.get("Metadata", {}) or {}

            timestamp = datetime.now()
            result_record = CSPMComplianceResult(
                tenant_id=scan.tenant_id,
                m365_tenant_id=scan.m365_tenant_id,
                scan_id=scan_id,
                tenant_benchmark_id=scan.tenant_benchmark_id,
                tech_type=result_data.get("TechType", scan.tech_type),
                benchmark_id=scan.benchmark_id,
                benchmark_key=scan.benchmark_key,
                check_id=result_data.get("CheckId", "unknown"),
                category=result_data.get("Category"),
                status=result_data.get("Status", "Error"),
                status_id=result_data.get("StatusId"),
                start_time=start_time,
                end_time=end_time,
                duration=result_data.get("Duration"),
                details=result_data.get("Details", []),
                error=result_data.get("Error"),
                # CIS Metadata fields
                title=metadata.get("Title"),
                level=metadata.get("Level"),
                section=metadata.get("Section"),
                subsection=metadata.get("SubSection"),
                recommendation_id=metadata.get("RecommendationId"),
                profile_applicability=metadata.get("ProfileApplicability"),
                description=metadata.get("Description"),
                rationale=metadata.get("Rationale"),
                impact=metadata.get("Impact"),
                remediation=metadata.get("Remediation"),
                audit_procedure=metadata.get("Audit"),
                default_value=metadata.get("DefaultValue"),
                references=metadata.get("References"),
                cis_controls=metadata.get("CISControls"),
                metadata_raw=metadata if metadata else None,
                created_at=timestamp,
                updated_at=timestamp
            )
            audit_ctx = AuditContext.system()
            result_record.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            if target_identifier:
                setattr(result_record, "target_identifier", target_identifier)
            if scan.tenant_benchmark:
                setattr(result_record, "assignment_display_name", scan.tenant_benchmark.display_name)
                if scan.tenant_benchmark.benchmark and not result_record.benchmark_key:
                    result_record.benchmark_key = scan.tenant_benchmark.benchmark.benchmark_key
            result_records.append(result_record)

        # Bulk insert
        self.db.add_all(result_records)
        await self.db.flush()

        # Update scan summary
        await self._update_scan_summary(scan_id)

        self.log_operation(
            "cspm_results_bulk_insert",
            {"scan_id": scan_id, "count": len(result_records)}
        )

        return len(result_records)

    async def get_scan_results(
        self,
        scan_id: str,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ComplianceResultResponse]:
        """
        Get results for a specific scan.

        Args:
            scan_id: Scan ID
            status_filter: Filter by status (Pass, Fail, Error)
            category_filter: Filter by category (L1, L2)
            limit: Maximum results
            offset: Results offset

        Returns:
            List of compliance result responses
        """
        logger.debug("Getting scan results", scan_id=scan_id, status=status_filter)

        stmt = select(CSPMComplianceResult).where(CSPMComplianceResult.scan_id == scan_id)

        # Apply tenant filtering
        if self.tenant_id is not None:
            stmt = stmt.where(CSPMComplianceResult.tenant_id == self.tenant_id)

        if status_filter:
            stmt = stmt.where(CSPMComplianceResult.status == status_filter)

        if category_filter:
            stmt = stmt.where(CSPMComplianceResult.category == category_filter)

        stmt = stmt.order_by(CSPMComplianceResult.check_id).limit(limit).offset(offset)

        # Tenant-scoped query - results belong to tenant via scan_id
        result = await self.execute(stmt, CSPMComplianceResult)
        results = result.scalars().all()

        if not results:
            return []

        enriched = []
        for res in results:
            assignment = res.tenant_benchmark
            benchmark = assignment.benchmark if assignment and assignment.benchmark else None

            setattr(res, "benchmark_display_name", benchmark.display_name if benchmark else None)
            if assignment:
                setattr(res, "assignment_display_name", assignment.display_name)
                if not getattr(res, "tech_type", None):
                    res.tech_type = assignment.tech_type
                config = assignment.config_json or {}
                target_identifier = (
                    config.get("target_identifier")
                    or config.get("m365_tenant_id")
                    or config.get("azure_subscription_id")
                    or config.get("aws_account_id")
                )
                if target_identifier and not getattr(res, "target_identifier", None):
                    setattr(res, "target_identifier", target_identifier)
            else:
                setattr(res, "assignment_display_name", None)

            enriched.append(ComplianceResultResponse.model_validate(res))

        return enriched

    def _attach_scan_metadata(self, scan: CSPMComplianceScan) -> CSPMComplianceScan:
        assignment = getattr(scan, "tenant_benchmark", None)
        benchmark = None
        if assignment and assignment.benchmark:
            benchmark = assignment.benchmark
        elif scan.benchmark_id:
            # Best effort fetch if relationship not loaded
            pass

        config = getattr(assignment, "config_json", {}) or {}
        target_identifier = (
            config.get("target_identifier")
            or config.get("m365_tenant_id")
            or config.get("azure_subscription_id")
            or config.get("aws_account_id")
        )
        target_display_name = (
            config.get("target_display_name")
            or config.get("m365_tenant_name")
            or config.get("azure_subscription_name")
            or (assignment.display_name if assignment else None)
        )

        setattr(scan, "assignment_display_name", assignment.display_name if assignment else None)
        setattr(scan, "benchmark_display_name", benchmark.display_name if benchmark else None)
        setattr(scan, "target_identifier", target_identifier)
        setattr(scan, "target_display_name", target_display_name)

        # Ensure legacy m365_tenant_id attribute is populated for downstream compatibility
        if not getattr(scan, "m365_tenant_id", None) and config.get("m365_tenant_id"):
            setattr(scan, "m365_tenant_id", config.get("m365_tenant_id"))

        return scan

    async def _get_scan_by_scan_id(self, scan_id: str) -> Optional[CSPMComplianceScan]:
        """
        Get scan by scan_id (not primary key id).

        Args:
            scan_id: Scan UUID

        Returns:
            Scan model or None
        """
        stmt = (
            self.create_base_query(CSPMComplianceScan)
            .options(
                selectinload(CSPMComplianceScan.tenant_benchmark)
                .selectinload(CSPMTenantBenchmark.benchmark)
            )
            .where(CSPMComplianceScan.scan_id == scan_id)
        )

        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, CSPMComplianceScan)
        return result.scalar_one_or_none()

    async def _update_scan_summary(self, scan_id: str) -> None:
        """
        Update scan summary metrics from results.

        Args:
            scan_id: Scan ID
        """
        scan = await self._get_scan_by_scan_id(scan_id)
        if not scan:
            return

        # Count results by status
        stmt = select(
            func.count(CSPMComplianceResult.id).label("total"),
            func.sum(case((CSPMComplianceResult.status == "Pass", 1), else_=0)).label("passed"),
            func.sum(case((CSPMComplianceResult.status == "Fail", 1), else_=0)).label("failed"),
            func.sum(case((CSPMComplianceResult.status == "Error", 1), else_=0)).label("errors")
        ).where(CSPMComplianceResult.scan_id == scan_id)

        # Aggregation query - scan_id provides implicit tenant scope
        result = await self.execute(
            stmt,
            CSPMComplianceResult,
            allow_cross_tenant=True,
            reason="Scan summary aggregation - scan_id provides implicit tenant scope"
        )
        summary = result.one()

        scan.total_checks = summary.total or 0
        scan.passed = summary.passed or 0
        scan.failed = summary.failed or 0
        scan.errors = summary.errors or 0
        scan.progress_percentage = 100
        system_ctx = AuditContext.system()
        scan.set_updated_by(system_ctx.user_email, system_ctx.user_name)
        scan.updated_at = datetime.now()

        await self.db.flush()

        logger.debug(
            "Scan summary updated",
            scan_id=scan_id,
            total=scan.total_checks,
            passed=scan.passed,
            failed=scan.failed
        )
