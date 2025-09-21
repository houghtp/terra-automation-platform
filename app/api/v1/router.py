"""
API v1 router aggregation.

Combines all slice routers into a versioned API structure.
"""
from fastapi import APIRouter, Depends, Request
from typing import Dict, Any

# Import existing slice routers
from app.features.auth.routes import router as auth_router
from app.features.administration.users.routes import router as users_router
from app.features.administration.tenants.routes import router as tenants_router
from app.features.administration.secrets.routes import router as secrets_router
from app.features.administration.audit.routes import router as audit_router
from app.features.administration.tasks.routes import router as tasks_router
from app.features.administration.api_keys.routes import router as api_keys_router
from app.features.dashboard.routes import router as dashboard_router
from app.features.monitoring.routes import router as monitoring_router
from app.api.webhooks.routes import router as webhooks_router

# Create main v1 router
v1_router = APIRouter(prefix="/api/v1", tags=["API v1"])

# Health check specific to v1
@v1_router.get("/health", tags=["health"])
async def api_v1_health():
    """Health check for API v1."""
    return {
        "status": "ok",
        "version": "v1",
        "api_version": "1.0.0",
        "features": [
            "authentication",
            "user_management",
            "tenant_management",
            "audit_logging",
            "background_tasks",
            "monitoring"
        ]
    }

@v1_router.get("/info", tags=["info"])
async def api_v1_info():
    """Get API v1 information and capabilities."""
    return {
        "version": "v1",
        "release_date": "2024-01-01",
        "status": "active",
        "description": "Core SaaS API with authentication, multi-tenancy, and administration",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/administration/users",
            "tenants": "/api/v1/administration/tenants",
            "secrets": "/api/v1/administration/secrets",
            "audit": "/api/v1/administration/audit",
            "tasks": "/api/v1/administration/tasks",
            "api_keys": "/api/v1/administration/api-keys",
            "dashboard": "/api/v1/dashboard",
            "monitoring": "/api/v1/monitoring",
            "webhooks": "/api/v1/webhooks"
        },
        "documentation": "/api/v1/docs"
    }

# Include slice routers with v1 prefix
# Auth router has no internal prefix, so we add /auth
v1_router.include_router(auth_router, prefix="/auth", tags=["auth-v1"])

# Administration routers already have /administration/[slice] prefix, so we include them directly
v1_router.include_router(users_router, prefix="", tags=["users-v1"])
v1_router.include_router(tenants_router, prefix="", tags=["tenants-v1"])
v1_router.include_router(secrets_router, prefix="", tags=["secrets-v1"])
v1_router.include_router(audit_router, prefix="", tags=["audit-v1"])
v1_router.include_router(tasks_router, prefix="", tags=["tasks-v1"])
v1_router.include_router(api_keys_router, prefix="", tags=["api-keys-v1"])

# Dashboard and monitoring routers have no internal prefix, so we add their prefix
v1_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard-v1"])
v1_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring-v1"])
v1_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks-v1"])
