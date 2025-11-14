"""
CSPM Analytics Service

Provides analytics data for compliance scans across all technology types.
Supports both tenant-scoped and global admin views.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.enhanced_base_service import BaseService
from app.features.msp.cspm.models import CSPMComplianceScan, CSPMComplianceResult
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class CSPMAnalyticsService(BaseService[CSPMComplianceScan]):
    """Service for CSPM analytics and reporting."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def get_scans_overview(self, days: int = 30) -> Dict[str, Any]:
        """
        Get overview statistics for scans dashboard (for stats widget).

        Args:
            days: Number of days to look back for trends

        Returns:
            Dict with stats for display
        """
        try:
            # Base query with tenant scope
            stmt = self.create_base_query(CSPMComplianceScan)

            # Filter to recent scans
            cutoff_date = datetime.now() - timedelta(days=days)
            stmt = stmt.where(CSPMComplianceScan.created_at >= cutoff_date)

            result = await self.execute(stmt, CSPMComplianceScan)
            scans = result.scalars().all()

            total_scans = len(scans)
            completed_scans = len([s for s in scans if s.status == 'completed'])

            # Calculate average pass rate
            pass_rates = []
            for scan in scans:
                if scan.status == 'completed' and scan.total_checks > 0:
                    pass_rate = (scan.passed / scan.total_checks) * 100
                    pass_rates.append(pass_rate)

            avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0

            return {
                'total_scans': total_scans,
                'completed_scans': completed_scans,
                'failed_scans': len([s for s in scans if s.status == 'failed']),
                'running_scans': len([s for s in scans if s.status in ['running', 'pending']]),
                'avg_pass_rate': f"{round(avg_pass_rate, 1)}%"
            }

        except Exception as e:
            await self.handle_error("get_scans_overview", e)
            raise

    async def get_compliance_over_time(self, days: int = 30, limit: int = 10) -> Dict[str, Any]:
        """
        Get compliance trend data over time (for line chart).

        Args:
            days: Number of days to look back
            limit: Maximum number of data points to return

        Returns:
            Dict with categories and values for chart-widget line chart
        """
        try:
            # Get completed scans ordered by date
            stmt = self.create_base_query(CSPMComplianceScan)
            stmt = stmt.where(
                and_(
                    CSPMComplianceScan.status == 'completed',
                    CSPMComplianceScan.completed_at.isnot(None),
                    CSPMComplianceScan.completed_at >= datetime.now() - timedelta(days=days)
                )
            ).order_by(desc(CSPMComplianceScan.completed_at)).limit(limit)

            result = await self.execute(stmt, CSPMComplianceScan)
            scans = result.scalars().all()

            # Build data in format expected by chart-widget
            categories = []
            values = []

            for scan in reversed(scans):  # Reverse to show oldest first
                if scan.total_checks > 0:
                    pass_rate = (scan.passed / scan.total_checks) * 100
                    categories.append(scan.completed_at.strftime('%m/%d %H:%M') if scan.completed_at else 'N/A')
                    values.append(round(pass_rate, 1))

            return {
                'categories': categories,
                'values': values
            }

        except Exception as e:
            await self.handle_error("get_compliance_over_time", e)
            raise

    async def get_scan_status_distribution(self) -> Dict[str, Any]:
        """
        Get count of scans by status (for donut chart).

        Returns:
            Dict with items array for chart-widget donut chart
        """
        try:
            stmt = select(
                CSPMComplianceScan.status,
                func.count(CSPMComplianceScan.id).label('count')
            )

            # Apply tenant filter
            if self.tenant_id is not None:
                stmt = stmt.where(CSPMComplianceScan.tenant_id == self.tenant_id)

            stmt = stmt.group_by(CSPMComplianceScan.status)

            result = await self.execute(
                stmt,
                CSPMComplianceScan,
                allow_cross_tenant=self.tenant_id is None,
                reason="Global admin dashboard - scan status distribution"
            )
            rows = result.all()

            # Convert to format expected by chart-widget: {items: [{name, value}]}
            items = [{'name': row.status.capitalize(), 'value': row.count} for row in rows]

            return {'items': items}

        except Exception as e:
            await self.handle_error("get_scan_status_distribution", e)
            raise

    async def get_scan_results_breakdown(self, scan_id: str) -> Dict[str, Any]:
        """
        Get detailed results breakdown for a specific scan (for donut chart).

        Args:
            scan_id: Scan ID to analyze

        Returns:
            Dict with items array for chart-widget donut chart
        """
        try:
            stmt = select(CSPMComplianceScan).where(CSPMComplianceScan.scan_id == scan_id)

            # Apply tenant filter
            if self.tenant_id is not None:
                stmt = stmt.where(CSPMComplianceScan.tenant_id == self.tenant_id)

            result = await self.execute(stmt, CSPMComplianceScan)
            scan = result.scalar_one_or_none()

            if not scan:
                raise ValueError(f"Scan {scan_id} not found")

            # Return in format expected by chart-widget donut type
            items = []
            if scan.passed > 0:
                items.append({'name': 'Passed', 'value': scan.passed})
            if scan.failed > 0:
                items.append({'name': 'Failed', 'value': scan.failed})
            if scan.errors > 0:
                items.append({'name': 'Errors', 'value': scan.errors})

            return {'items': items}

        except Exception as e:
            await self.handle_error("get_scan_results_breakdown", e, scan_id=scan_id)
            raise

    async def get_compliance_by_section(self, scan_id: str) -> Dict[str, Any]:
        """
        Get pass rate by section for a specific scan (for horizontal bar chart).

        Args:
            scan_id: Scan ID to analyze

        Returns:
            Dict with categories and values for chart-widget bar chart
        """
        try:
            # Group results by section
            stmt = select(
                CSPMComplianceResult.section,
                func.count(CSPMComplianceResult.id).label('total'),
                func.sum(
                    case((CSPMComplianceResult.status == 'Pass', 1), else_=0)
                ).label('passed')
            ).where(CSPMComplianceResult.scan_id == scan_id)

            # Apply tenant filter
            if self.tenant_id is not None:
                stmt = stmt.where(CSPMComplianceResult.tenant_id == self.tenant_id)

            stmt = stmt.group_by(CSPMComplianceResult.section).order_by(CSPMComplianceResult.section)

            result = await self.execute(
                stmt,
                CSPMComplianceResult,
                allow_cross_tenant=False  # Results are always tenant-scoped via scan_id
            )
            rows = result.all()

            categories = []
            values = []

            for row in rows:
                if row.section:  # Skip null sections
                    pass_rate = (row.passed / row.total * 100) if row.total > 0 else 0
                    categories.append(row.section)
                    values.append(round(pass_rate, 1))

            return {
                'categories': categories,
                'values': values
            }

        except Exception as e:
            await self.handle_error("get_compliance_by_section", e, scan_id=scan_id)
            raise

    async def get_level_distribution(self, scan_id: str) -> Dict[str, Any]:
        """
        Get results distribution by level (L1/L2) for a specific scan (for donut chart).

        Args:
            scan_id: Scan ID to analyze

        Returns:
            Dict with items array for chart-widget donut chart
        """
        try:
            stmt = select(
                CSPMComplianceResult.level,
                func.count(CSPMComplianceResult.id).label('total')
            ).where(CSPMComplianceResult.scan_id == scan_id)

            # Apply tenant filter
            if self.tenant_id is not None:
                stmt = stmt.where(CSPMComplianceResult.tenant_id == self.tenant_id)

            stmt = stmt.group_by(CSPMComplianceResult.level)

            result = await self.execute(
                stmt,
                CSPMComplianceResult,
                allow_cross_tenant=False
            )
            rows = result.all()

            # Convert to format expected by chart-widget: {items: [{name, value}]}
            items = []
            for row in rows:
                if row.level:
                    items.append({'name': row.level, 'value': row.total})

            return {'items': items}

        except Exception as e:
            await self.handle_error("get_level_distribution", e, scan_id=scan_id)
            raise

    async def get_top_failures(self, scan_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top failed checks for a specific scan.

        Args:
            scan_id: Scan ID to analyze
            limit: Maximum number of failures to return

        Returns:
            List of failed check details
        """
        try:
            stmt = select(CSPMComplianceResult).where(
                and_(
                    CSPMComplianceResult.scan_id == scan_id,
                    CSPMComplianceResult.status == 'Fail'
                )
            )

            # Apply tenant filter
            if self.tenant_id is not None:
                stmt = stmt.where(CSPMComplianceResult.tenant_id == self.tenant_id)

            # Order by level (L1 first) then recommendation_id
            stmt = stmt.order_by(
                CSPMComplianceResult.level,
                CSPMComplianceResult.recommendation_id
            ).limit(limit)

            result = await self.execute(stmt, CSPMComplianceResult)
            failures = result.scalars().all()

            return [
                {
                    'check_id': f.check_id,
                    'title': f.title or f.check_id,
                    'recommendation_id': f.recommendation_id,
                    'section': f.section,
                    'subsection': f.subsection,
                    'level': f.level
                }
                for f in failures
            ]

        except Exception as e:
            await self.handle_error("get_top_failures", e, scan_id=scan_id)
            raise
