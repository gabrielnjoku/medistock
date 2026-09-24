import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware attaching unique X-Request-ID and X-Response-Time header to every response.

    Allows user-reported errors, server logs, and performance metrics to be matched up
    precisely without guessing by timestamp.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000.0

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{process_time_ms:.2f}ms"
        return response
