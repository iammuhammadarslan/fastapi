"""
app/api/v1/endpoints/users.py
------------------------------
User management endpoints: register, list, get, update, delete.
"""

# BackgroundTasks → FastAPI's built-in system for running tasks after the response is sent
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import user as user_crud
from app.dependencies.auth import get_current_active_user, get_current_superuser
from app.dependencies.pagination import PaginationParams
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserWithItems
from app.utils.email import send_welcome_email


# prefix="/users" → all routes here start with /users
#   Full path (with app prefix): /api/v1/users
# tags=["Users"]  → groups these routes under "Users" in Swagger UI
router = APIRouter(prefix="/users", tags=["Users"])


# @router.post("/") → POST /users/
#
# response_model=UserResponse → FastAPI converts the returned User ORM object
#   to a UserResponse Pydantic schema before sending the JSON response.
#   Fields NOT in UserResponse (like hashed_password) are automatically excluded.
#
# status_code=status.HTTP_201_CREATED → returns HTTP 201 instead of the default 200.
#   201 = "Created". The standard status code for successful resource creation.
#   status.HTTP_201_CREATED is just the integer 201 — using the named constant
#   is clearer and less error-prone than writing 201 directly.
#
# summary="..." → short description shown in Swagger UI next to the endpoint
@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def create_user(
    # payload: UserCreate → FastAPI reads the JSON request body and validates it
    # as a UserCreate Pydantic schema. If validation fails (e.g. invalid email,
    # password too short), FastAPI automatically returns HTTP 422 with error details.
    payload: UserCreate,

    # BackgroundTasks → FastAPI injects this automatically (no Depends needed).
    # You call background_tasks.add_task(func, arg1, arg2) to schedule a function
    # to run AFTER the HTTP response is sent. The client doesn't wait for it.
    background_tasks: BackgroundTasks,

    db: Session = Depends(get_db),
):
    """
    Register a new user account.
    A welcome email is sent in the background so the response is not delayed.
    """
    user = user_crud.create_user(db, payload)

    # add_task(function, *args) → schedules send_welcome_email to run after the response.
    # The client gets their 201 response immediately.
    # send_welcome_email runs in the background after.
    background_tasks.add_task(send_welcome_email, user.email, user.username)

    return user


# dependencies=[Depends(get_current_superuser)] → route-level dependency.
#   This applies the dependency to the whole route WITHOUT injecting its return value
#   into the function. We just want the auth check to run — we don't need the User object.
#   If the user is not a superuser, get_current_superuser raises ForbiddenException
#   and this route never runs.
@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List all users (superuser only)",
    dependencies=[Depends(get_current_superuser)],
)
def list_users(
    # Depends(PaginationParams) → FastAPI reads ?page= and ?size= from the URL
    # and builds a PaginationParams object. No Depends(get_db) needed here
    # because PaginationParams doesn't use the database.
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    # pagination.skip → how many rows to skip (calculated from page and size)
    # pagination.limit → how many rows to return
    return user_crud.get_users(db, skip=pagination.skip, limit=pagination.limit)


# response_model=UserWithItems → returns the user WITH their items list included
@router.get("/me", response_model=UserWithItems, summary="Get current user profile")
def get_me(
    # Depends(get_current_active_user) → calls the dependency chain:
    #   oauth2_scheme (extracts token) → get_current_user (decodes token, fetches user)
    #   → get_current_active_user (checks is_active)
    # The returned User object is injected as current_user.
    current_user: User = Depends(get_current_active_user)
):
    """Returns the authenticated user's profile including their items."""
    # current_user.items → SQLAlchemy automatically loads the related items
    # because of the relationship() defined in the User model
    return current_user


# /{user_id} → path parameter. The value in the URL becomes the user_id argument.
#   GET /users/42 → user_id = 42
@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
def get_user(
    user_id: int,   # FastAPI reads this from the URL path and converts to int
    db: Session = Depends(get_db),

    # _: User → the underscore means "I need this dependency to run (for auth),
    # but I don't need to use the returned value in this function."
    # This is a Python convention for "unused variable".
    _: User = Depends(get_current_active_user),
):
    return user_crud.get_user(db, user_id)


# PATCH → partial update. Only the fields sent in the request body are changed.
#   Different from PUT which replaces the entire resource.
@router.patch("/{user_id}", response_model=UserResponse, summary="Update user")
def update_user(
    user_id: int,
    payload: UserUpdate,   # all fields in UserUpdate are optional
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Users can only update themselves; superusers can update anyone."""
    # Authorization check: you can only update your own profile
    # unless you're a superuser (who can update anyone)
    if current_user.id != user_id and not current_user.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("You can only update your own profile")
    return user_crud.update_user(db, user_id, payload)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    # status_code=200 → DELETE returns 200 OK with a message body.
    # Some APIs return 204 No Content (no body) for deletes.
    # We use 200 so we can include a confirmation message.
    status_code=status.HTTP_200_OK,
    summary="Delete user (superuser only)",
    # Route-level dependency: only superusers can delete users
    dependencies=[Depends(get_current_superuser)],
)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user_crud.delete_user(db, user_id)
    # f-string → embeds user_id into the message string
    return MessageResponse(message=f"User {user_id} deleted successfully")
