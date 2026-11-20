"""Email delivery for password-reset OTPs — the ONLY place OTP email sending is configured.

How it works (no demo / fake OTP anywhere):
  * Enter your SMTP credentials in the FILE SETTINGS block below (easiest),
    or in the .env file — file settings win when both are filled.
  * When SMTP is configured, the 6-digit code is emailed automatically to the
    user's own email address the moment they submit the forgot-password form.
  * If SMTP is not configured, delivery simply fails with an honest error —
    no code is ever faked, printed, or auto-verified.

Supported servers:
  * port 465 -> implicit SSL/TLS (Gmail: smtp.gmail.com:465)
  * port 587 -> STARTTLS (Gmail: smtp.gmail.com:587)
  * port 25  -> plain SMTP on the local network (no TLS)

Gmail setup: enable 2-Step Verification, then create an App Password at
https://myaccount.google.com/apppasswords and paste the 16-character code
into SMTP_PASSWORD below (never your normal Gmail login password).
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

# =========================================================================
# FILE SETTINGS — enter your SMTP credentials here (leave "" to use .env)
# =========================================================================
SMTP_HOSTNAME = ""          # e.g. "smtp.gmail.com"
SMTP_PORT_NUMBER = 0        # e.g. 465 (Gmail SSL) or 587 (STARTTLS)
SMTP_SENDER_EMAIL = ""      # e.g. "yourgmail@gmail.com" (same as SMTP_USERNAME for Gmail)
SMTP_USERNAME = ""          # e.g. "yourgmail@gmail.com"
SMTP_PASSWORD = ""          # e.g. "abcdefghijklmnop" (16-char Gmail App Password, no spaces)
# =========================================================================

logger = logging.getLogger("uvicorn.error")


def _apply_file_settings() -> None:
    """Push the FILE SETTINGS above into the environment so the whole app
    (including the auth route's delivery check) sees them. Values already
    set in the environment/.env keep priority only when the file is empty."""
    for key, value in (
        ("SMTP_HOST", SMTP_HOSTNAME),
        ("SMTP_FROM", SMTP_SENDER_EMAIL),
        ("SMTP_USER", SMTP_USERNAME),
        ("SMTP_PASS", SMTP_PASSWORD),
    ):
        if value and not os.environ.get(key):
            os.environ[key] = str(value)
    if SMTP_PORT_NUMBER and not os.environ.get("SMTP_PORT"):
        os.environ["SMTP_PORT"] = str(SMTP_PORT_NUMBER)


_apply_file_settings()


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def _connect(host: str, port: int) -> smtplib.SMTP:
    """Open the SMTP connection with the right TLS mode for the port."""
    if port == 465:
        # Implicit TLS from the first byte (Gmail's recommended port).
        return smtplib.SMTP_SSL(host, port, timeout=10)
    server = smtplib.SMTP(host, port, timeout=10)
    if port != 25:
        # STARTTLS is upgraded in place; smtplib negotiates EHLO automatically.
        server.starttls()
    return server


def send_otp_email(to_email: str, otp: str, reset_url: str | None = None) -> tuple[bool, str]:
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("SMTP_FROM")
    if not host or not sender:
        return False, "Email delivery is not configured."
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        return False, "Email delivery is not configured correctly."
    if not 1 <= port <= 65535:
        return False, "Email delivery is not configured correctly."

    reset_link = f"\n\nContinue your password reset here: {reset_url}" if reset_url else ""
    message = MIMEText(
        f"Your Smart Library verification code is {otp}.\n\n"
        f"It expires in 10 minutes. If you did not request it, ignore this email."
        f"{reset_link}",
        "plain",
        "utf-8",
    )
    message["Subject"] = "Smart Library — Password Reset Code"
    message["From"] = formataddr(("Smart Library", sender))
    message["To"] = to_email

    try:
        with _connect(host, port) as server:
            user = os.environ.get("SMTP_USER")
            if user:
                server.login(user, os.environ.get("SMTP_PASS", ""))
            server.sendmail(sender, [to_email], message.as_string())
        return True, "A verification code has been emailed to you."
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP login failed for user %s — check SMTP_USER / SMTP_PASS "
                     "(for Gmail, use a 16-character App Password, not your login password).", os.environ.get("SMTP_USER"))
        return False, "Email delivery failed: the mail server rejected the login."
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending the OTP email: %s", exc)
        return False, "Email delivery failed."
    except OSError as exc:
        logger.error("Could not reach the SMTP server %s:%s — %s", host, port, exc)
        return False, "Email delivery failed: mail server unreachable."
