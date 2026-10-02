"""Shared helpers for the API layer: JSON responses, access decorators, input validation."""
import re
from functools import wraps

from flask import current_app, jsonify, request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ok(data=None, message=""):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return jsonify(body)


def fail(message, status=400):
    return jsonify({"success": False, "message": message}), status


def get_controller():
    return current_app.extensions["library_controller"]


def current_user():
    return request.environ.get("library_user")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return fail("Authentication required. Please sign in.", 401)
        return fn(*args, **kwargs)
    return wrapper


def staff_required(fn):
    """Admin and librarian accounts — book/borrow/reservation management."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return fail("Authentication required. Please sign in.", 401)
        if user["role"] not in ("admin", "librarian"):
            return fail("You do not have permission to perform this action.", 403)
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return fail("Authentication required. Please sign in.", 401)
        if user["role"] != "admin":
            return fail("Administrator access is required for this action.", 403)
        return fn(*args, **kwargs)
    return wrapper


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def require_fields(data, *names):
    """Return an error string for the first missing/blank field, else None."""
    for name in names:
        value = data.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"'{name}' is required."
    return None


def valid_email(email) -> bool:
    return bool(email) and bool(EMAIL_RE.match(str(email)))


def password_problem(password) -> str | None:
    """Returns an error message, or None when the password satisfies the policy."""
    if not password or len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain both letters and numbers."
    return None


def parse_int(value, field, minimum=None, maximum=None):
    """Returns (value, error). Non-numeric or out-of-range input is rejected."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"'{field}' must be a whole number."
    if minimum is not None and number < minimum:
        return None, f"'{field}' must be at least {minimum}."
    if maximum is not None and number > maximum:
        return None, f"'{field}' must be at most {maximum}."
    return number, None
