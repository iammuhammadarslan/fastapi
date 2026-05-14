"""
app/models/item.py
------------------
The Item ORM model. Maps to the "items" table in the database.
Each item belongs to one user (many-to-one relationship).
"""

from datetime import datetime

# Float      → FLOAT/REAL in the database (decimal numbers like 9.99)
# ForeignKey → creates a link between two tables at the database level
# Text       → TEXT in the database — unlimited length text (vs String which has a limit)
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Item(Base):
    __tablename__ = "items"

    # primary_key=True → unique identifier for each item row
    # index=True       → fast lookups by item ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # index=True → we'll often search/filter items by title, so index it
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    # Text → unlike String(255), Text has no length limit. Good for long descriptions.
    # Mapped[str | None] + nullable=True → description is optional
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Float → stores decimal numbers (e.g. 19.99)
    # nullable=False → price is required, every item must have a price
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # default=True → new items are available by default
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Foreign Key ───────────────────────────────────────────────────────────

    # ForeignKey("users.id") → this is the database-level link.
    # It says: "the value in owner_id must match an existing id in the users table".
    # The database enforces this — you cannot create an item with an owner_id
    # that doesn't exist in the users table (referential integrity).
    # "users.id" → format is "tablename.columnname"
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationship ──────────────────────────────────────────────────────────

    # This is the OTHER side of the User.items relationship.
    # Mapped["User"]      → Python type: a single User object (not a list)
    # "User"              → the related model class name (forward reference)
    # back_populates="items" → links to the "items" attribute on User.
    #                          Setting item.owner = user automatically updates user.items.
    # After this, you can do: item.owner → returns the User object who owns this item
    owner: Mapped["User"] = relationship("User", back_populates="items")

    def __repr__(self) -> str:
        return f"<Item id={self.id} title={self.title!r}>"
