

"""
Main application entry point for TerraAutomationPlatform.
"""
import os
import logging
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import RequestValidationError as FastAPIRequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .features.core.logging import setup_logging
from .features.core.database import engine, Base, get_db
from .features.core.templates import templates
from .features.core.secrets_manager import get_secrets_manager
from .features.core.bootstrap import global_admin_bootstrap
from .features.auth.routes import router as auth_router
from .features.core.log_viewer import router as log_viewer_router
from .features.administration.logs.routes import router as admin_logs_router
from .features.administration.logs.models import ApplicationLog  # Ensure model is imported for table creation
from .features.auth.models import PasswordResetToken  # Ensure password reset model is imported for table creation
from .features.core.config import get_settings
from .features.core.security import SecureHeadersMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application lifespan events."""
    # Startup logic
    logging.info("Starting FastAPI application")

    # Validate secrets and perform startup checks
    secrets_manager = get_secrets_manager()

    # Check secrets provider health
    if not secrets_manager.health_check():
        logging.error("Secrets provider health check failed!")
        # In production, you might want to raise an exception here

    # Validate all required secrets
    validation_results = await secrets_manager.validate_all_required_secrets()
    missing_secrets = [name for name, available in validation_results.items() if not available]

    if missing_secrets:
        logging.error(f"Missing required secrets: {missing_secrets}")
        # In production, you might want to raise an exception here
    else:
        logging.info("All required secrets are available")

    # Log secrets backend being used (without exposing values)
    logging.info(f"Using secrets backend: {secrets_manager.backend.value}")

    # Database tables are managed by Alembic migrations
    # Run: alembic upgrade head
    # Note: Base.metadata.create_all() is disabled to avoid conflicts with Alembic

    # Bootstrap global admin system
    async for db_session in get_db():
        try:
            bootstrap_success = await global_admin_bootstrap.ensure_global_admin_exists(db_session)
            if bootstrap_success:
                logging.info("✅ Global admin system validated")
            else:
                logging.error("❌ Failed to initialize global admin system")
            break  # Only need one iteration
        except Exception as e:
            logging.error(f"❌ Global admin bootstrap error: {e}")

    logging.info("✅ Application startup completed")

    yield  # Application runs here

    # Shutdown logic
    logging.info("Shutting down FastAPI application")


app = FastAPI(
    title="TerraAutomationPlatform",
    description="Vertical slice FastAPI template.",
    lifespan=lifespan
)
setup_logging()

# Note: Startup events have been moved to lifespan context manager
# This validation is now handled during application startup

# Add session middleware first (required for tenant switching)
from starlette.middleware.sessions import SessionMiddleware
import secrets
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", secrets.token_urlsafe(32))
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# Add request id and tenant middleware early
from .middleware.request_id import RequestIDMiddleware
from .middleware.tenant import TenantMiddleware
from .middleware.rate_limiting import RateLimitMiddleware
from .middleware.metrics import MetricsMiddleware

# Add API versioning middleware (must run early)
from .features.core.versioning import VersioningMiddleware, api_version_manager, setup_version_docs
app.add_middleware(VersioningMiddleware, version_manager=api_version_manager)

# Tenant middleware must run before auth/audit so context vars are populated
app.add_middleware(TenantMiddleware)

# Add API security middleware (must run first after tenant context resolves)
from .features.core.api_security import APISecurityMiddleware
app.add_middleware(APISecurityMiddleware)

# Add authentication context middleware (sets request.state.user_id, tenant_id, etc.)
from .middleware.auth_context import AuthContextMiddleware
app.add_middleware(AuthContextMiddleware)

# Add audit logging middleware (reads request.state set by auth context)
from .features.administration.audit.middleware import AuditLoggingMiddleware
app.add_middleware(AuditLoggingMiddleware)

app.add_middleware(RequestIDMiddleware)

# Add rate limiting middleware - TEMPORARILY DISABLED due to greenlet async context error
# TODO: Fix rate limiting to work with async SQLAlchemy properly
# app.add_middleware(RateLimitMiddleware)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Request logging middleware (register after app is defined)
import time
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logging.info({
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time, 2)
        })
        return response

app.add_middleware(RequestLoggingMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGINS] if settings.CORS_ORIGINS != '*' else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secure headers
app.add_middleware(SecureHeadersMiddleware)

# Serve local static assets at /static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount core static files
app.mount("/features/core/static", StaticFiles(directory="app/features/core/static"), name="core_static")


# Auth static directory removed - no longer needed

# Mount dashboard static files
app.mount("/dashboard/static", StaticFiles(directory="app/features/dashboard/static"), name="dashboard_static")

# Administration static directory removed - no longer needed

# Mount administration users static files
app.mount("/features/administration/users/static", StaticFiles(directory="app/features/administration/users/static"), name="administration_users_static")

# Mount tenants static files
app.mount("/features/administration/tenants/static", StaticFiles(directory="app/features/administration/tenants/static"), name="tenants_static")

# Mount audit static files
app.mount("/features/administration/audit/static", StaticFiles(directory="app/features/administration/audit/static"), name="audit_static")

# Mount logs static files
app.mount("/features/administration/logs/static", StaticFiles(directory="app/features/administration/logs/static"), name="logs_static")

# Mount secrets static files
app.mount("/features/administration/secrets/static", StaticFiles(directory="app/features/administration/secrets/static"), name="secrets_static")

# Mount SMTP static files
app.mount("/features/administration/smtp/static", StaticFiles(directory="app/features/administration/smtp/static"), name="smtp_static")

# Mount AI prompts static files
app.mount("/features/administration/ai_prompts/static", StaticFiles(directory="app/features/administration/ai_prompts/static"), name="ai_prompts_static")

# Mount content broadcaster static files
app.mount("/features/content-broadcaster/static", StaticFiles(directory="app/features/business_automations/content_broadcaster/static"), name="content_broadcaster_static")
app.mount("/features/business-automations/sales-outreach-prep/static", StaticFiles(directory="app/features/business_automations/sales_outreach_prep/static"), name="sales_outreach_prep_static")
app.mount("/features/community/static", StaticFiles(directory="app/features/community/static"), name="community_static")
app.mount("/features/connectors/static", StaticFiles(directory="app/features/connectors/connectors/static"), name="connectors_static")

# Mount MSP CSPM static files
app.mount("/features/msp/cspm/static", StaticFiles(directory="app/features/msp/cspm/static"), name="cspm_static")


# Setup versioned API documentation
setup_version_docs(app, api_version_manager)

# Include versioned API routers
from .api.v1.router import v1_router
app.include_router(v1_router)

# Include legacy routers (for backwards compatibility - can be removed later)
app.include_router(auth_router, prefix="/auth")

# User management moved to administration slice

app.include_router(log_viewer_router)

# Include dashboard router
from .features.dashboard.routes import router as dashboard_router
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# Include monitoring routes
from .features.monitoring.routes import router as monitoring_router
app.include_router(monitoring_router, tags=["monitoring"])

# Include administration routes
from .features.administration.secrets.routes.crud_routes import router as administration_secrets_crud_router
from .features.administration.secrets.routes.form_routes import router as administration_secrets_form_router
from .features.administration.audit.routes import router as administration_audit_router
from .features.administration.tenants.routes import router as administration_tenants_router
from .features.administration.users.routes import router as administration_users_router
from .features.administration.tasks.routes import router as administration_tasks_router
from .features.administration.api_keys.routes import router as administration_api_keys_router
from .features.administration.smtp.routes import router as administration_smtp_router
from .features.administration.ai_prompts.routes import router as administration_ai_prompts_router

# Include business automation routes
from .features.business_automations.content_broadcaster.routes import router as content_broadcaster_router
from .features.business_automations.marketing_intellegence_hub.routes import router as marketing_intelligence_router
from .features.business_automations.sales_outreach_prep.routes import router as sales_outreach_prep_router
from .features.community.routes import router as community_router
from .features.connectors.connectors.routes import router as connectors_router

# Include MSP routes
from .features.msp.cspm.routes import cspm_router

app.include_router(administration_secrets_crud_router, prefix="/features/administration/secrets", tags=["administration"])
app.include_router(administration_secrets_form_router, prefix="/features/administration/secrets", tags=["administration"])
app.include_router(administration_audit_router, prefix="/features/administration/audit", tags=["administration"])
app.include_router(administration_tenants_router, prefix="/features/administration/tenants", tags=["administration"])
app.include_router(administration_users_router, prefix="/features/administration/users", tags=["administration"])
app.include_router(administration_tasks_router, prefix="/features/administration/tasks", tags=["tasks"])
app.include_router(administration_api_keys_router, prefix="/features/administration/api-keys", tags=["administration"])
app.include_router(administration_smtp_router, prefix="/features/administration/smtp", tags=["administration"])
app.include_router(administration_ai_prompts_router, prefix="/features/administration/ai-prompts", tags=["administration"])
app.include_router(admin_logs_router, prefix="/features/administration/logs", tags=["administration"])

# Business automation routes
app.include_router(content_broadcaster_router, prefix="/features/content-broadcaster", tags=["business-automations"])
app.include_router(marketing_intelligence_router, prefix="/features/marketing-intelligence", tags=["business-automations"])
app.include_router(sales_outreach_prep_router, tags=["business-automations"])

# Community routes
app.include_router(community_router, prefix="/features/community", tags=["community"])

# Connectors routes
app.include_router(connectors_router, prefix="/features/connectors", tags=["connectors"])

# MSP CSPM routes
app.include_router(cspm_router, tags=["msp"])

# Old users routes moved to administration

# Root route with authentication check
@app.get("/", response_class=HTMLResponse, tags=["pages"])
async def root(request: Request):
    """Root page - redirect to login if not authenticated, otherwise to dashboard"""
    from fastapi.responses import RedirectResponse
    from app.features.auth.dependencies import get_optional_current_user
    from app.features.auth.models import User
    from typing import Optional

    # Try to get current user using the optional dependency manually
    try:
        # Check for JWT token in various places (Authorization header, cookies)
        authorization = request.headers.get("Authorization")
        access_token = request.cookies.get("access_token")

        if not authorization and not access_token:
            # No token found, redirect to login
            return RedirectResponse(url="/auth/login", status_code=302)

        # Simple token presence check - if we have any token, redirect to dashboard
        # Let the dashboard handle the detailed authentication
        if authorization or access_token:
            return RedirectResponse(url="/dashboard", status_code=302)
        else:
            return RedirectResponse(url="/auth/login", status_code=302)

    except Exception:
        # Any error, redirect to login
        return RedirectResponse(url="/auth/login", status_code=302)

# Health check endpoints
@app.get("/health", tags=["infra"])
async def health():
    """Basic health check for load balancers."""
    from datetime import datetime, timezone
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/health/db", tags=["infra"])
async def db_health():
    """Database connectivity health check."""
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logging.exception("DB health check failed")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.get("/health/detailed", tags=["infra"])
async def detailed_health():
    """Comprehensive health check for monitoring systems."""
    from datetime import datetime, timezone

    health_data = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",  # TODO: Get from package.json or version file
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    # Database check
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_data["database"] = {"status": "ok", "type": "postgresql"}
    except Exception as e:
        health_data["database"] = {"status": "error", "error": str(e)}
        health_data["status"] = "degraded"

    # System metrics (optional)
    try:
        import psutil
        health_data["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except ImportError:
        # psutil not available, skip system metrics
        pass

    return health_data

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    # For 401 Unauthorized on API endpoints, return JSON response
    if exc.status_code == 401:
        # Check if this is an API request
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        else:
            # For web requests, redirect to login page
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/auth/login", status_code=302)

    # For other HTTP exceptions, show error page
    return templates.TemplateResponse("error/404.html", {"request": request, "detail": exc.detail}, status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.error(
        "Request validation error on %s: %s",
        request.url.path,
        exc.errors()
    )
    return templates.TemplateResponse("error/422.html", {"request": request, "detail": exc.errors()}, status_code=422)

# Note: Database table creation moved to lifespan context manager
# This initialization is now handled during application startup





# For direct execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
