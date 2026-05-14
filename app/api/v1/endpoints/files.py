"""
app/api/v1/endpoints/files.py
------------------------------
File upload and download endpoints.
"""

import uuid          # generates unique IDs to avoid filename collisions
from pathlib import Path  # cross-platform file path handling

# aiofiles → async file I/O. Lets you read/write files without blocking the server.
#            Regular open() blocks the event loop; aiofiles doesn't.
import aiofiles

# File      → marks a parameter as a file upload field
# Form      → marks a parameter as a form field (text in a multipart form)
# UploadFile → represents an uploaded file with metadata (filename, content_type, etc.)
# status    → HTTP status code constants
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

# FileResponse → streams a file from disk back to the client as a download
from fastapi.responses import FileResponse

from app.dependencies.auth import get_current_active_user
from app.models.user import User


# prefix="/files" → all routes here start with /files
# tags=["Files"]  → groups under "Files" in Swagger UI
router = APIRouter(prefix="/files", tags=["Files"])

# Path("uploads") → the folder where uploaded files are saved
# .mkdir(exist_ok=True) → creates the folder if it doesn't exist.
#   exist_ok=True → don't raise an error if the folder already exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 5 * 1024 * 1024 = 5,242,880 bytes = 5 MB
# This is the maximum allowed file size
MAX_FILE_SIZE = 5 * 1024 * 1024

# A set of allowed MIME types. Files with other types are rejected.
# MIME type = the file's content type (e.g. "image/jpeg", "application/pdf")
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "application/pdf"}


# async def → this is an async function because it uses `await` for file I/O.
#   FastAPI supports both sync (def) and async (async def) route handlers.
#   Use async def when you do I/O operations (file reads, HTTP calls, etc.)
@router.post("/upload", summary="Upload a single file")
async def upload_file(
    # UploadFile → represents the uploaded file
    # File(...) → marks this as a file upload field in a multipart/form-data request
    # ... (Ellipsis) → the file is required
    # description → shown in Swagger UI
    file: UploadFile = File(..., description="File to upload"),

    # Form() → reads this value from the multipart form body (not JSON, not URL)
    # default="" → description is optional, defaults to empty string
    # You can mix File() and Form() in the same endpoint for multipart forms
    description: str = Form(default="", description="Optional description"),

    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a single file.
    - Validates content type and file size.
    - Saves with a UUID filename to prevent collisions.
    - Returns the saved filename.
    """

    # file.content_type → the MIME type the client reported (e.g. "image/jpeg")
    # We check it against our allowed set to reject unwanted file types
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        # HTTP 415 Unsupported Media Type → the file type is not allowed
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' not allowed. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    # await file.read() → reads the entire file into memory as bytes
    # We use await because file.read() is an async operation
    contents = await file.read()

    # len(contents) → size of the file in bytes
    if len(contents) > MAX_FILE_SIZE:
        # HTTP 413 Request Entity Too Large → file exceeds the size limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Path(file.filename).suffix → extracts the file extension
    # Path("photo.jpg").suffix → ".jpg"
    # Path("document.pdf").suffix → ".pdf"
    extension = Path(file.filename).suffix

    # uuid.uuid4() → generates a random UUID like "550e8400-e29b-41d4-a716-446655440000"
    # Using UUID as the filename prevents:
    #   1. Filename collisions (two users uploading "photo.jpg")
    #   2. Path traversal attacks (user uploading a file named "../../etc/passwd")
    saved_name = f"{uuid.uuid4()}{extension}"

    # UPLOAD_DIR / saved_name → Path object for the full file path
    # The / operator on Path objects joins paths (like os.path.join)
    save_path = UPLOAD_DIR / saved_name

    # async with aiofiles.open(...) → opens the file asynchronously
    # "wb" → write binary mode (files are bytes, not text)
    # We use async with so the file is automatically closed when done
    async with aiofiles.open(save_path, "wb") as out_file:
        # await out_file.write(contents) → writes the bytes to disk asynchronously
        await out_file.write(contents)

    # Return a dict — FastAPI serializes it to JSON automatically
    return {
        "filename": saved_name,
        "original_name": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(contents),
        "description": description,
        "uploaded_by": current_user.username,
    }


@router.post("/upload-multiple", summary="Upload multiple files")
async def upload_multiple_files(
    # list[UploadFile] → accepts multiple files in one request
    # File(...) → all files are required
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """Upload up to 10 files at once."""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per request")

    results = []
    for file in files:
        contents = await file.read()
        extension = Path(file.filename).suffix
        saved_name = f"{uuid.uuid4()}{extension}"
        async with aiofiles.open(UPLOAD_DIR / saved_name, "wb") as f:
            await f.write(contents)
        results.append({"original": file.filename, "saved_as": saved_name})

    return {"uploaded": results}


@router.get("/download/{filename}", summary="Download a file")
def download_file(
    # filename → path parameter from the URL: GET /files/download/abc123.jpg
    filename: str,
    current_user: User = Depends(get_current_active_user),
):
    """Stream a previously uploaded file back to the client."""

    # Path(filename).name → extracts just the filename, stripping any directory parts.
    # This prevents path traversal attacks where a malicious user sends:
    #   filename = "../../etc/passwd"
    # Path("../../etc/passwd").name → "passwd" (safe — just the filename)
    safe_name = Path(filename).name

    # UPLOAD_DIR / safe_name → full path to the file
    file_path = UPLOAD_DIR / safe_name

    # file_path.exists() → checks if the file actually exists on disk
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # FileResponse → streams the file to the client as a download.
    # path     → the file to send
    # filename → the filename the client sees in their download dialog
    # FastAPI sets the correct Content-Type and Content-Disposition headers automatically.
    return FileResponse(path=file_path, filename=safe_name)
