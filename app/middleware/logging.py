"""
app/middleware/logging.py
--------------------------
Custom request/response logging middleware.

Middleware runs on EVERY request, before and after the route handler.
Think of it as a wrapper around your entire application.

Request flow with middleware:
  Client → Middleware (before) → Route Handler → Middleware (after) → Client
"""

import time     # for measuring how long a request takes
import logging  # Python's built-in logging module

# Request  → represents the incoming HTTP request
from fastapi import Request

# BaseHTTPMiddleware → the base class for writing custom middleware in FastAPI/Starlette
from starlette.middleware.base import BaseHTTPMiddleware

# Response → represents the HTTP response
from starlette.responses import Response


# logging.getLogger("fastapi.access") → gets (or creates) a logger named "fastapi.access"
# Logger names are hierarchical: "fastapi.access" is a child of "fastapi"
# You can configure log levels and handlers for specific loggers in your logging config
logger = logging.getLogger("fastapi.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with its method, path, status code, and duration.
    Also adds an X-Process-Time header to every response.

    Inherits from BaseHTTPMiddleware which requires implementing dispatch().
    """

    # dispatch() is called for EVERY request.
    # It must call `await call_next(request)` to pass the request to the next layer
    # (either the next middleware or the actual route handler).
    # async def → required because call_next is async
    async def dispatch(self, request: Request, call_next) -> Response:
        # time.perf_counter() → high-resolution timer. More accurate than time.time()
        # for measuring short durations. Returns seconds as a float.
        start = time.perf_counter()

        # call_next(request) → passes the request to the route handler and waits for the response.
        # Everything BEFORE this line runs before the route handler.
        # Everything AFTER this line runs after the route handler.
        response = await call_next(request)

        # Calculate how long the request took in milliseconds
        # (perf_counter() - start) → elapsed seconds
        # * 1000 → convert to milliseconds
        duration_ms = (time.perf_counter() - start) * 1000

        # Log the request details
        # %s → string placeholder, %d → integer placeholder, %.2f → float with 2 decimal places
        # request.method → "GET", "POST", "PATCH", etc.
        # request.url.path → "/api/v1/users/me"
        # response.status_code → 200, 201, 404, etc.
        logger.info(
            "%s %s → %d  (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Add a custom header to the response.
        # X-Process-Time → a custom header (X- prefix = non-standard/custom header)
        # The client can see this in their browser's DevTools → Network tab → Response Headers
        # Useful for debugging slow endpoints
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Must return the response — this sends it back to the client
        return response
