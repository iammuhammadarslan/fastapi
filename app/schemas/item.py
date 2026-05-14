"""
app/schemas/item.py
-------------------
Pydantic schemas for Item. Follow the Base/Create/Update/Response pattern:

  ItemBase     → shared fields used by multiple schemas
  ItemCreate   → fields required when CREATING an item (POST request body)
  ItemUpdate   → fields allowed when UPDATING an item (PATCH request body, all optional)
  ItemResponse → fields returned in the API response (GET response body)
"""

from datetime import datetime

# BaseModel     → base class for all Pydantic schemas
# Field         → lets you add validation rules and metadata to a field
# field_validator → decorator for custom per-field validation logic
from pydantic import BaseModel, Field, field_validator


class ItemBase(BaseModel):
    """
    Shared fields that appear in both the create request and the response.
    Other schemas inherit from this to avoid repeating these fields.
    """

    # Field(...) → the ... (Ellipsis) means this field is REQUIRED. No default value.
    # min_length=1  → must have at least 1 character
    # max_length=255 → cannot exceed 255 characters
    title: str = Field(..., min_length=1, max_length=255)

    # str | None → this field can be a string OR None (it's optional)
    # Field(None, ...) → None is the default value (field is optional)
    # max_length=2000 → if provided, cannot exceed 2000 characters
    description: str | None = Field(None, max_length=2000)

    # gt=0 → "greater than 0". Price must be positive. (gt = greater than)
    # Other options: ge=0 (≥0), lt=100 (<100), le=100 (≤100)
    # description → this text appears in the Swagger UI docs for this field
    price: float = Field(..., gt=0, description="Price must be greater than 0")

    # No Field() needed here — True is just the default value
    is_available: bool = True


class ItemCreate(ItemBase):
    """
    Schema for creating a new item. Inherits all fields from ItemBase.
    Adds a custom validator to clean up the title.
    """

    # @field_validator("title") → this function runs when the "title" field is validated
    # @classmethod → required by Pydantic for field validators
    # v: str → the value that was submitted for the "title" field
    # The function must return the (possibly modified) value, or raise ValueError to reject it
    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        # v.strip() removes leading/trailing whitespace
        # "   " would pass min_length=1 but is still blank — this catches that case
        if not v.strip():
            raise ValueError("Title cannot be blank or whitespace")
        # Return the stripped version — this REPLACES the submitted value.
        # So "  My Item  " becomes "My Item" before it's saved.
        return v.strip()


class ItemUpdate(BaseModel):
    """
    Schema for partially updating an item (PATCH request).
    ALL fields are optional (str | None, float | None, bool | None).
    This means the client only needs to send the fields they want to change.

    We use model_dump(exclude_unset=True) in the CRUD layer to only update
    the fields that were actually sent, not all fields.
    """

    # str | None with Field(None, ...) → optional field, defaults to None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    # float | None → optional, but if provided must be > 0
    price: float | None = Field(None, gt=0)
    is_available: bool | None = None


class ItemResponse(ItemBase):
    """
    Schema for the API response when returning item data.
    Inherits all fields from ItemBase and adds DB-generated fields.

    These fields exist in the database but are NOT in ItemCreate
    (the client doesn't send them — the DB generates them automatically).
    """
    id: int           # auto-generated primary key
    owner_id: int     # the ID of the user who created this item

    # datetime → Python's datetime type. FastAPI serializes this to ISO 8601 string
    # e.g. "2024-01-15T10:30:00Z"
    created_at: datetime
    updated_at: datetime

    # from_attributes=True → tells Pydantic to read data from object ATTRIBUTES
    # (like user.email) instead of only from dictionaries (like data["email"]).
    # This is required when converting SQLAlchemy model instances to Pydantic schemas.
    # Without this, FastAPI cannot serialize a SQLAlchemy Item object to JSON.
    model_config = {"from_attributes": True}
