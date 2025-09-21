from typing import Optional

from fastapi import Request, Depends, HTTPException

from app.middleware.tenant import tenant_ctx_var


async def tenant_from_token_dependency(request: Request) -> Optional[str]:
    """
    Extract tenant from JWT token if available.
    This allows global admins with 'global' tenant to work properly.
    """
    from app.features.auth.dependencies import get_current_user_token
    from fastapi.security import HTTPBearer
    from fastapi import Depends

    # Try to get token data
    security = HTTPBearer(auto_error=False)
    credentials = await security(request)

    token_data = None
    if credentials:
        token_data = await get_current_user_token(request, credentials)
    else:
        # Try cookie fallback
        token_data = await get_current_user_token(request, None)

    if token_data:
        return token_data.tenant_id

    return None


def get_current_tenant() -> Optional[str]:
    """Return the tenant id from the request ContextVar (set by middleware).

    Returns None if no tenant is set.
    """
    return tenant_ctx_var.get(None)


async def tenant_dependency(
    request: Request, token_tenant: Optional[str] = Depends(tenant_from_token_dependency)
) -> str:
    """FastAPI dependency that resolves the current tenant.

    Precedence (production recommendation):
      1. tenant from verified token (token_tenant)
      2. X-Tenant-ID header
      3. tenant ContextVar (middleware)
      4. fallback: 'global' (for global admin access)

    If both token_tenant and header are present but disagree, raise 403.
    """
    header_tenant = request.headers.get("x-tenant-id")
    if token_tenant and header_tenant and token_tenant != header_tenant:
        raise HTTPException(
            status_code=403,
            detail="Tenant mismatch between auth token and X-Tenant-ID header",
        )

    tenant = token_tenant or header_tenant or get_current_tenant() or "global"
    return tenant
