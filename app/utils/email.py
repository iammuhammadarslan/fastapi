"""
app/utils/email.py
-------------------
Email utility functions.

These are called from BackgroundTasks (in users.py) so they run AFTER
the HTTP response is sent. The client never waits for emails to send.

In production, replace the print() calls with a real email provider:
  - SendGrid: sendgrid.SendGridAPIClient
  - AWS SES: boto3.client("ses")
  - SMTP: smtplib.SMTP
  - Resend, Mailgun, Postmark, etc.
"""

import logging

# logging.getLogger(__name__) → creates a logger named after this module.
# __name__ is a Python built-in that equals the module's import path.
# For this file: __name__ = "app.utils.email"
# This lets you configure logging per-module (e.g. set app.utils.email to DEBUG level)
logger = logging.getLogger(__name__)


def send_welcome_email(email: str, username: str) -> None:
    """
    Send a welcome email to a newly registered user.

    Called as a background task from create_user() in users.py:
      background_tasks.add_task(send_welcome_email, user.email, user.username)

    This function runs in a thread pool after the HTTP response is sent.
    It's a regular (sync) function — BackgroundTasks handles running it off the main thread.
    """
    # logger.info() → logs at INFO level. Shows up in the console during development.
    # %s → string placeholder (safer than f-strings for logging — avoids formatting errors)
    logger.info("[EMAIL] Sending welcome email to %s (%s)", email, username)

    # Replace this print() with your actual email provider call:
    # e.g. sendgrid_client.send(to=email, subject="Welcome!", body=f"Hi {username}!")
    print(f"[EMAIL] Welcome email sent to {email}")


def send_password_reset_email(email: str, reset_token: str) -> None:
    """
    Send a password-reset link to the user.

    reset_token → a short-lived JWT or random token that proves the user
                  owns this email address. The link expires after a few minutes.
    """
    # Build the reset URL with the token as a query parameter
    reset_url = f"https://yourapp.com/reset-password?token={reset_token}"
    logger.info("[EMAIL] Sending password reset to %s", email)
    print(f"[EMAIL] Password reset link: {reset_url}")
