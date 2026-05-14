"""
app/core/config.py
------------------
Central configuration file. All settings come from environment variables
or a .env file. Never hardcode secrets — put them here and read from .env.
"""

# BaseSettings  → special Pydantic class that reads values from environment variables
# SettingsConfigDict → used to configure HOW BaseSettings behaves (e.g. which .env file to read)
from pydantic_settings import BaseSettings, SettingsConfigDict

# field_validator → a decorator to add custom validation logic to a single field
from pydantic import field_validator

# List → standard Python type hint for a list (same as list[str] in Python 3.9+)
from typing import List


class Settings(BaseSettings):
    """
    Every attribute here is a setting.
    Pydantic reads them in this priority order:
      1. Actual environment variables (e.g. export SECRET_KEY=abc)
      2. Values in the .env file
      3. The default values written below
    """

    # ── App settings ──────────────────────────────────────────────────────────
    APP_NAME: str = "FastAPI Learning Project"   # shown in Swagger UI title
    APP_VERSION: str = "1.0.0"                   # shown in Swagger UI
    DEBUG: bool = True                           # True = show SQL logs, more verbose errors
    API_V1_PREFIX: str = "/api/v1"               # all routes start with this prefix

    # ── Security settings ─────────────────────────────────────────────────────
    # SECRET_KEY is used to SIGN JWT tokens. Anyone with this key can forge tokens.
    # Generate a safe one with: openssl rand -hex 32
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    # ALGORITHM tells python-jose which signing algorithm to use for JWT.
    # HS256 = HMAC with SHA-256. It's symmetric (same key to sign and verify).
    ALGORITHM: str = "HS256"

    # How long (in minutes) before an access token expires and the user must re-login
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # How long (in days) before a refresh token expires
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database settings ─────────────────────────────────────────────────────
    # The connection string SQLAlchemy uses to connect to the database.
    # Format: dialect+driver://username:password@host:port/database
    # sqlite:///./app.db  → SQLite file called app.db in the current directory
    # For PostgreSQL: postgresql+psycopg2://user:pass@localhost:5432/mydb
    DATABASE_URL: str = "sqlite:///./app.db"

    # ── CORS settings ─────────────────────────────────────────────────────────
    # CORS = Cross-Origin Resource Sharing.
    # Browsers block JavaScript from calling APIs on different domains by default.
    # This list tells FastAPI which frontend origins are allowed to call our API.
    # Example: your React app on localhost:3000 calling this API on localhost:8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    # mode="before" → this validator runs BEFORE Pydantic does its own type checking.
    # That means `v` here could be a raw string from the .env file, not yet a list.
    @classmethod
    def parse_origins(cls, v):
        # If someone sets ALLOWED_ORIGINS="http://a.com,http://b.com" in .env,
        # this splits it into a proper Python list: ["http://a.com", "http://b.com"]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v  # already a list, return as-is

    # model_config controls how this Settings class behaves
    # env_file=".env"       → look for a file called .env in the project root
    # case_sensitive=True   → SECRET_KEY and secret_key are treated as different variables
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create ONE instance of Settings at import time.
# Every other file does: from app.core.config import settings
# They all get this same object — no re-reading the .env file on every import.
settings = Settings()
