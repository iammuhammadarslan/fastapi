"""
app/crud/user.py
----------------
CRUD operations for User. CRUD = Create, Read, Update, Delete.

These functions contain ALL database logic for users.
Route handlers (api/v1/endpoints/users.py) call these functions.
This separation means:
  - Routes stay thin and readable (no SQL in routes)
  - DB logic is reusable across multiple routes
  - Easier to test (test these functions directly without HTTP)
"""

# Session → type hint for a SQLAlchemy database session object
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_user(db: Session, user_id: int) -> User:
    """
    Fetch a single user by their primary key (id).

    db.query(User)           → start a SELECT query on the users table
    .filter(User.id == user_id) → add WHERE id = user_id
    .first()                 → return the first result, or None if not found

    We raise NotFoundException instead of returning None so the caller
    doesn't need to check for None — the exception is handled globally.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(f"User with id={user_id} not found")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Fetch a user by email. Returns None if not found (no exception).
    Used for login (where "not found" means "wrong credentials", not an error)
    and for duplicate-check before registration.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Fetch a user by username. Returns None if not found."""
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """
    Fetch a paginated list of all users.

    .offset(skip)  → skip the first N rows (for pagination)
    .limit(limit)  → return at most N rows
    .all()         → execute the query and return all results as a list

    Example: skip=20, limit=20 → returns rows 21-40 (page 2 of 20 per page)
    """
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, payload: UserCreate) -> User:
    """
    Create a new user in the database.

    Steps:
    1. Check for duplicate email/username (raise ConflictException if found)
    2. Hash the password (never store plain text)
    3. Create a User ORM object
    4. Add it to the session (staged for insert)
    5. Commit (execute the INSERT SQL)
    6. Refresh (reload the object from DB to get auto-generated fields like id, created_at)
    7. Return the user
    """
    # Guard against duplicate email
    if get_user_by_email(db, payload.email):
        raise ConflictException("A user with this email already exists")

    # Guard against duplicate username
    if get_user_by_username(db, payload.username):
        raise ConflictException("A user with this username already exists")

    # Create the ORM object. We pass hashed_password, NOT payload.password.
    user = User(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )

    # db.add(user) → stages the user for insertion. No SQL runs yet.
    db.add(user)

    # db.commit() → executes the INSERT SQL and saves to the database.
    #               If this fails (e.g. unique constraint violation), it raises an error
    #               and the session is automatically rolled back.
    db.commit()

    # db.refresh(user) → reloads the user object from the database.
    #                    This populates auto-generated fields: id, created_at, updated_at.
    #                    Without this, user.id would still be None after the commit.
    db.refresh(user)

    return user


def update_user(db: Session, user_id: int, payload: UserUpdate) -> User:
    """
    Update a user's fields. Only updates the fields that were actually sent.

    payload.model_dump(exclude_unset=True) → converts the Pydantic model to a dict,
    but ONLY includes fields that were explicitly set by the client.
    If the client sends {"full_name": "John"}, only full_name is in the dict.
    email and password are NOT included (they weren't sent), so they won't be changed.
    This is what makes PATCH different from PUT (which replaces everything).
    """
    user = get_user(db, user_id)

    # exclude_unset=True → only include fields the client actually sent
    update_data = payload.model_dump(exclude_unset=True)

    # If the client sent a new password, hash it before saving.
    # We pop "password" (remove it from the dict) and add "hashed_password" instead.
    # The User model has hashed_password, not password.
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    # setattr(obj, name, value) → dynamically sets an attribute on an object.
    # Same as: user.full_name = value, but works when the field name is a variable.
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """
    Delete a user from the database.
    Because of cascade="all, delete-orphan" on User.items,
    all of this user's items are automatically deleted too.
    """
    user = get_user(db, user_id)

    # db.delete(user) → stages the user for deletion. No SQL runs yet.
    db.delete(user)

    # db.commit() → executes the DELETE SQL
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Verify login credentials. Returns the User if valid, None if not.

    We return None (not raise an exception) because "wrong credentials" is
    a normal login failure, not an unexpected error. The route handler
    decides what HTTP response to send.

    We allow login with EITHER email OR username:
    get_user_by_email(db, username) → tries to find a user with that email
    or get_user_by_username(db, username) → if not found by email, try username
    The `or` short-circuits: if the first call returns a user, the second is skipped.
    """
    from app.core.security import verify_password

    user = get_user_by_email(db, username) or get_user_by_username(db, username)

    # If no user found, or password doesn't match → return None
    if not user or not verify_password(password, user.hashed_password):
        return None

    return user
