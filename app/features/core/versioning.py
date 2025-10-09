"""
API versioning system for enterprise SaaS platform.

Provides robust API versioning with deprecation, compatibility, and migration support.
"""
import structlog
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class VersionStatus(Enum):
    """API version status types."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    EXPERIMENTAL = "experimental"


@dataclass
class VersionInfo:
    """Information about an API version."""
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    description: str = ""
    changelog_url: Optional[str] = None
    migration_guide_url: Optional[str] = None


class APIVersionManager:
    """
    Manages API versions, compatibility, and deprecation.

    Features:
    - URL path versioning (/api/v1/, /api/v2/)
    - Version negotiation via headers
    - Deprecation warnings
    - Sunset notifications
    - Version compatibility matrix
    """

    def __init__(self):
        self.versions: Dict[str, VersionInfo] = {}
        self.default_version = "v1"
        self.supported_versions = set()
        self.compatibility_matrix: Dict[str, List[str]] = {}

    def register_version(
        self,
        version: str,
        status: VersionStatus,
        release_date: datetime,
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None,
        description: str = "",
        changelog_url: Optional[str] = None,
        migration_guide_url: Optional[str] = None
    ):
        """Register a new API version."""

        version_info = VersionInfo(
            version=version,
            status=status,
            release_date=release_date,
            deprecation_date=deprecation_date,
            sunset_date=sunset_date,
            description=description,
            changelog_url=changelog_url,
            migration_guide_url=migration_guide_url
        )

        self.versions[version] = version_info

        if status in [VersionStatus.ACTIVE, VersionStatus.DEPRECATED]:
            self.supported_versions.add(version)

        logger.info(f"Registered API version {version} with status {status.value}")

    def set_compatibility(self, version: str, compatible_with: List[str]):
        """Set version compatibility matrix."""
        self.compatibility_matrix[version] = compatible_with

    def get_version_info(self, version: str) -> Optional[VersionInfo]:
        """Get information about a specific version."""
        return self.versions.get(version)

    def is_version_supported(self, version: str) -> bool:
        """Check if a version is currently supported."""
        return version in self.supported_versions

    def get_all_versions(self) -> Dict[str, VersionInfo]:
        """Get all registered versions."""
        return self.versions.copy()

    def get_active_versions(self) -> Dict[str, VersionInfo]:
        """Get only active (non-deprecated, non-sunset) versions."""
        return {
            v: info for v, info in self.versions.items()
            if info.status == VersionStatus.ACTIVE
        }

    def get_deprecated_versions(self) -> Dict[str, VersionInfo]:
        """Get deprecated versions."""
        return {
            v: info for v, info in self.versions.items()
            if info.status == VersionStatus.DEPRECATED
        }

    def check_deprecation_warnings(self, version: str) -> Optional[Dict[str, Any]]:
        """Check if version needs deprecation warning."""
        version_info = self.get_version_info(version)
        if not version_info:
            return None

        if version_info.status == VersionStatus.DEPRECATED:
            warning = {
                "warning": "deprecated",
                "message": f"API version {version} is deprecated",
                "deprecation_date": version_info.deprecation_date.isoformat() if version_info.deprecation_date else None,
                "sunset_date": version_info.sunset_date.isoformat() if version_info.sunset_date else None
            }

            if version_info.migration_guide_url:
                warning["migration_guide"] = version_info.migration_guide_url

            return warning

        # Check if approaching deprecation
        if version_info.deprecation_date:
            days_until_deprecation = (version_info.deprecation_date - datetime.now(timezone.utc)).days
            if 0 < days_until_deprecation <= 90:  # 90 days warning
                return {
                    "warning": "approaching_deprecation",
                    "message": f"API version {version} will be deprecated in {days_until_deprecation} days",
                    "deprecation_date": version_info.deprecation_date.isoformat()
                }

        return None


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning logic.

    Features:
    - Extract version from URL path or headers
    - Add deprecation warnings to responses
    - Handle version negotiation
    - Block access to sunset versions
    """

    def __init__(self, app, version_manager: APIVersionManager):
        super().__init__(app)
        self.version_manager = version_manager

    async def dispatch(self, request: Request, call_next):
        """Process request with version handling."""

        # Extract version from URL path
        path_version = self._extract_version_from_path(request.url.path)

        # Extract version from headers
        header_version = self._extract_version_from_headers(request)

        # Determine effective version
        version = path_version or header_version or self.version_manager.default_version

        # Check for version warnings
        version_warning = None

        # Check for version mismatch (header vs URL)
        if path_version and header_version and path_version != header_version:
            version_warning = f"Version mismatch: URL specifies {path_version}, header specifies {header_version}"
            # Use URL version as primary
            version = path_version

        # Check for unsupported version request
        elif header_version and not self.version_manager.is_version_supported(header_version):
            version_warning = f"Unsupported version {header_version} requested, using default {self.version_manager.default_version}"
            version = self.version_manager.default_version

        # Store version in request state
        request.state.api_version = version

        # Check for sunset versions (only block if the effective version is sunset)
        version_info = self.version_manager.get_version_info(version)
        if version_info and version_info.status == VersionStatus.SUNSET:
            return JSONResponse(
                status_code=status.HTTP_410_GONE,
                content={
                    "error": "version_sunset",
                    "message": f"API version {version} has been sunset and is no longer available",
                    "sunset_date": version_info.sunset_date.isoformat() if version_info.sunset_date else None,
                    "migration_guide": version_info.migration_guide_url
                }
            )

        # Process request
        response = await call_next(request)

        # Add version headers to response
        response.headers["X-API-Version"] = version
        response.headers["X-API-Supported-Versions"] = ",".join(self.version_manager.supported_versions)

        # Add version warning header if needed
        if version_warning:
            response.headers["X-API-Version-Warning"] = version_warning

        # Add deprecation warnings
        deprecation_warning = self.version_manager.check_deprecation_warnings(version)
        if deprecation_warning:
            response.headers["X-API-Deprecation-Warning"] = deprecation_warning["warning"]
            response.headers["X-API-Deprecation-Message"] = deprecation_warning["message"]

            if "sunset_date" in deprecation_warning:
                response.headers["X-API-Sunset-Date"] = deprecation_warning["sunset_date"]

        return response

    def _extract_version_from_path(self, path: str) -> Optional[str]:
        """Extract version from URL path like /api/v1/users."""
        parts = path.strip("/").split("/")

        # Look for /api/vX/ pattern
        for i, part in enumerate(parts):
            if part == "api" and i + 1 < len(parts):
                next_part = parts[i + 1]
                if next_part.startswith("v") and next_part[1:].isdigit():
                    return next_part
                # Handle semantic versioning like v1.2
                if next_part.startswith("v") and "." in next_part:
                    return next_part

        return None

    def _extract_version_from_headers(self, request: Request) -> Optional[str]:
        """Extract version from headers."""

        # Check X-API-Version header (matching test expectations)
        version = request.headers.get("X-API-Version")
        if version:
            return f"v{version}" if not version.startswith("v") else version

        # Check API-Version header
        version = request.headers.get("API-Version")
        if version:
            return f"v{version}" if not version.startswith("v") else version

        # Check Accept header with versioning
        accept = request.headers.get("Accept", "")
        if "version=" in accept:
            # Parse application/json; version=1
            for part in accept.split(";"):
                if "version=" in part:
                    version_num = part.split("version=")[1].strip()
                    return f"v{version_num}"

        return None


def create_versioned_app() -> FastAPI:
    """Create FastAPI app with versioning support."""

    app = FastAPI(
        title="Enterprise SaaS API",
        description="Multi-versioned API for enterprise SaaS platform",
        version="1.0.0",
        docs_url=None,  # Disable default docs, create versioned ones
        redoc_url=None
    )

    return app


def setup_version_docs(app: FastAPI, version_manager: APIVersionManager):
    """Setup versioned documentation endpoints."""

    @app.get("/api/versions", tags=["versioning"])
    async def get_api_versions():
        """Get information about all API versions."""
        versions = {}

        for version, info in version_manager.get_all_versions().items():
            versions[version] = {
                "version": info.version,
                "status": info.status.value,
                "release_date": info.release_date.isoformat(),
                "deprecation_date": info.deprecation_date.isoformat() if info.deprecation_date else None,
                "sunset_date": info.sunset_date.isoformat() if info.sunset_date else None,
                "description": info.description,
                "changelog_url": info.changelog_url,
                "migration_guide_url": info.migration_guide_url
            }

        return {
            "versions": versions,
            "default_version": version_manager.default_version,
            "supported_versions": list(version_manager.supported_versions)
        }

    @app.get("/api/{version}/docs", include_in_schema=False)
    async def get_versioned_docs(version: str):
        """Get Swagger docs for specific version."""
        from fastapi.openapi.docs import get_swagger_ui_html

        if not version_manager.is_version_supported(version):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documentation for version {version} not found"
            )

        return get_swagger_ui_html(
            openapi_url=f"/api/{version}/openapi.json",
            title=f"API Documentation - {version}",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
        )

    @app.get("/api/{version}/openapi.json", include_in_schema=False)
    async def get_versioned_openapi(version: str):
        """Get OpenAPI schema for specific version."""
        if not version_manager.is_version_supported(version):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OpenAPI schema for version {version} not found"
            )

        # Return version-specific OpenAPI schema
        # This would be customized based on the version
        return app.openapi()


# Global version manager instance
api_version_manager = APIVersionManager()

# Register initial versions
api_version_manager.register_version(
    version="v1",
    status=VersionStatus.ACTIVE,
    release_date=datetime(2024, 1, 1),
    description="Initial API version with core functionality"
)

# Example future version
api_version_manager.register_version(
    version="v2",
    status=VersionStatus.EXPERIMENTAL,
    release_date=datetime(2024, 6, 1),
    description="Enhanced API with additional features and improved responses"
)

# Set compatibility
api_version_manager.set_compatibility("v2", ["v1"])  # v2 is backwards compatible with v1