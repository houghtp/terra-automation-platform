"""
Secrets management helper for Sales Outreach Prep.

Retrieves API keys from the platform's secrets management system.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.sqlalchemy_imports import get_logger
from app.features.administration.secrets.services import SecretsManagementService

logger = get_logger(__name__)


async def get_firecrawl_api_key(
    db: AsyncSession,
    tenant_id: str,
    current_user=None
) -> Optional[str]:
    """
    Fetch Firecrawl API key from Secrets Management.

    Args:
        db: Database session
        tenant_id: Tenant ID
        current_user: Current user (for audit trail)

    Returns:
        API key string or None if not configured
    """
    try:
        secrets_service = SecretsManagementService(db, tenant_id)
        secret = await secrets_service.get_secret_by_name("Firecrawl API Key")

        if not secret:
            logger.warning("Firecrawl API key not configured in secrets management")
            return None

        secret_value = await secrets_service.get_secret_value(
            secret_id=secret.id,
            accessed_by_user=current_user
        )

        if not secret_value:
            logger.error("Failed to retrieve Firecrawl API key value")
            return None

        return secret_value.value

    except Exception as e:
        logger.error("Error retrieving Firecrawl API key", error=str(e))
        return None


async def get_hunter_api_key(
    db: AsyncSession,
    tenant_id: str,
    current_user=None
) -> Optional[str]:
    """
    Fetch Hunter.io API key from Secrets Management.

    Args:
        db: Database session
        tenant_id: Tenant ID
        current_user: Current user (for audit trail)

    Returns:
        API key string or None if not configured
    """
    try:
        secrets_service = SecretsManagementService(db, tenant_id)
        secret = await secrets_service.get_secret_by_name("Hunter.io API Key")

        if not secret:
            logger.warning("Hunter.io API key not configured in secrets management")
            return None

        secret_value = await secrets_service.get_secret_value(
            secret_id=secret.id,
            accessed_by_user=current_user
        )

        if not secret_value:
            logger.error("Failed to retrieve Hunter.io API key value")
            return None

        return secret_value.value

    except Exception as e:
        logger.error("Error retrieving Hunter.io API key", error=str(e))
        return None


async def get_openai_api_key(
    db: AsyncSession,
    tenant_id: str,
    current_user=None
) -> Optional[str]:
    """
    Fetch OpenAI API key from Secrets Management.

    Args:
        db: Database session
        tenant_id: Tenant ID
        current_user: Current user (for audit trail)

    Returns:
        API key string or None if not configured
    """
    try:
        secrets_service = SecretsManagementService(db, tenant_id)
        secret = await secrets_service.get_secret_by_name("OpenAI API Key")

        if not secret:
            logger.warning("OpenAI API key not configured in secrets management")
            return None

        secret_value = await secrets_service.get_secret_value(
            secret_id=secret.id,
            accessed_by_user=current_user
        )

        if not secret_value:
            logger.error("Failed to retrieve OpenAI API key value")
            return None

        return secret_value.value

    except Exception as e:
        logger.error("Error retrieving OpenAI API key", error=str(e))
        return None
