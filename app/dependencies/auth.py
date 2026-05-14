"""
app/dependencies/auth.py
------------------------
Reusable authentication dependencies.

A "dependency" in FastAPI is a function you declare in a route parameter with Depends().
FastAPI calls it automatically before your route runs and injects the result.

These three functions form a chain:
  get_current_user
      ↓ (called by)
  get_current_active_user
      ↓ (called by)
  get_current_superuser

Each level adds one more check on top of the previous.
"""

# Depends → tells FastAPI "call this function and inject its return value"
from fastapi import Depends

# OAuth2PasswordBearer → extracts the JWT token from the Authorization header.
#   The client sends: Authorization: Bearer eyJhbGci...
#   OAuth2PasswordBearer extracts just the token part: eyJhbGci...
from fastapi.security import OAuth2PasswordBearer

# JWTError → raised by python-jose when a token is invalid or expired
from jose import JWTError

# Session → type hint for a SQLAlchemy database session
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.security import decode_token
from app.crud.user import get_user
from app.models.user import User


# OAuth2PasswordBearer does two things:
# 1. Extracts the token from the "Authorization: Bearer <token>" header
# 2. If the header is missing, automatically returns HTTP 401 (no token = not authenticated)
#
# tokenUrl="/api/v1/auth/login" → tells Swagger UI where to send the login form.
#   When you click "Authorize" in Swagger UI, it sends the form to this URL.
#   This is just for documentation — it doesn't affect how the token is validated.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    # Depends(oauth2_scheme) → FastAPI calls oauth2_scheme first, extracts the token
    # string from the Authorization header, and passes it here as `token`.
    token: str = Depends(oauth2_scheme),

    # Depends(get_db) → FastAPI calls get_db(), opens a DB session, passes it as `db`.
    db: Session = Depends(get_db),
) -> User:
    """
    Decodes the JWT token and returns the User it belongs to.
    Raises UnauthorizedException (HTTP 401) if the token is invalid.
    """
    try:
        # decode_token() verifies the signature and expiry, returns the payload dict
        payload = decode_token(token)

        # Check that this is an access token, not a refresh token.
        # payload.get("type") → safely gets "type" from the dict (returns None if missing)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")

        # "sub" is the standard JWT claim for "subject" — who the token belongs to.
        # We stored the user's ID as a string in the token when we created it.
        user_id: str = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException()

    except JWTError:
        # JWTError covers: expired token, invalid signature, malformed token
        raise UnauthorizedException("Could not validate credentials")

    # int(user_id) → convert the string "42" back to integer 42
    # get_user() queries the DB and raises NotFoundException if user doesn't exist
    return get_user(db, int(user_id))


def get_current_active_user(
    # Depends(get_current_user) → FastAPI calls get_current_user() first.
    # If that raises an exception, this function never runs.
    # If it succeeds, the returned User object is passed here as `current_user`.
    # This is "dependency chaining" — each dependency builds on the previous one.
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Extends get_current_user by also checking the user's is_active flag.
    A user might exist in the DB but be deactivated (banned, suspended, etc.).
    Raises ForbiddenException (HTTP 403) if the user is inactive.
    """
    if not current_user.is_active:
        raise ForbiddenException("Inactive user account")
    return current_user


def get_current_superuser(
    # Depends(get_current_active_user) → calls get_current_active_user() first.
    # So the full chain is: oauth2_scheme → get_current_user → get_current_active_user → here
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Extends get_current_active_user by also checking the is_superuser flag.
    Only superusers can access routes that use this dependency.
    Raises ForbiddenException (HTTP 403) if the user is not a superuser.
    """
    if not current_user.is_superuser:
        raise ForbiddenException("Superuser privileges required")
    return current_user
