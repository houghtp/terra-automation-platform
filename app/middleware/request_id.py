import uuid
import typing
from contextvars import ContextVar
from starlette.types import ASGIApp, Receive, Scope, Send

# ContextVar to store current request id
request_id_ctx_var: ContextVar[typing.Optional[str]] = ContextVar("request_id", default=None)


class RequestIDMiddleware:
    """ASGI middleware that ensures each request has a request id.

    It will read X-Request-ID from the incoming headers if present, otherwise
    generate a uuid4. The id is stored in a ContextVar and the response will
    include the header `X-Request-ID`.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get("headers", []))
        incoming_id = headers.get("x-request-id")
        if incoming_id:
            rid = incoming_id[:128]
        else:
            rid = str(uuid.uuid4())

        token = request_id_ctx_var.set(rid)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx_var.reset(token)
