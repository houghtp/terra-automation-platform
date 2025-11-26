"""
GA4 credential loader that uses the shared OAuth client settings and Secrets Management.

This keeps the client secret out of environment variables and pulls it from the
global tenant's secrets store, mirroring how OpenAI/Firecrawl credentials are handled.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.config import get_settings
from app.features.administration.secrets.services import SecretsManagementService


# Keep secret naming consistent with other slices (e.g., "OpenAI API Key").
# Accept the current naming ("GA4 Client Secret") and fall back to the older suggestion ("GA4 Client Key").
GA4_SECRET_NAMES = ("GA4 Client Secret", "GA4 Client Key")


async def load_ga4_credentials(
    db_session: AsyncSession,
    accessed_by_user=None,
) -> dict:
    """
    Load GA4 OAuth credentials.

    - client_id and redirect_uri come from app settings (env-backed)
    - client_secret is fetched from Secrets Management (tenant_id="global")
    """
    settings = get_settings()

    if not settings.GA4_CLIENT_ID:
        raise ValueError("GA4_CLIENT_ID is not configured")
    if not settings.GA4_REDIRECT_URI:
        raise ValueError("GA4_REDIRECT_URI is not configured")

    secrets_service = SecretsManagementService(db_session, tenant_id="global")
    secret_meta = None
    for name in GA4_SECRET_NAMES:
        secret_meta = await secrets_service.get_secret_by_name(name)
        if secret_meta:
            break

    if not secret_meta:
        raise ValueError(f"GA4 client secret not found in Secrets Management (tried: {', '.join(GA4_SECRET_NAMES)})")

    secret_value = await secrets_service.get_secret_value(
        secret_id=secret_meta.id,
        accessed_by_user=accessed_by_user,
    )
    if not secret_value or not secret_value.value:
        raise ValueError("Unable to retrieve GA4 client secret value from Secrets Management")

    return {
        "client_id": settings.GA4_CLIENT_ID,
        "client_secret": secret_value.value,
        "redirect_uri": settings.GA4_REDIRECT_URI,
    }
