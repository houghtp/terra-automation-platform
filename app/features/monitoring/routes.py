"""
Monitoring endpoints for Prometheus metrics and enhanced health checks.
Provides comprehensive application monitoring and observability.
"""
import time
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
import asyncio

from app.features.core.metrics import metrics
from app.features.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from .schemas import HealthStatus, MetricsInfo

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus exposition format.
    """
    try:
        metrics_data = metrics.get_metrics()

        # Record metrics access
        metrics.record_feature_usage("metrics_access", tenant_id="system")

        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        metrics.record_security_event("metrics_error", "high", "system")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/metrics/info", response_model=MetricsInfo)
async def get_metrics_info():
    """Get information about the metrics endpoint."""
    return MetricsInfo(
        endpoint="/metrics",
        format="prometheus",
        description="Prometheus metrics exposition endpoint",
        content_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get("/health/detailed", response_model=HealthStatus)
async def get_detailed_health(session: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check with detailed component status.
    Includes database, secrets, and application health.
    """
    start_time = time.time()
    checks = {}
    overall_status = "healthy"

    try:
        # Database health check
        try:
            db_start = time.time()
            result = await session.execute(text("SELECT 1"))
            db_duration = time.time() - db_start

            checks["database"] = {
                "status": "healthy",
                "response_time_ms": round(db_duration * 1000, 2),
                "connection": "active"
            }

            # Record database metrics
            metrics.record_database_query("health_check", db_duration, "system")

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            checks["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }
            overall_status = "unhealthy"
            metrics.record_database_query("health_check", 0, "system", "connection_failed")

        # Secrets management health check
        try:
            from app.features.core.secrets_manager import get_secrets_manager
            secrets_status = await _check_secrets_health()
            checks["secrets"] = secrets_status

            if secrets_status["status"] != "healthy":
                overall_status = "degraded" if overall_status == "healthy" else "unhealthy"

        except Exception as e:
            logger.error(f"Secrets health check failed: {e}")
            checks["secrets"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_status = "unhealthy"

        # Rate limiting health check
        try:
            rate_limit_status = await _check_rate_limiting_health()
            checks["rate_limiting"] = rate_limit_status

            if rate_limit_status["status"] != "healthy":
                overall_status = "degraded" if overall_status == "healthy" else "unhealthy"

        except Exception as e:
            logger.error(f"Rate limiting health check failed: {e}")
            checks["rate_limiting"] = {
                "status": "degraded",
                "error": str(e)
            }
            if overall_status == "healthy":
                overall_status = "degraded"

        # Application metrics health
        try:
            app_metrics = await _check_application_metrics()
            checks["application"] = app_metrics

        except Exception as e:
            logger.error(f"Application metrics check failed: {e}")
            checks["application"] = {
                "status": "degraded",
                "error": str(e)
            }

        # System resources (if psutil is available)
        try:
            import psutil
            system_info = {
                "status": "healthy",
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }

            # Mark as degraded if resources are high
            if (system_info["cpu_percent"] > 80 or
                system_info["memory_percent"] > 85 or
                system_info["disk_percent"] > 90):
                system_info["status"] = "degraded"
                if overall_status == "healthy":
                    overall_status = "degraded"

            checks["system"] = system_info

        except ImportError:
            checks["system"] = {
                "status": "unknown",
                "message": "psutil not available"
            }
        except Exception as e:
            checks["system"] = {
                "status": "degraded",
                "error": str(e)
            }

        # Update application health metric
        metrics.set_application_health(overall_status)

        # Record health check metrics
        total_duration = time.time() - start_time
        metrics.record_feature_usage("health_check_detailed", "system")

        import os
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.now(),
            version=os.getenv("APP_VERSION", "dev"),
            environment=os.getenv("ENVIRONMENT", "development"),
            checks=checks
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        metrics.record_security_event("health_check_error", "high", "system")

        import os
        return HealthStatus(
            status="unhealthy",
            timestamp=datetime.now(),
            version=os.getenv("APP_VERSION", "dev"),
            environment=os.getenv("ENVIRONMENT", "development"),
            checks={"error": str(e)}
        )


async def _check_secrets_health() -> Dict[str, Any]:
    """Check secrets management system health."""
    try:
        from app.features.core.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()

        # Test secrets access
        test_start = time.time()
        await secrets_manager.get_secret("JWT_SECRET_KEY")
        access_time = time.time() - test_start

        backend_info = {
            "backend": secrets_manager.provider.__class__.__name__,
            "response_time_ms": round(access_time * 1000, 2)
        }

        # Record successful access
        metrics.record_secrets_access(backend_info["backend"], True)

        return {
            "status": "healthy",
            **backend_info
        }

    except Exception as e:
        # Record failed access
        metrics.record_secrets_access("unknown", False)
        return {
            "status": "degraded",
            "error": str(e)
        }


async def _check_rate_limiting_health() -> Dict[str, Any]:
    """Check rate limiting system health."""
    try:
        from app.middleware.rate_limiting import RateLimitMiddleware

        # Simple check - if we can import and it's configured, it's healthy
        return {
            "status": "healthy",
            "middleware": "active"
        }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }


async def _check_application_metrics() -> Dict[str, Any]:
    """Check application metrics collection health."""
    try:
        # Generate a small metrics sample to verify the system works
        metrics_sample = metrics.get_metrics()

        # Count number of metrics
        metric_count = len([line for line in metrics_sample.split('\n')
                           if line and not line.startswith('#')])

        return {
            "status": "healthy",
            "metrics_count": metric_count,
            "collection": "active"
        }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }


@router.get("/health/liveness")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    Simple check to determine if the application is running.
    """
    try:
        metrics.record_feature_usage("liveness_check", "system")
        return {"status": "alive", "timestamp": datetime.now()}
    except Exception as e:
        logger.error(f"Liveness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Application not alive")


@router.get("/health/readiness")
async def readiness_probe(session: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.
    Checks if the application is ready to serve traffic.
    """
    try:
        # Quick database check
        await session.execute(text("SELECT 1"))

        metrics.record_feature_usage("readiness_check", "system")
        return {"status": "ready", "timestamp": datetime.now()}

    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        metrics.record_database_query("readiness_check", 0, "system", "connection_failed")
        raise HTTPException(status_code=503, detail="Application not ready")


@router.get("/health/startup")
async def startup_probe():
    """
    Kubernetes startup probe endpoint.
    Checks if the application has started successfully.
    """
    try:
        # Check that critical components are initialized
        from app.features.core.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()

        # Verify secrets are accessible
        await secrets_manager.get_secret("JWT_SECRET_KEY")

        metrics.record_feature_usage("startup_check", "system")
        return {"status": "started", "timestamp": datetime.now()}

    except Exception as e:
        logger.error(f"Startup probe failed: {e}")
        raise HTTPException(status_code=503, detail="Application startup incomplete")
