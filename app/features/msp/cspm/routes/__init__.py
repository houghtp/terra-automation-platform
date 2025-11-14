"""
CSPM Routes

Aggregates all CSPM-related routes (API, forms, and dashboards).
"""

from fastapi import APIRouter
from .webhook_routes import router as webhook_router
from .m365_tenant_routes import router as m365_tenant_router
from .scan_routes import router as scan_router
from .benchmark_routes import router as benchmark_router
from .tenant_benchmark_routes import router as tenant_benchmark_router
from .stream_routes import router as stream_router
from .form_routes import router as form_router
from .dashboard_routes import router as dashboard_router
from .analytics_routes import router as analytics_router

# Create main CSPM router
cspm_router = APIRouter(tags=["cspm"])

# Include dashboard routes (no prefix - already has /msp/cspm)
cspm_router.include_router(dashboard_router)

# Include form routes (under /msp/cspm)
cspm_router.include_router(form_router, prefix="/msp/cspm")

# Include API routes (under /msp/cspm)
cspm_router.include_router(webhook_router, prefix="/msp/cspm")
cspm_router.include_router(m365_tenant_router, prefix="/msp/cspm")
cspm_router.include_router(tenant_benchmark_router, prefix="/msp/cspm")
cspm_router.include_router(scan_router, prefix="/msp/cspm")
cspm_router.include_router(benchmark_router, prefix="/msp/cspm")
cspm_router.include_router(stream_router, prefix="/msp/cspm")
cspm_router.include_router(analytics_router)

__all__ = ["cspm_router"]
