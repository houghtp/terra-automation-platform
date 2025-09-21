from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class ProviderAdapter(ABC):
    """Abstract provider adapter.

    Implementations should provide authorize_url, exchange_code, and resource discovery methods.
    """

    @abstractmethod
    def authorize_url(self, tenant_id: str, state: str) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    async def list_mailboxes(self, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError()
