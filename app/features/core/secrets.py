"""
Production-ready secrets management for FastAPI applications.
Supports multiple backends: .env files (dev), AWS Secrets Manager, Azure Key Vault, HashiCorp Vault.
"""
import os
import json
import structlog
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class SecretsBackend(Enum):
    """Supported secrets management backends."""
    ENV_FILE = "env_file"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    HASHICORP_VAULT = "hashicorp_vault"


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    name: str
    description: str
    required: bool = True
    default: Optional[str] = None
    environment_specific: bool = True


class SecretsProvider(ABC):
    """Abstract base class for secrets providers."""

    @abstractmethod
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a single secret value."""
        pass

    @abstractmethod
    async def get_secrets(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets at once."""
        pass

    @abstractmethod
    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set a secret value (if supported)."""
        pass

    @abstractmethod
    async def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret (if supported)."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the secrets provider is accessible."""
        pass


class EnvFileSecretsProvider(SecretsProvider):
    """Secrets provider that reads from .env files (development only)."""

    def __init__(self, env_file_path: str = ".env"):
        self.env_file_path = env_file_path
        self._load_env_file()

    def _load_env_file(self):
        """Load environment variables from .env file."""
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_file_path)
            logger.info(f"Loaded secrets from {self.env_file_path}")
        except ImportError:
            logger.warning("python-dotenv not installed, using system environment only")
        except Exception as e:
            logger.error(f"Failed to load .env file: {e}")

    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variables."""
        return os.getenv(secret_name)

    async def get_secrets(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from environment variables."""
        return {name: os.getenv(name) for name in secret_names}

    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set environment variable (runtime only)."""
        os.environ[secret_name] = secret_value
        return True

    async def delete_secret(self, secret_name: str) -> bool:
        """Remove environment variable."""
        if secret_name in os.environ:
            del os.environ[secret_name]
            return True
        return False

    def health_check(self) -> bool:
        """Always healthy for env file provider."""
        return True


class AWSSecretsManagerProvider(SecretsProvider):
    """AWS Secrets Manager provider."""

    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self._client = None

    def _get_client(self):
        """Lazy initialization of AWS client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client('secretsmanager', region_name=self.region_name)
            except ImportError:
                raise ImportError("boto3 is required for AWS Secrets Manager")
        return self._client

    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            client = self._get_client()
            response = client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name} from AWS: {e}")
            return None

    async def get_secrets(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from AWS Secrets Manager."""
        results = {}
        for name in secret_names:
            results[name] = await self.get_secret(name)
        return results

    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create or update secret in AWS Secrets Manager."""
        try:
            client = self._get_client()
            try:
                client.create_secret(Name=secret_name, SecretString=secret_value)
            except client.exceptions.ResourceExistsException:
                client.update_secret(SecretId=secret_name, SecretString=secret_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {secret_name} in AWS: {e}")
            return False

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from AWS Secrets Manager."""
        try:
            client = self._get_client()
            client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name} from AWS: {e}")
            return False

    def health_check(self) -> bool:
        """Check AWS Secrets Manager connectivity."""
        try:
            client = self._get_client()
            client.list_secrets(MaxResults=1)
            return True
        except Exception as e:
            logger.error(f"AWS Secrets Manager health check failed: {e}")
            return False


class AzureKeyVaultProvider(SecretsProvider):
    """Azure Key Vault provider."""

    def __init__(self, vault_url: str):
        self.vault_url = vault_url
        self._client = None

    def _get_client(self):
        """Lazy initialization of Azure client."""
        if self._client is None:
            try:
                from azure.keyvault.secrets import SecretClient
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
                self._client = SecretClient(vault_url=self.vault_url, credential=credential)
            except ImportError:
                raise ImportError("azure-keyvault-secrets and azure-identity are required for Azure Key Vault")
        return self._client

    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault."""
        try:
            client = self._get_client()
            secret = client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name} from Azure: {e}")
            return None

    async def get_secrets(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple secrets from Azure Key Vault."""
        results = {}
        for name in secret_names:
            results[name] = await self.get_secret(name)
        return results

    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Azure Key Vault."""
        try:
            client = self._get_client()
            client.set_secret(secret_name, secret_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {secret_name} in Azure: {e}")
            return False

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from Azure Key Vault."""
        try:
            client = self._get_client()
            client.begin_delete_secret(secret_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name} from Azure: {e}")
            return False

    def health_check(self) -> bool:
        """Check Azure Key Vault connectivity."""
        try:
            client = self._get_client()
            list(client.list_properties_of_secrets(max_page_size=1))
            return True
        except Exception as e:
            logger.error(f"Azure Key Vault health check failed: {e}")
            return False


# Registry of all secret definitions
SECRETS_REGISTRY: Dict[str, SecretMetadata] = {
    # Database
    "DATABASE_URL": SecretMetadata(
        name="DATABASE_URL",
        description="Database connection string",
        required=True
    ),

    # JWT Authentication
    "JWT_SECRET_KEY": SecretMetadata(
        name="JWT_SECRET_KEY",
        description="JWT signing key (256+ bits)",
        required=True
    ),
    "SECRET_KEY": SecretMetadata(
        name="SECRET_KEY",
        description="Application secret key",
        required=True
    ),

    # API Keys
    "OPENAI_API_KEY": SecretMetadata(
        name="OPENAI_API_KEY",
        description="OpenAI API key for GPT services",
        required=False
    ),
    "FIRECRAWL_API_KEY": SecretMetadata(
        name="FIRECRAWL_API_KEY",
        description="Firecrawl API key for web scraping",
        required=False
    ),
    "HUNTER_API_KEY": SecretMetadata(
        name="HUNTER_API_KEY",
        description="Hunter.io API key for email finding",
        required=False
    ),

    # Email Services
    "EMAIL_HOST": SecretMetadata(
        name="EMAIL_HOST",
        description="SMTP server hostname",
        required=False,
        default="smtp.gmail.com"
    ),
    "EMAIL_PASSWORD": SecretMetadata(
        name="EMAIL_PASSWORD",
        description="SMTP server password",
        required=False
    ),

    # Monitoring
    "SENTRY_DSN": SecretMetadata(
        name="SENTRY_DSN",
        description="Sentry error tracking DSN",
        required=False
    ),

    # Global Admin Bootstrap
    "GLOBAL_ADMIN_EMAIL": SecretMetadata(
        name="GLOBAL_ADMIN_EMAIL",
        description="Global administrator email address",
        required=False,
        default="admin@system.local"
    ),
    "GLOBAL_ADMIN_PASSWORD": SecretMetadata(
        name="GLOBAL_ADMIN_PASSWORD",
        description="Global administrator password (will auto-generate if not set)",
        required=False
    ),
    "GLOBAL_ADMIN_NAME": SecretMetadata(
        name="GLOBAL_ADMIN_NAME",
        description="Global administrator display name",
        required=False,
        default="System Administrator"
    ),
}
