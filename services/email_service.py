"""SMTP delivery for password-reset verification codes."""
from __future__ import annotations

import html
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

logger = logging.getLogger("uvicorn.error")


def _smtp_password() -> tuple[str, str]:
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    if password:
        return password, "SMTP_PASSWORD"
    password = os.environ.get("SMTP_PASS", "").strip()
    return password, "SMTP_PASS" if password else "missing"


def _smtp_error_detail(error: smtplib.SMTPException, username: str, password: str) -> str:
    code = getattr(error, "smtp_code", None)
    reply = getattr(error, "smtp_error", str(error))
    if isinstance(reply, bytes):
        reply = reply.decode("utf-8", errors="replace")
    detail = " ".join(str(reply).split())
    for secret in (username, password):
        if secret:
            detail = detail.replace(secret, "[redacted]")
    return f"SMTP {code}: {detail}" if code else detail


def smtp_configuration_status() -> dict:
    host = os.environ.get("SMTP_HOST", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip()
    port_value = os.environ.get("SMTP_PORT", "").strip()
    username = os.environ.get("SMTP_USER", "").strip()
    password, password_source = _smtp_password()
    auth_pair_valid = bool(username) == bool(password)
    auth_required = host.casefold() == "smtp.gmail.com"
    try:
        port = int(port_value or "587")
        port_valid = 1 <= port <= 65535
    except ValueError:
        port = None
        port_valid = False

    issues = []
    if not host:
        issues.append("SMTP_HOST is missing")
    if not sender:
        issues.append("SMTP_FROM is missing")
    if not port_valid:
        issues.append("SMTP_PORT must be a valid port from 1 to 65535")
    if not auth_pair_valid:
        issues.append("Set both SMTP_USER and SMTP_PASSWORD (legacy SMTP_PASS is also accepted), or leave both blank")
    elif auth_required and not username:
        issues.append("SMTP_USER and SMTP_PASSWORD are required when SMTP_HOST is smtp.gmail.com")

    return {
        "smtp_host_detected": bool(host),
        "smtp_port_detected": bool(port_value),
        "smtp_port_valid": port_valid,
        "smtp_port_defaulted": not bool(port_value),
        "smtp_port_effective": port,
        "smtp_sender_detected": bool(sender),
        "smtp_username_detected": bool(username),
        "smtp_password_detected": bool(password),
        "smtp_password_source": password_source,
        "smtp_auth_required": auth_required,
        "smtp_auth_pair_valid": auth_pair_valid,
        "ready": not issues,
        "issues": issues,
    }


def smtp_configured() -> bool:
    return smtp_configuration_status()["ready"]


def _connect(host: str, port: int):
    """Open SMTP using implicit TLS on 465 and STARTTLS on other secure ports."""
    if port == 465:
        return smtplib.SMTP_SSL(host, port, timeout=10, context=ssl.create_default_context())
    server = smtplib.SMTP(host, port, timeout=10)
    if port != 25:
        server.starttls(context=ssl.create_default_context())
    return server


def send_otp_email(to_email: str, otp: str, reset_url: str | None = None) -> tuple[bool, str]:
    status = smtp_configuration_status()
    if not status["ready"]:
        return False, "Email delivery is not configured: " + "; ".join(status["issues"]) + "."

    host = os.environ["SMTP_HOST"].strip()
    sender = os.environ["SMTP_FROM"].strip()
    username = os.environ.get("SMTP_USER", "").strip()
    password, _password_source = _smtp_password()
    port = status["smtp_port_effective"]
    if host.casefold() == "smtp.gmail.com":
        password = "".join(password.split())

    code = html.escape(otp)
    reset_link = ""
    text_reset_link = ""
    if reset_url:
        safe_url = html.escape(reset_url, quote=True)
        reset_link = (
            '<p style="margin:24px 0 0"><a href="' + safe_url + '" '
            'style="color:#f2b84b">Continue password reset</a></p>'
        )
        text_reset_link = f"\n\nContinue your password reset here: {reset_url}"

    message = EmailMessage()
    message["Subject"] = "Smart Library password reset code"
    message["From"] = formataddr(("Smart Library", sender))
    message["To"] = to_email
    message.set_content(
        f"Your Smart Library password reset code is {otp}.\n\n"
        f"It expires in 10 minutes. If you did not request this code, you can ignore this email."
        f"{text_reset_link}"
    )
    message.add_alternative(
        f"""\
<!doctype html>
<html lang="en">
  <body style="margin:0;background:#0b1020;color:#e8ecff;font-family:Arial,sans-serif">
    <div style="max-width:560px;margin:32px auto;padding:32px;background:#141a33;border:1px solid #2a3560;border-radius:16px">
      <p style="margin:0 0 8px;color:#f2b84b;font-size:13px;font-weight:bold;letter-spacing:1px">NORTHSTAR LIBRARY</p>
      <h1 style="margin:0 0 16px;font-size:24px">Password reset</h1>
      <p style="color:#c4cbea;line-height:1.6">Use this verification code to reset your password:</p>
      <p style="margin:24px 0;padding:16px;text-align:center;background:#0b1020;border-radius:10px;color:#f2b84b;font-size:32px;font-weight:bold;letter-spacing:8px">{code}</p>
      <p style="color:#97a1cc;line-height:1.6">This code expires in 10 minutes and can only be used once. If you did not request a password reset, ignore this email.</p>
      {reset_link}
    </div>
  </body>
</html>
""",
        subtype="html",
    )

    try:
        with _connect(host, port) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
        return True, "A verification code has been emailed to you."
    except smtplib.SMTPAuthenticationError as exc:
        detail = _smtp_error_detail(exc, username, password)
        logger.error("SMTP authentication rejected by %s: %s", host, detail)
        if host.casefold() == "smtp.gmail.com":
            return False, (
                "Email delivery failed: Gmail rejected SMTP authentication. "
                "Use the full Gmail address for SMTP_USER and a 16-character Google App Password "
                "for SMTP_PASSWORD (not your regular Gmail password)."
            )
        return False, "Email delivery failed: the mail server rejected SMTP authentication. Check SMTP_USER and SMTP_PASSWORD."
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending the OTP email to %s: %s", host, _smtp_error_detail(exc, username, password))
        return False, "Email delivery failed. Check the SMTP server settings and try again."
    except OSError as exc:
        logger.error("Could not reach the SMTP server %s:%s: %s", host, port, exc)
        return False, "Email delivery failed: the mail server is unreachable."
