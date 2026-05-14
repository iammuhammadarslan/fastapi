"""
app/crud/item.py
----------------
CRUD operations for Item.
All database logic for items lives here — routes just call these functions.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


def get_item(db: Session, item_id: int) -> Item:
    """Fetch a single item by ID. Raises NotFoundException if not found."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise NotFoundException(f"Item with id={item_id} not found")
    return item


def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[Item]:
    """
    Fetch all items with pagination.
    .offset(skip) → skip the first N rows
    .limit(limit) → return at most N rows
    .all()        → execute and return as a list
    """
    return db.query(Item).offset(skip).limit(limit).all()


def get_items_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> list[Item]:
    """
    Fetch only items belonging to a specific user.
    .filter(Item.owner_id == owner_id) → adds WHERE owner_id = ? to the SQL query
    """
    return (
        db.query(Item)
        .filter(Item.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_item(db: Session, payload: ItemCreate, owner_id: int) -> Item:
    """
    Create a new item owned by the given user.

    **payload.model_dump() → converts the Pydantic ItemCreate schema to a dict:
      {"title": "...", "description": "...", "price": 9.99, "is_available": True}
    **dict → unpacks the dict as keyword arguments to Item():
      Item(title="...", description="...", price=9.99, is_available=True)
    We then add owner_id separately (it's not in the schema — it comes from the auth token).
    """
    item = Item(**payload.model_dump(), owner_id=owner_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item_id: int, payload: ItemUpdate, current_user_id: int) -> Item:
    """
    Update an item. Only the owner can update their own items.

    current_user_id → the ID of the logged-in user (from the JWT token)
    item.owner_id   → the ID of the user who created this item

    If they don't match, raise ForbiddenException (HTTP 403).
    Note: superuser bypass is handled at the route level, not here.
    """
    item = get_item(db, item_id)

    # Ownership check — only the owner can update their item
    if item.owner_id != current_user_id:
        raise ForbiddenException("You do not own this item")

    # model_dump(exclude_unset=True) → only update fields the client actually sent.
    # If the client sends {"price": 19.99}, only price is updated.
    # title, description, is_available are left unchanged.
    for field, value in payload.model_dump(exclude_unset=True).items():
        # setattr(item, "price", 19.99) → same as item.price = 19.99
        # but works when the field name is a variable string
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: int, current_user_id: int) -> None:
    """Delete an item. Only the owner can delete their own items."""
    item = get_item(db, item_id)

    if item.owner_id != current_user_id:
        raise ForbiddenException("You do not own this item")

    db.delete(item)
    db.commit()
