"""
app/api/v1/router.py
---------------------
The central v1 API router. This is the "hub" that connects all endpoint routers.

Instead of registering every route directly on the main FastAPI app,
we group them into routers (one per feature) and include them all here.
Then app/main.py includes this single api_router.

This keeps app/main.py clean and makes it easy to add new feature routers.
"""

# APIRouter → creates a router that can hold other routers (a "parent" router)
from fastapi import APIRouter

# Import each feature's router module
from app.api.v1.endpoints import auth, background, files, items, users


# Create the top-level v1 router.
# No prefix here — the prefix "/api/v1" is added in app/main.py when this is included.
api_router = APIRouter()

# include_router() → mounts a child router onto this parent router.
# Each child router already has its own prefix (e.g. auth.router has prefix="/auth").
# So the final paths are:
#   auth.router     → /api/v1/auth/login, /api/v1/auth/refresh, /api/v1/auth/logout
#   users.router    → /api/v1/users/, /api/v1/users/me, /api/v1/users/{id}
#   items.router    → /api/v1/items/, /api/v1/items/mine, /api/v1/items/{id}
#   files.router    → /api/v1/files/upload, /api/v1/files/download/{filename}
#   background.router → /api/v1/tasks/generate-report
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(items.router)
api_router.include_router(files.router)
api_router.include_router(background.router)
