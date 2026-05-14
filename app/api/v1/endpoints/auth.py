"""
app/api/v1/endpoints/auth.py
-----------------------------
Authentication endpoints: login, token refresh, and logout.
"""

# APIRouter  → a mini FastAPI app. Groups related routes together.
#              Think of it as a "section" of your API.
# Depends    → dependency injection. FastAPI calls the function and injects the result.
# HTTPException → raises an HTTP error response (status code + message)
# status     → module of HTTP status code constants (status.HTTP_401_UNAUTHORIZED = 401)
from fastapi import APIRouter, Depends, HTTPException, status

# OAuth2PasswordRequestForm → a special Pydantic model that reads username + password
#   from an application/x-www-form-urlencoded request body (the standard OAuth2 format).
#   This is what Swagger UI's "Authorize" button sends.
from fastapi.security import OAuth2PasswordRequestForm

# JWTError → raised when a token is invalid, expired, or tampered with
from jose import JWTError

# Session → type hint for a SQLAlchemy database session
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.crud.user import authenticate_user, get_user
from app.schemas.auth import MessageResponse, RefreshRequest, Token


# APIRouter() creates a router object that holds a group of related routes.
#
# prefix="/auth" → all routes in this router start with /auth.
#   So @router.post("/login") becomes POST /auth/login
#   And @router.post("/refresh") becomes POST /auth/refresh
#   When this router is included in the main app with prefix="/api/v1",
#   the full path becomes /api/v1/auth/login
#
# tags=["Authentication"] → groups these routes under the "Authentication" section
#   in Swagger UI (/docs). Makes the docs easier to navigate.
#   All routes with the same tag appear together in one collapsible section.
router = APIRouter(prefix="/auth", tags=["Authentication"])


# @router.post("/login") → registers this function as a POST /auth/login endpoint
#
# response_model=Token → FastAPI will:
#   1. Take whatever this function returns
#   2. Validate it against the Token schema
#   3. Serialize it to JSON
#   4. Any fields NOT in Token are automatically excluded from the response
#
# summary="..." → a short description shown next to the endpoint in Swagger UI
@router.post(
    "/login",
    response_model=Token,
    summary="Login with username/email and password",
)
def login(
    # OAuth2PasswordRequestForm → reads `username` and `password` from the form body.
    # Depends() with no arguments → FastAPI instantiates OAuth2PasswordRequestForm
    # and injects it. The form data comes from the request body, not JSON.
    # form_data.username → the submitted username
    # form_data.password → the submitted password
    form_data: OAuth2PasswordRequestForm = Depends(),

    # Depends(get_db) → FastAPI calls get_db(), opens a DB session, injects it as `db`
    db: Session = Depends(get_db),
):
    """
    OAuth2-compatible login endpoint.
    Accepts application/x-www-form-urlencoded with `username` and `password`.
    Returns JWT access + refresh tokens.
    """
    # authenticate_user checks if the credentials are valid
    # Returns the User object if valid, None if not
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        # raise HTTPException → immediately stops the function and returns an error response
        # status_code=401 → HTTP 401 Unauthorized
        # detail → the error message in the response body: {"detail": "Incorrect username..."}
        # headers={"WWW-Authenticate": "Bearer"} → required by the OAuth2 spec.
        #   Tells the client what authentication scheme to use.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        # status.HTTP_400_BAD_REQUEST = 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    # Return a Token object. FastAPI serializes it to JSON using the Token schema.
    # create_access_token(user.id) → creates a JWT with "sub": "42" (the user's ID)
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# response_model=Token → the response will be serialized as a Token JSON object
# summary="..." → shown in Swagger UI
@router.post("/refresh", response_model=Token, summary="Refresh access token")
def refresh_token(
    # payload: RefreshRequest → reads the JSON body and validates it as RefreshRequest
    # The client sends: {"refresh_token": "eyJhbGci..."}
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Called when the access token expires (after 30 minutes).
    """
    try:
        # decode_token() verifies the signature and expiry
        data = decode_token(payload.refresh_token)

        # Make sure this is a refresh token, not an access token
        if data.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")

        # data["sub"] → the user ID stored in the token (as a string)
        # int(data["sub"]) → convert "42" back to 42
        user = get_user(db, int(data["sub"]))

    except (JWTError, KeyError):
        # JWTError → token is expired, invalid signature, or malformed
        # KeyError  → "sub" key is missing from the payload
        raise UnauthorizedException("Invalid or expired refresh token")

    # Issue a fresh pair of tokens
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# response_model=MessageResponse → returns {"message": "..."}
# summary="..." → shown in Swagger UI
@router.post("/logout", response_model=MessageResponse, summary="Logout (client-side)")
def logout():
    """
    Stateless logout.

    JWTs are stateless — the server doesn't store them, so it can't "invalidate" one.
    The standard approach is to tell the client to delete their tokens.

    For true server-side revocation (e.g. "log out all devices"), you'd store
    issued tokens in a Redis blocklist and check it on every request.
    """
    return MessageResponse(message="Successfully logged out. Please discard your tokens.")
