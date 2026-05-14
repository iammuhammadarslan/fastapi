"""
app/api/v1/endpoints/background.py
------------------------------------
Demonstrates FastAPI's BackgroundTasks — running work after the response is sent.

Use case: anything that takes time but the client doesn't need to wait for.
Examples: sending emails, generating reports, resizing images, calling external APIs.
"""

import time  # used to simulate a slow job with time.sleep()

from fastapi import APIRouter, BackgroundTasks, Depends

from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.auth import MessageResponse


# prefix="/tasks" → all routes here start with /tasks
#   Full path: /api/v1/tasks
# tags=["Background Tasks"] → groups under "Background Tasks" in Swagger UI
router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


def _heavy_report_job(user_email: str, report_type: str) -> None:
    """
    Simulates a slow background job (e.g. generating a PDF report).

    This is a regular function (not async) — BackgroundTasks runs it in a thread pool
    so it doesn't block the async event loop.

    In a real app, this would:
    - Query the database for data
    - Generate a PDF or CSV
    - Upload it to S3
    - Send an email with the download link

    The leading underscore (_) in the name is a Python convention meaning
    "this is a private/internal function, not meant to be called from outside this module".
    """
    time.sleep(3)  # simulate 3 seconds of work
    print(f"[BG] Report '{report_type}' generated and sent to {user_email}")


@router.post("/generate-report", response_model=MessageResponse)
def generate_report(
    # report_type → a query parameter from the URL: POST /tasks/generate-report?report_type=monthly
    # "summary" → default value if not provided in the URL
    report_type: str = "summary",

    # BackgroundTasks → FastAPI injects this automatically.
    # You call .add_task() to schedule a function to run after the response is sent.
    # BackgroundTasks() → creates a new instance as the default value.
    background_tasks: BackgroundTasks = BackgroundTasks(),

    current_user: User = Depends(get_current_active_user),
):
    """
    Kick off a background report job.

    Timeline:
    1. Client sends POST /tasks/generate-report
    2. FastAPI runs this function
    3. background_tasks.add_task() schedules _heavy_report_job
    4. FastAPI sends the HTTP response IMMEDIATELY (the client gets it in milliseconds)
    5. AFTER the response is sent, _heavy_report_job runs (takes 3 seconds)

    The client doesn't wait for the job to finish.
    """

    # add_task(function, *args) → schedules the function to run after the response.
    # The arguments after the function are passed to the function as positional args.
    # So this calls: _heavy_report_job(current_user.email, report_type)
    background_tasks.add_task(_heavy_report_job, current_user.email, report_type)

    # This response is sent immediately — before _heavy_report_job even starts
    return MessageResponse(
        message=f"Report '{report_type}' is being generated. You'll receive it by email."
    )
