"""
app/dependencies/pagination.py
-------------------------------
A reusable pagination dependency.

Instead of adding ?page= and ?size= query parameters to every single route,
we define them once here and inject them with Depends(PaginationParams).

Usage in a route:
    @router.get("/items")
    def list_items(pagination: PaginationParams = Depends()):
        items = crud.get_items(db, skip=pagination.skip, limit=pagination.limit)

The client calls: GET /items?page=2&size=10
FastAPI reads the query params and builds a PaginationParams object automatically.
"""

# Query → used to define query parameters with validation rules and documentation
from fastapi import Query

# BaseModel → base class for Pydantic models
from pydantic import BaseModel


class PaginationParams(BaseModel):
    """
    Holds pagination parameters extracted from the URL query string.

    When used with Depends(), FastAPI reads ?page= and ?size= from the URL
    and validates them against the rules defined in Query().
    """

    # Query() → marks this as a query parameter (from the URL, not the request body)
    # default=1  → if ?page= is not in the URL, use 1
    # ge=1       → "greater than or equal to 1". Page 0 or negative pages are invalid.
    # description → shown in Swagger UI to explain what this parameter does
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)")

    # default=20 → return 20 items per page if ?size= is not specified
    # ge=1       → must request at least 1 item
    # le=100     → cannot request more than 100 items at once (prevents abuse)
    size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def skip(self) -> int:
        """
        Calculates how many rows to skip in the database query.
        This is how SQL pagination works: OFFSET skip LIMIT size

        Page 1, size 20 → skip 0  (rows 1-20)
        Page 2, size 20 → skip 20 (rows 21-40)
        Page 3, size 20 → skip 40 (rows 41-60)

        Formula: (page - 1) * size
        """
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """
        Returns the number of rows to fetch. Same as size.
        Named 'limit' to match SQLAlchemy's .limit() method name.
        """
        return self.size
