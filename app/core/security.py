"""
app/core/security.py
--------------------
Two responsibilities:
  1. Password hashing  — store passwords safely using bcrypt
  2. JWT tokens        — create and verify JSON Web Tokens for authentication
"""

# datetime  → for calculating token expiry times
# timedelta → represents a duration (e.g. timedelta(minutes=30) = 30 minutes)
# timezone  → used to make datetimes timezone-aware (UTC)
from datetime import datetime, timedelta, timezone

# Any → a type hint meaning "this can be any type" (used for the token subject)
from typing import Any

# bcrypt → the password hashing library. Never stores plain passwords.
import bcrypt

# jwt      → creates and decodes JWT tokens
# JWTError → raised when a token is invalid, expired, or tampered with
from jose import JWTError, jwt

from app.core.config import settings


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Takes a plain-text password and returns a bcrypt hash.

    Why hash? If your database is stolen, attackers get hashes like
    "$2b$12$abc..." instead of real passwords. Bcrypt is one-way —
    you cannot reverse a hash back to the original password.

    plain.encode("utf-8") → converts the string to bytes (bcrypt requires bytes)
    [:72]                 → bcrypt has a 72-byte limit. We truncate to avoid errors.
    bcrypt.gensalt()      → generates a random "salt" — random data mixed into the hash.
                            Two users with the same password get DIFFERENT hashes
                            because of different salts. This defeats rainbow table attacks.
    bcrypt.hashpw()       → combines the password bytes + salt and produces the hash
    .decode("utf-8")      → converts the result back to a string for storing in the DB
    """
    password_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Checks if a plain-text password matches a stored hash.

    You never "decrypt" a bcrypt hash. Instead, bcrypt re-hashes the plain
    password using the same salt (which is embedded in the stored hash string)
    and compares the result. Returns True if they match.

    bcrypt.checkpw() → does the comparison in constant time to prevent
                       timing attacks (where an attacker measures response
                       time to guess characters of the password)
    """
    password_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(subject: Any, expires_delta: timedelta | None = None) -> str:
    """
    Creates a short-lived JWT access token.

    A JWT looks like: xxxxx.yyyyy.zzzzz
      - xxxxx = header (algorithm used)
      - yyyyy = payload (the data we put in, base64-encoded but NOT encrypted)
      - zzzzz = signature (proves the token wasn't tampered with)

    subject      → who this token belongs to. We pass the user's ID (e.g. 42).
    expires_delta → how long until the token expires. Defaults to the setting value.

    datetime.now(timezone.utc) → current time in UTC (always use UTC for tokens)
    timedelta(minutes=30)      → adds 30 minutes to get the expiry time

    payload dict:
      "sub"  → "subject" — standard JWT claim. Who this token is for (user ID).
      "exp"  → "expiry"  — standard JWT claim. Unix timestamp when token expires.
      "type" → our custom claim. Distinguishes access tokens from refresh tokens.

    jwt.encode() → signs the payload with SECRET_KEY using the ALGORITHM.
                   Anyone with SECRET_KEY can verify the signature.
                   If someone changes the payload, the signature won't match.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Any) -> str:
    """
    Creates a long-lived JWT refresh token.

    Refresh tokens are used ONLY to get a new access token when the old one expires.
    They live longer (7 days) but should be stored securely (e.g. httpOnly cookie).
    The "type": "refresh" claim prevents using a refresh token as an access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token. Returns the payload dict.

    jwt.decode() does three things automatically:
      1. Verifies the signature (was this token signed by us?)
      2. Checks the expiry ("exp" claim) — raises JWTError if expired
      3. Decodes the payload and returns it as a Python dict

    algorithms=[settings.ALGORITHM] → list of allowed algorithms.
                                       Using a list prevents algorithm-switching attacks.

    Raises JWTError if the token is invalid, expired, or tampered with.
    The caller (get_current_user dependency) catches this and returns 401.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
