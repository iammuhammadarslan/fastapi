"""
app/core/database.py
--------------------
Sets up the SQLAlchemy database connection.
Three things are created here and imported everywhere else:
  - engine       → the actual connection to the database
  - SessionLocal → a factory that creates new DB sessions
  - Base         → the parent class all ORM models inherit from
"""

# create_engine → creates the database connection (the "engine")
from sqlalchemy import create_engine

# sessionmaker   → a factory for creating Session objects
# DeclarativeBase → the base class for all ORM models
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


# SQLite has a limitation: by default it only allows one thread to use a connection.
# check_same_thread=False disables that restriction so FastAPI (which is multi-threaded) can use it.
# For PostgreSQL/MySQL this is not needed, so we only add it for SQLite.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

# create_engine() sets up the connection pool to the database.
# settings.DATABASE_URL → the connection string (e.g. "sqlite:///./app.db")
# connect_args          → extra arguments passed to the underlying DB driver
# echo=settings.DEBUG   → when True, SQLAlchemy prints every SQL query it runs.
#                          Very useful for learning and debugging. Turn off in production.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

# sessionmaker() creates a Session CLASS (not an instance yet).
# Every time you call SessionLocal(), you get a new session object.
# autocommit=False → you must explicitly call db.commit() to save changes.
#                    This gives you control — if something fails, you can rollback.
# autoflush=False  → don't automatically send pending changes to the DB before queries.
#                    Gives you more control over when SQL is actually executed.
# bind=engine      → tells sessions which database engine to use
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    The base class that all ORM models (User, Item, etc.) must inherit from.
    SQLAlchemy uses this to track which classes are database tables.
    When you call Base.metadata.create_all(engine), it creates all tables
    for every class that inherits from Base.
    """
    pass


def get_db():
    """
    A FastAPI dependency that provides a database session to route handlers.

    How it works:
    1. FastAPI sees `db: Session = Depends(get_db)` in a route function
    2. FastAPI calls get_db() before calling the route
    3. get_db() opens a new session and YIELDS it (pauses here)
    4. FastAPI injects that session into the route as `db`
    5. The route runs and uses `db` to query the database
    6. After the route finishes (or if an error occurs), execution resumes after yield
    7. The finally block ALWAYS runs — it closes the session and returns it to the pool

    The try/finally pattern guarantees the session is always closed,
    even if the route raises an exception. This prevents connection leaks.
    """
    db = SessionLocal()   # open a new database session
    try:
        yield db          # give the session to the route handler
    finally:
        db.close()        # always close the session when done
