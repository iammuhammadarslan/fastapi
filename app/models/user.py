"""
app/models/user.py
------------------
The User ORM model. This class maps directly to the "users" table in the database.
ORM = Object Relational Mapper. It lets you work with DB rows as Python objects
instead of writing raw SQL.
"""

from datetime import datetime, timezone

# SQLAlchemy column types — these map to database column types:
# Boolean  → BOOLEAN  (True/False)
# DateTime → DATETIME or TIMESTAMP
# Integer  → INTEGER  (whole numbers)
# String   → VARCHAR  (text with a max length)
# func     → lets you call database functions like NOW(), COUNT(), etc.
from sqlalchemy import Boolean, DateTime, Integer, String, func

# Mapped        → type hint wrapper that tells SQLAlchemy "this is a DB column"
# mapped_column → defines the actual column with its constraints
# relationship  → defines a Python-level link between two models (no extra column needed)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Base → the parent class all models must inherit from (defined in database.py)
from app.core.database import Base


class User(Base):
    """
    Represents a row in the "users" table.
    Every attribute with mapped_column() becomes a column in the database.
    """

    # __tablename__ tells SQLAlchemy the exact name of the table in the database.
    # If you don't set this, SQLAlchemy uses the class name in lowercase.
    __tablename__ = "users"

    # ── Columns ───────────────────────────────────────────────────────────────

    # Mapped[int]          → Python type hint: this attribute will be an int
    # mapped_column(...)   → defines the database column
    # Integer              → database column type: stores whole numbers
    # primary_key=True     → this column uniquely identifies each row.
    #                        Every table must have exactly one primary key.
    #                        SQLAlchemy auto-increments this (1, 2, 3, ...)
    # index=True           → creates a database index on this column.
    #                        An index is like a book's index — makes lookups MUCH faster.
    #                        Always index columns you search/filter by.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # String(255)   → VARCHAR(255) in the database — text up to 255 characters
    # unique=True   → no two rows can have the same email (enforced by the DB)
    # index=True    → fast lookups by email (used in login)
    # nullable=False → this column cannot be NULL — it must always have a value
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # String(100) → max 100 characters for username
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # We NEVER store the plain password. Only the bcrypt hash.
    # String(255) is enough for a bcrypt hash (they're ~60 chars but we give extra room)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Mapped[str | None] → Python type: either a string OR None (optional field)
    # nullable=True      → this column CAN be NULL in the database
    # When Mapped[str | None] and nullable=True go together, the field is optional.
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Boolean → stores True/False (1/0 in SQLite, BOOLEAN in PostgreSQL)
    # default=True → if you don't set this when creating a user, it defaults to True
    #                Note: this is a Python-level default, not a database default.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # DateTime(timezone=True) → stores date + time WITH timezone info (recommended)
    # server_default=func.now() → the DATABASE sets this automatically on INSERT.
    #   func.now() calls the DB's built-in NOW() function.
    #   This is better than Python's datetime.now() because it uses the DB server's
    #   clock, not your app server's clock (they might differ in distributed systems).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # onupdate=func.now() → every time this row is UPDATED, the DB automatically
    #                        sets this column to the current time.
    #                        You don't need to set it manually in your code.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    # relationship() creates a Python-level link between User and Item.
    # It does NOT create a new column — the foreign key is on the Item side.
    # After this, you can do: user.items → returns a list of Item objects.
    # SQLAlchemy runs the JOIN query automatically.

    # Mapped[list["Item"]]  → Python type: a list of Item objects
    #   "Item" in quotes    → forward reference. Item is defined in another file
    #                         and hasn't been imported yet when Python reads this line.
    #                         The quotes tell Python "resolve this name later".

    # "Item"                → the name of the related model class
    # back_populates="owner" → links this relationship to the "owner" attribute on Item.
    #                          When you set item.owner = user, SQLAlchemy automatically
    #                          adds the item to user.items (and vice versa).
    # cascade="all, delete-orphan" → when you DELETE a user, automatically DELETE
    #                                 all their items too. Without this, deleting a user
    #                                 with items would cause a foreign key error.
    items: Mapped[list["Item"]] = relationship(
        "Item", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        # __repr__ is what Python shows when you print() this object or inspect it
        # in a debugger. The !r adds quotes around the email string.
        return f"<User id={self.id} email={self.email!r}>"
