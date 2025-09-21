from typing import List, Dict, Any

from app.integrations.base import ProviderAdapter
from app.integrations.credentials import CredentialsStore


async def discover_mailboxes(tenant_id: str, provider: str, adapter: ProviderAdapter, store: CredentialsStore) -> List[Dict[str, Any]]:
    """Discover mailboxes for a tenant using the provided adapter and credentials store.

    Returns a list of mailbox dicts. Implementations should persist into a DB-backed
    Resource model; this helper returns the discovered list for demo purposes.
    """
    creds = await store.get_credentials(tenant_id, provider)
    if not creds:
        raise RuntimeError("No credentials for tenant/provider")

    mailboxes = await adapter.list_mailboxes(creds)
    # In a real app: persist each mailbox with tenant_id, provider, external_id, metadata
    return mailboxes
