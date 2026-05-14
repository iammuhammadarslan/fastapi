"""
app/schemas/user.py
-------------------
Pydantic schemas for User. Follow the Base/Create/Update/Response pattern.

Why separate schemas from models?
  - The DB model (User) has hashed_password — never expose that in an API response.
  - The create schema has password + password_confirm — never store those in the DB.
  - The update schema has all optional fields — the DB model has required fields.
  Schemas are the "contract" between your API and the outside world.
"""

from datetime import datetime

# BaseModel      → base class for all Pydantic schemas
# EmailStr       → a special string type that validates email format (user@example.com)
# Field          → adds validation rules and metadata to a field
# computed_field → a property that gets included in the serialized output
# model_validator → validates the whole model (can compare multiple fields)
from pydantic import BaseModel, EmailStr, Field, computed_field, model_validator

# We import ItemResponse here so UserWithItems can include a list of items
from app.schemas.item import ItemResponse


class UserBase(BaseModel):
    """
    Shared fields used by UserCreate, UserUpdate, and UserResponse.
    Putting common fields here avoids repeating them in every schema.
    """

    # EmailStr → Pydantic validates this is a real email format.
    # If you send "notanemail", Pydantic rejects it with a 422 error automatically.
    # Requires pydantic[email] to be installed (adds the email-validator library).
    email: EmailStr

    # Field(...) → ... means REQUIRED
    # min_length=3    → username must be at least 3 characters
    # max_length=50   → username cannot exceed 50 characters
    # pattern=r"..."  → regex pattern the value must match.
    #   ^             → start of string
    #   [a-zA-Z0-9_]+ → one or more letters, digits, or underscores
    #   $             → end of string
    #   This prevents usernames like "user name" (space) or "user@name" (@ sign)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")

    # str | None → optional field (can be None)
    # Field(None, ...) → None is the default (field not required)
    full_name: str | None = Field(None, max_length=255)


class UserCreate(UserBase):
    """
    Schema for registering a new user (POST /users/ request body).
    Inherits email, username, full_name from UserBase and adds password fields.
    """

    # min_length=8   → enforce a minimum password length
    # max_length=128 → prevent extremely long passwords (bcrypt has a 72-byte limit anyway)
    password: str = Field(..., min_length=8, max_length=128)

    # password_confirm → the user types their password twice to confirm it.
    # No Field() constraints here — we validate it matches password in the validator below.
    password_confirm: str

    # @model_validator → runs after ALL individual fields are validated.
    # mode="after"     → "after" means self is a fully constructed UserCreate instance.
    #                    You can access self.password and self.password_confirm.
    #                    (mode="before" would give you raw dict data instead)
    # The method must return self (the validated model) or raise ValueError.
    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class UserUpdate(BaseModel):
    """
    Schema for updating a user (PATCH /users/{id} request body).
    ALL fields are optional — the client only sends what they want to change.

    Note: we don't inherit from UserBase because UserBase has required fields.
    For updates, everything must be optional.
    """

    # EmailStr | None → optional email update
    full_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None

    # str | None → optional password change
    # min_length=8 → if provided, must still be at least 8 characters
    password: str | None = Field(None, min_length=8)


class UserResponse(UserBase):
    """
    Schema for the API response when returning user data.
    Inherits email, username, full_name from UserBase.
    Adds DB-generated fields (id, timestamps) and computed fields.

    IMPORTANT: hashed_password is NOT here — it's never sent to the client.
    """
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    # from_attributes=True → allows Pydantic to read from SQLAlchemy model attributes.
    # Without this, FastAPI cannot convert a User ORM object to UserResponse JSON.
    # model_config is a Pydantic v2 way to configure the schema behavior.
    model_config = {"from_attributes": True}

    # @computed_field → this property is calculated from other fields and included
    #                   in the JSON response automatically. The client sees "display_name"
    #                   in the response even though it's not a DB column.
    # @property       → makes it a property (accessed as self.display_name, not self.display_name())
    @computed_field
    @property
    def display_name(self) -> str:
        # Returns full_name if it exists, otherwise falls back to username.
        # "John Doe" if full_name is set, "johndoe" if not.
        return self.full_name or self.username


class UserWithItems(UserResponse):
    """
    Extended response that includes the user's items.
    Used by GET /users/me to show the current user's profile with their items.

    Inherits everything from UserResponse and adds the items list.
    list[ItemResponse] = [] → defaults to empty list if user has no items.
    """
    items: list[ItemResponse] = []
