import asyncio

from app.integrations.credentials import InMemoryCredentialsStore
from app.integrations.m365_stub import M365StubAdapter
from app.integrations.gmail_stub import GmailStubAdapter
from app.integrations.discovery import discover_mailboxes


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_discover_mailboxes_m365():
    store = InMemoryCredentialsStore()
    adapter = M365StubAdapter()
    tenant = "tenant-example"
    # save fake credentials
    run(store.save_credentials(tenant, "m365", {"domain": "example.com"}))
    mailboxes = run(discover_mailboxes(tenant, "m365", adapter, store))
    assert any(m.get("email", "").endswith("@example.com") for m in mailboxes)


def test_discover_mailboxes_gmail():
    store = InMemoryCredentialsStore()
    adapter = GmailStubAdapter()
    tenant = "tenant-example"
    run(store.save_credentials(tenant, "gmail", {"domain": "example.com"}))
    mailboxes = run(discover_mailboxes(tenant, "gmail", adapter, store))
    assert any(m.get("email", "").endswith("@example.com") for m in mailboxes)
