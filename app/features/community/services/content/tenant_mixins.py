"""Shared helpers for content hub services."""

from typing import Any, Dict


class ContentTenantMixin:
    """Resolve tenant IDs for content hub operations."""

    def _resolve_tenant_id(self, payload: Dict[str, Any]) -> str:
        tenant_id = getattr(self, "tenant_id", None) or payload.get("tenant_id")
        if tenant_id in (None, "global"):
            raise ValueError("Tenant context is required for this operation.")
        return tenant_id
