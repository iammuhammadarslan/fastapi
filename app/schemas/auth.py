"""
app/schemas/auth.py
-------------------
Pydantic schemas for authentication-related request and response bodies.

Schemas are NOT database models. They define the shape of data going IN and OUT
of the API. Pydantic validates the data automatically before your code runs.
"""

# BaseModel → the base class for all Pydantic schemas.
#             Gives you automatic validation, serialization, and documentation.
from pydantic import BaseModel


class Token(BaseModel):
    """
    The response body returned by POST /auth/login.
    The client receives both tokens and stores them (e.g. in localStorage or a cookie).

    access_token  → short-lived token (30 min). Sent with every API request.
                    Put it in the Authorization header: "Bearer <access_token>"
    refresh_token → long-lived token (7 days). Used ONLY to get a new access token.
    token_type    → always "bearer". This is the OAuth2 standard.
                    "bearer" means "whoever holds this token can use it".
                    default="bearer" → if not provided, Pydantic uses "bearer"
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Represents the decoded contents (payload) of a JWT token.
    Used internally when we decode a token to find out who it belongs to.

    sub  → "subject" — standard JWT claim. Contains the user's ID as a string.
    type → our custom claim. Either "access" or "refresh".
           We check this to prevent using a refresh token as an access token.
    """
    sub: str
    type: str


class LoginRequest(BaseModel):
    """
    Request body for a JSON-based login (not used by the OAuth2 form endpoint,
    but useful if you want a JSON login endpoint).

    username → can be either the user's username OR their email.
               Our authenticate_user() function checks both.
    """
    username: str
    password: str


class RefreshRequest(BaseModel):
    """
    Request body for POST /auth/refresh.
    The client sends their refresh token to get a new access token.
    """
    refresh_token: str


class MessageResponse(BaseModel):
    """
    A generic response schema for endpoints that just return a success message.
    Used by logout, delete, and other endpoints that don't return data.

    Example response JSON: {"message": "User deleted successfully"}
    """
    message: str
