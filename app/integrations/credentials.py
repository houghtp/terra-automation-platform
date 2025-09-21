from __future__ import annotations

from typing import Dict, Optional, Any
from abc import ABC, abstractmethod


class CredentialsStore(ABC):
    """Abstract credentials store interface.

    Implementations should securely persist provider credentials per tenant.
    """

    @abstractmethod
    async def save_credentials(self, tenant_id: str, provider: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_credentials(self, tenant_id: str, provider: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    @abstractmethod
    async def delete_credentials(self, tenant_id: str, provider: str) -> None:
        raise NotImplementedError()


class InMemoryCredentialsStore(CredentialsStore):
    """A simple in-memory credentials store for local development and tests.

    NOTE: This stores secrets in memory and is NOT secure. Replace with a
    KMS-backed DB encryption or Vault in production.
    """

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}

    async def save_credentials(self, tenant_id: str, provider: str, data: Dict[str, Any]) -> None:
        self._data.setdefault(tenant_id, {})[provider] = data

    async def get_credentials(self, tenant_id: str, provider: str) -> Optional[Dict[str, Any]]:
        return self._data.get(tenant_id, {}).get(provider)

    async def delete_credentials(self, tenant_id: str, provider: str) -> None:
        if tenant_id in self._data and provider in self._data[tenant_id]:
            del self._data[tenant_id][provider]
