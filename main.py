"""
main.py (root)
--------------
The entry point of the application. This is the file you point uvicorn at.

Why is this separate from app/main.py?
  - app/main.py → contains the FastAPI app factory (create_app)
  - main.py     → is just the entry point that imports the app

This separation means other files can do `from app.main import app`
without accidentally triggering uvicorn.run().

How to run:
  uvicorn main:app --reload
    → "main" = this file (main.py)
    → "app"  = the `app` variable imported below
    → --reload = restart the server automatically when you save a file (dev only)

  fastapi dev main.py
    → same thing, but uses FastAPI's CLI with nicer output
"""

# Import the FastAPI app instance from app/main.py
# This is the object uvicorn needs to run the server
from app.main import app  # noqa: F401 (imported but used by uvicorn, not directly here)


# if __name__ == "__main__" → this block only runs when you execute this file directly:
#   python main.py
# It does NOT run when uvicorn imports this file (uvicorn does its own thing).
# This is a Python convention for "run this only as a script, not as an import".
if __name__ == "__main__":
    import uvicorn

    # uvicorn.run() → starts the ASGI server programmatically
    # "main:app"    → tells uvicorn to import `app` from `main.py`
    #                 (same as running: uvicorn main:app from the terminal)
    # host="0.0.0.0" → listen on all network interfaces (not just localhost).
    #                   Required if you want to access the server from another machine
    #                   or from inside a Docker container.
    # port=8000      → the port to listen on. Visit http://localhost:8000
    # reload=True    → restart the server when files change (development only)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
