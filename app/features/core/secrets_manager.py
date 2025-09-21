"""
Secrets Manager - High-level interface for managing application secrets.
"""
import os
import logging
from typing import Dict, Any, Optional, Type
from app.features.core.secrets import (
    SecretsProvider,
    SecretsBackend,
    EnvFileSecretsProvider,
    AWSSecretsManagerProvider,
    AzureKeyVaultProvider,
    SECRETS_REGISTRY,
    SecretMetadata
)

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    High-level secrets manager that handles multiple backends and provides
    a unified interface for accessing application secrets.
    """

    def __init__(self, backend: Optional[SecretsBackend] = None):
        self.backend = backend or self._detect_backend()
        self.provider = self._create_provider()
        self._secret_cache: Dict[str, str] = {}
        self._cache_enabled = os.getenv("SECRETS_CACHE_ENABLED", "true").lower() == "true"

        logger.info(f"Initialized SecretsManager with backend: {self.backend.value}")

    def _detect_backend(self) -> SecretsBackend:
        """Auto-detect the appropriate secrets backend based on environment."""
        # Check for explicit backend configuration
        backend_env = os.getenv("SECRETS_BACKEND", "").upper()
        if backend_env:
            try:
                return SecretsBackend[backend_env]
            except KeyError:
                logger.warning(f"Unknown secrets backend: {backend_env}, falling back to auto-detection")

        # Auto-detect based on environment
        environment = os.getenv("ENVIRONMENT", "development").lower()

        if environment == "production":
            # Check for cloud provider indicators
            if os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"):
                return SecretsBackend.AWS_SECRETS_MANAGER
            elif os.getenv("AZURE_SUBSCRIPTION_ID") or os.getenv("AZURE_CLIENT_ID"):
                return SecretsBackend.AZURE_KEY_VAULT
            else:
                logger.warning("Production environment detected but no cloud provider found, using env files")
                return SecretsBackend.ENV_FILE
        else:
            return SecretsBackend.ENV_FILE

    def _create_provider(self) -> SecretsProvider:
        """Create the appropriate secrets provider based on backend."""
        if self.backend == SecretsBackend.ENV_FILE:
            return EnvFileSecretsProvider()

        elif self.backend == SecretsBackend.AWS_SECRETS_MANAGER:
            region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
            return AWSSecretsManagerProvider(region_name=region)

        elif self.backend == SecretsBackend.AZURE_KEY_VAULT:
            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL is required for Azure Key Vault backend")
            return AzureKeyVaultProvider(vault_url=vault_url)

        else:
            raise ValueError(f"Unsupported secrets backend: {self.backend}")

    async def get_secret(self, secret_name: str, required: bool = True) -> Optional[str]:
        """
        Get a secret value by name.

        Args:
            secret_name: Name of the secret
            required: Whether this secret is required (raises exception if missing)

        Returns:
            Secret value or None if not found and not required

        Raises:
            ValueError: If required secret is not found
        """
        # Check cache first
        if self._cache_enabled and secret_name in self._secret_cache:
            return self._secret_cache[secret_name]

        # Get from provider
        value = await self.provider.get_secret(secret_name)

        # Handle missing required secrets
        if value is None and required:
            # Check if we have metadata with a default
            metadata = SECRETS_REGISTRY.get(secret_name)
            if metadata and metadata.default:
                value = metadata.default
                logger.info(f"Using default value for secret: {secret_name}")
            else:
                raise ValueError(f"Required secret '{secret_name}' not found")

        # Cache the value
        if value is not None and self._cache_enabled:
            self._secret_cache[secret_name] = value

        return value

    async def get_secrets(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets at once."""
        # Separate cached and non-cached secrets
        cached_secrets = {}
        uncached_names = []

        if self._cache_enabled:
            for name in secret_names:
                if name in self._secret_cache:
                    cached_secrets[name] = self._secret_cache[name]
                else:
                    uncached_names.append(name)
        else:
            uncached_names = secret_names

        # Get uncached secrets from provider
        uncached_secrets = await self.provider.get_secrets(uncached_names)

        # Update cache
        if self._cache_enabled:
            for name, value in uncached_secrets.items():
                if value is not None:
                    self._secret_cache[name] = value

        # Combine results
        return {**cached_secrets, **uncached_secrets}

    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set a secret value (if provider supports it)."""
        success = await self.provider.set_secret(secret_name, secret_value)

        # Update cache if successful
        if success and self._cache_enabled:
            self._secret_cache[secret_name] = secret_value

        return success

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret (if provider supports it)."""
        success = await self.provider.delete_secret(secret_name)

        # Remove from cache if successful
        if success and self._cache_enabled and secret_name in self._secret_cache:
            del self._secret_cache[secret_name]

        return success

    def clear_cache(self):
        """Clear the secrets cache."""
        self._secret_cache.clear()
        logger.info("Secrets cache cleared")

    def health_check(self) -> bool:
        """Check if the secrets provider is healthy."""
        return self.provider.health_check()

    async def validate_all_required_secrets(self) -> Dict[str, bool]:
        """
        Validate that all required secrets are available.

        Returns:
            Dictionary mapping secret names to availability status
        """
        required_secrets = {
            name: metadata
            for name, metadata in SECRETS_REGISTRY.items()
            if metadata.required
        }

        secret_names = list(required_secrets.keys())
        secret_values = await self.get_secrets(secret_names)

        validation_results = {}
        for name in secret_names:
            value = secret_values.get(name)
            is_available = value is not None and value != ""
            validation_results[name] = is_available

            if not is_available:
                logger.error(f"Required secret '{name}' is not available")

        return validation_results

    async def get_database_url(self) -> str:
        """Get database URL with fallback to PostgreSQL for development."""
        db_url = await self.get_secret("DATABASE_URL", required=False)
        if not db_url:
            # Default to PostgreSQL for development
            db_url = "postgresql+asyncpg://dev_user:dev_password@localhost:5434/fastapi_template_dev"
            logger.info("Using default PostgreSQL database for development")
        return db_url

    async def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration secrets."""
        jwt_secrets = await self.get_secrets([
            "JWT_SECRET_KEY",
            "JWT_ALGORITHM",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS"
        ])

        return {
            "secret_key": jwt_secrets["JWT_SECRET_KEY"] or "dev-secret-key-change-in-production",
            "algorithm": jwt_secrets["JWT_ALGORITHM"] or "HS256",
            "access_token_expire_minutes": int(jwt_secrets["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] or "30"),
            "refresh_token_expire_days": int(jwt_secrets["JWT_REFRESH_TOKEN_EXPIRE_DAYS"] or "7")
        }

    async def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get all API keys."""
        return await self.get_secrets([
            "OPENAI_API_KEY",
            "FIRECRAWL_API_KEY",
            "HUNTER_API_KEY"
        ])


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


async def get_secret(secret_name: str, required: bool = True) -> Optional[str]:
    """Convenience function to get a secret."""
    manager = get_secrets_manager()
    return await manager.get_secret(secret_name, required)


async def get_database_url() -> str:
    """Convenience function to get database URL."""
    manager = get_secrets_manager()
    return await manager.get_database_url()
