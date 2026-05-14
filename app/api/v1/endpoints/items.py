"""
app/api/v1/endpoints/items.py
------------------------------
Item CRUD endpoints.
"""

# Query → used to define query parameters (from the URL ?key=value)
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import item as item_crud
from app.dependencies.auth import get_current_active_user
from app.dependencies.pagination import PaginationParams
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate


# prefix="/items" → all routes here start with /items
#   Full path (with app prefix): /api/v1/items
# tags=["Items"]  → groups these routes under "Items" in Swagger UI
router = APIRouter(prefix="/items", tags=["Items"])


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,  # 201 = Created (standard for POST that creates a resource)
    summary="Create a new item",
)
def create_item(
    payload: ItemCreate,   # JSON request body, validated by Pydantic
    db: Session = Depends(get_db),
    # We need the current user to set owner_id on the new item
    current_user: User = Depends(get_current_active_user),
):
    # owner_id=current_user.id → the item is owned by whoever is logged in
    return item_crud.create_item(db, payload, owner_id=current_user.id)


@router.get("/", response_model=list[ItemResponse], summary="List all items")
def list_items(
    pagination: PaginationParams = Depends(),

    # Query() → defines a query parameter from the URL
    # False → default value if ?available_only= is not in the URL
    # description → shown in Swagger UI to explain this parameter
    # Example URL: GET /items?available_only=true&page=1&size=20
    available_only: bool = Query(False, description="Filter to only available items"),

    db: Session = Depends(get_db),

    # _: User → we need auth (user must be logged in) but don't use the user object
    _: User = Depends(get_current_active_user),
):
    items = item_crud.get_items(db, skip=pagination.skip, limit=pagination.limit)

    # If available_only=true was in the URL, filter the list in Python.
    # In production with large datasets, you'd add this filter to the SQL query instead.
    if available_only:
        items = [i for i in items if i.is_available]

    return items


@router.get("/mine", response_model=list[ItemResponse], summary="List my items")
def list_my_items(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # owner_id=current_user.id → only return items owned by the logged-in user
    return item_crud.get_items_by_owner(
        db, owner_id=current_user.id, skip=pagination.skip, limit=pagination.limit
    )


# /{item_id} → path parameter. GET /items/5 → item_id = 5
@router.get("/{item_id}", response_model=ItemResponse, summary="Get item by ID")
def get_item(
    item_id: int,   # FastAPI reads from URL path and converts to int
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),  # auth required, user object not needed
):
    return item_crud.get_item(db, item_id)


# PATCH → partial update. Only fields sent in the body are changed.
@router.patch("/{item_id}", response_model=ItemResponse, summary="Update item")
def update_item(
    item_id: int,
    payload: ItemUpdate,   # all fields optional — only sent fields are updated
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # current_user_id → passed to the CRUD function for ownership check
    # Only the item's owner can update it (checked inside update_item)
    return item_crud.update_item(db, item_id, payload, current_user_id=current_user.id)


@router.delete(
    "/{item_id}",
    response_model=MessageResponse,  # returns {"message": "Item 5 deleted successfully"}
    summary="Delete item",
)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # current_user_id → passed for ownership check inside delete_item
    item_crud.delete_item(db, item_id, current_user_id=current_user.id)
    return MessageResponse(message=f"Item {item_id} deleted successfully")
