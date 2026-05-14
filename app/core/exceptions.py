"""
app/core/exceptions.py
-----------------------
Custom exception classes and their FastAPI handlers.

Why custom exceptions instead of raising HTTPException directly?
  - CRUD functions (crud/user.py) don't know about HTTP. They should raise
    business-level errors like "not found" or "conflict".
  - The handlers here convert those business errors into proper HTTP responses.
  - This keeps your database layer clean and decoupled from FastAPI.
"""

# Request    → represents the incoming HTTP request (used in handler signatures)
# status     → a module of HTTP status code constants (e.g. status.HTTP_404_NOT_FOUND = 404)
#              Using named constants is better than magic numbers like 404
from fastapi import Request, status

# JSONResponse → lets us return a custom JSON body with any status code
from fastapi.responses import JSONResponse


# ── Custom exception classes ──────────────────────────────────────────────────

class AppException(Exception):
    """
    Base class for all our custom exceptions.
    Inherits from Python's built-in Exception class.

    status_code → the HTTP status code to return (e.g. 404, 401, 403)
    detail      → the error message shown to the client
    """
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class NotFoundException(AppException):
    """
    Raised when a requested resource doesn't exist in the database.
    Maps to HTTP 404 Not Found.

    super().__init__() → calls AppException.__init__() with the 404 status code.
    detail has a default value so you can raise NotFoundException() with no arguments,
    or override it: raise NotFoundException("User with id=5 not found")
    """
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class UnauthorizedException(AppException):
    """
    Raised when a request has no valid authentication token.
    Maps to HTTP 401 Unauthorized.
    401 means "you need to log in first".
    """
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


class ForbiddenException(AppException):
    """
    Raised when a user is authenticated but doesn't have permission.
    Maps to HTTP 403 Forbidden.
    403 means "you're logged in, but you can't do this".
    Example: a regular user trying to delete another user's account.
    """
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class ConflictException(AppException):
    """
    Raised when trying to create something that already exists.
    Maps to HTTP 409 Conflict.
    Example: registering with an email that's already taken.
    """
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status.HTTP_409_CONFLICT, detail)


class BadRequestException(AppException):
    """
    Raised when the request data is invalid in a way Pydantic didn't catch.
    Maps to HTTP 400 Bad Request.
    """
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


# ── Exception handlers ────────────────────────────────────────────────────────
# These are registered in app/main.py with app.add_exception_handler().
# When an exception is raised anywhere in the app, FastAPI looks for a matching
# handler and calls it instead of returning a generic 500 error.

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handles any AppException (and its subclasses: NotFoundException, etc.).

    request → the HTTP request that caused the error (we don't use it here,
              but FastAPI requires it in the handler signature)
    exc     → the exception that was raised

    JSONResponse() → builds an HTTP response with:
      status_code → taken from the exception (e.g. 404)
      content     → the JSON body. {"detail": "..."} is the FastAPI standard format.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any exception we didn't anticipate.
    Maps to HTTP 500 Internal Server Error.

    IMPORTANT: Never return the actual error message (exc) to the client.
    It could leak sensitive information like file paths, SQL queries, or
    internal variable names. Always return a generic message.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )
