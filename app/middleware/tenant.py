from contextvars import ContextVar
from typing import Optional
from starlette.types import ASGIApp, Receive, Scope, Send

# ContextVar for tenant
tenant_ctx_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


class TenantMiddleware:
    """Simple middleware to extract tenant id for multi-tenant support.

    Extraction order:
      1. Authorization/JWT (not implemented here; placeholder)
      2. X-Tenant-ID header
      3. Host-based parsing (subdomain)
      4. Fallback: 'unknown'

    This middleware stores a sanitized tenant id in a ContextVar so logs can
    include it.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get("headers", []))
        tenant = None

        # 1) Check for a header
        tenant_header = headers.get("x-tenant-id")
        if tenant_header:
            tenant = tenant_header
        else:
            # 2) Host-based extraction (subdomain)
            host = headers.get("host", "")
            if host and "." in host:
                possible = host.split(".")[0]
                # Don't extract tenant from localhost or IP addresses
                if possible and possible not in ("www", "localhost", "127"):
                    tenant = possible

        if not tenant:
            tenant = "unknown"

        # sanitize/truncate
        tenant = tenant.strip()[:64]

        token = tenant_ctx_var.set(tenant)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-tenant-id", tenant.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            tenant_ctx_var.reset(token)
