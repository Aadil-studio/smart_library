"""Email delivery for password-reset OTPs.

If SMTP settings are present in the environment the code is emailed; otherwise the
controller falls back to development mode (OTP returned in the API response only
when OTP_DEV_MODE=1). No real credentials are ever stored in source code.
"""
import os
import smtplib
from email.mime.text import MIMEText


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


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
    try:
        reset_link = f"\n\nContinue your password reset here: {reset_url}" if reset_url else ""
        message = MIMEText(
            f"Your Smart Library verification code is {otp}.\n\n"
            f"It expires in 10 minutes. If you did not request it, ignore this email."
            f"{reset_link}",
            "plain",
            "utf-8",
        )
        message["Subject"] = "Smart Library — Password Reset Code"
        message["From"] = sender
        message["To"] = to_email

        with smtplib.SMTP(host, port, timeout=10) as server:
            if os.environ.get("SMTP_USER"):
                server.starttls()
                server.login(os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS", ""))
            server.sendmail(sender, [to_email], message.as_string())
        return True, "A verification code has been emailed to you."
    except (OSError, smtplib.SMTPException, TypeError, ValueError):
        return False, "Email delivery failed."
