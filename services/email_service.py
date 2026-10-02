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


def send_otp_email(to_email: str, otp: str) -> tuple[bool, str]:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ.get("SMTP_FROM")
    try:
        message = MIMEText(
            f"Your Smart Library verification code is {otp}.\n\n"
            f"It expires in 10 minutes. If you did not request it, ignore this email.",
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
    except Exception:
        return False, "Email delivery failed."
