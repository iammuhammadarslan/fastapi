"""
app/main.py
-----------
The FastAPI application factory. This is where everything is wired together:
  - App is created with metadata
  - Middleware is added
  - Exception handlers are registered
  - Routers are included
  - Startup/shutdown logic is defined
"""

# asynccontextmanager → a decorator that turns an async generator function
#   into a context manager. Used to define startup/shutdown logic (lifespan).
from contextlib import asynccontextmanager

# FastAPI → the main class. Creating an instance gives you the app.
from fastapi import FastAPI

# CORSMiddleware → handles Cross-Origin Resource Sharing headers.
#   Allows (or blocks) browsers from making requests from different domains.
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.middleware.logging import RequestLoggingMiddleware
from app.websockets.chat import router as ws_router


# ── Lifespan ──────────────────────────────────────────────────────────────────

# @asynccontextmanager → makes this function work as a context manager
# async def lifespan(app: FastAPI) → FastAPI calls this with the app instance
#
# Everything BEFORE yield → runs on STARTUP (when the server starts)
# Everything AFTER yield  → runs on SHUTDOWN (when the server stops with Ctrl+C)
#
# This replaces the old @app.on_event("startup") / @app.on_event("shutdown") decorators
# which are now deprecated in FastAPI.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables defined in our ORM models.
    # Base.metadata → knows about all models that inherit from Base (User, Item, etc.)
    # .create_all(bind=engine) → runs CREATE TABLE IF NOT EXISTS for each model
    # In production, use Alembic migrations instead (more control, supports rollbacks)
    Base.metadata.create_all(bind=engine)
    print(f"✅  {settings.APP_NAME} v{settings.APP_VERSION} started")

    yield  # ← server is running and handling requests while paused here

    # Code here runs when the server is shutting down
    print("🛑  Application shutting down")


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Using a factory function (instead of creating the app at module level) makes
    testing easier — you can call create_app() with different settings in tests.
    """

    # FastAPI() → creates the application instance
    # All these arguments customize the auto-generated API documentation
    app = FastAPI(
        # title → shown at the top of Swagger UI (/docs)
        title=settings.APP_NAME,

        # version → shown in Swagger UI and in the /openapi.json spec
        version=settings.APP_VERSION,

        # description → shown in Swagger UI below the title. Supports Markdown.
        description=(
            "A production-grade FastAPI project covering: "
            "JWT auth, CRUD, Pydantic v2, SQLAlchemy, WebSockets, "
            "file uploads, background tasks, middleware, and more."
        ),

        # docs_url → the URL for Swagger UI (interactive API explorer)
        # Visit http://localhost:8000/docs to see it
        # Set to None to disable Swagger UI in production
        docs_url="/docs",

        # redoc_url → the URL for ReDoc (alternative API documentation UI)
        # Visit http://localhost:8000/redoc to see it
        redoc_url="/redoc",

        # openapi_url → the URL for the raw OpenAPI JSON spec
        # This is what Swagger UI and ReDoc read to generate their UIs
        openapi_url="/openapi.json",

        # lifespan → the startup/shutdown context manager defined above
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # IMPORTANT: Middleware is applied in REVERSE order.
    # The LAST middleware added runs FIRST on incoming requests.
    # So: RequestLoggingMiddleware runs first, then CORSMiddleware.

    # CORSMiddleware → adds CORS headers to every response.
    # Without this, browsers block JavaScript from calling this API from other domains.
    app.add_middleware(
        CORSMiddleware,

        # allow_origins → list of frontend URLs allowed to call this API.
        # ["*"] would allow ALL origins (not recommended for production with credentials).
        allow_origins=settings.ALLOWED_ORIGINS,

        # allow_credentials=True → allows cookies and Authorization headers to be sent.
        # Required for JWT auth from a browser frontend.
        allow_credentials=True,

        # allow_methods=["*"] → allow all HTTP methods (GET, POST, PATCH, DELETE, etc.)
        # You could restrict to ["GET", "POST"] if needed.
        allow_methods=["*"],

        # allow_headers=["*"] → allow all request headers.
        # The Authorization header (for JWT) must be allowed.
        allow_headers=["*"],
    )

    # Our custom logging middleware — logs every request with timing
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception Handlers ────────────────────────────────────────────────────
    # add_exception_handler(ExceptionClass, handler_function)
    # When an exception of that class is raised anywhere in the app,
    # FastAPI calls the handler function instead of returning a generic 500 error.

    # Handles all our custom AppException subclasses (NotFoundException, etc.)
    app.add_exception_handler(AppException, app_exception_handler)

    # Catch-all for any unexpected exception — prevents stack traces leaking to clients
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    # include_router() → mounts a router onto the app.
    # prefix=settings.API_V1_PREFIX → prepends "/api/v1" to all routes in api_router.
    # So auth.router's "/auth/login" becomes "/api/v1/auth/login"
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # WebSocket routes don't use the /api/v1 prefix — they have their own paths
    app.include_router(ws_router)

    # ── Health Check ──────────────────────────────────────────────────────────
    # A simple endpoint to check if the server is running.
    # Used by load balancers, monitoring tools, and Kubernetes liveness probes.
    # tags=["Health"] → groups under "Health" in Swagger UI
    # summary="..." → short description in Swagger UI
    @app.get("/health", tags=["Health"], summary="Health check")
    def health():
        # Returns a simple JSON response — no auth required
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


# Call create_app() to build the app instance.
# This is what uvicorn imports: uvicorn main:app
# (main.py imports this app from app/main.py)
app = create_app()
