import asyncio

from fastapi import HTTPException

from app.deps.tenant import tenant_dependency


class DummyRequest:
    def __init__(self, headers: dict):
        # case-insensitive lookup like starlette's headers
        self.headers = {k.lower(): v for k, v in headers.items()}


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_header_only_tenant():
    req = DummyRequest({"X-Tenant-ID": "header-tenant"})
    tenant = run(tenant_dependency(req, token_tenant=None))
    assert tenant == "header-tenant"


def test_token_overrides_header():
    # when token and header agree, token value is used
    req = DummyRequest({"X-Tenant-ID": "token-tenant"})
    tenant = run(tenant_dependency(req, token_tenant="token-tenant"))
    assert tenant == "token-tenant"


def test_mismatch_raises_403():
    req = DummyRequest({"X-Tenant-ID": "different"})
    try:
        run(tenant_dependency(req, token_tenant="token-tenant"))
        assert False, "expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 403
