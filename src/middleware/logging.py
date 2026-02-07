# src/middleware/logging.py
import time
import uuid
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger("http")

class RequestIdMiddleware:
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        start = time.time()
        req_id = request.headers.get(self.header_name.lower()) or str(uuid.uuid4())
        bind_contextvars(request_id=req_id, path=request.url.path, method=request.method)
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.exception("http_request_exception", error=str(exc))
            raise
        finally:
            duration_ms = int((time.time() - start) * 1000)
            logger.info("http_request_finished", request_id=req_id, path=request.url.path, method=request.method, duration_ms=duration_ms)
            clear_contextvars()
