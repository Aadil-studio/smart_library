"""Shared helpers for the FastAPI layer: JSON responses, access checks, input validation."""
import re
from collections.abc import Callable
from functools import wraps
from json import JSONDecodeError

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ok(data=None, message=""):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return JSONResponse(content=body, status_code=200)


def fail(message, status=400):
    return JSONResponse(content={"success": False, "message": message}, status_code=status)


def get_controller(request: Request):
    return request.app.state.library_controller


def current_user(request: Request | None = None):
    if request is None:
        return None
    session = getattr(request, "session", None)
    if session is None:
        return None
    session_user = session.get("user")
    if not isinstance(session_user, dict) or not session_user.get("user_id"):
        return None
    controller = getattr(request.app.state, "library_controller", None)
    user = controller.get_user(session_user["user_id"]) if controller else None
    if not user or user.get("status") != "active":
        session.clear()
        return None
    if user != session_user:
        session["user"] = user
    return user


async def json_body(request: Request):
    try:
        data = await request.json()
    except (JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(
            status_code=400,
            detail={"message": "Request body must be a valid JSON object."},
        ) from error
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=400,
            detail={"message": "Request body must be a valid JSON object."},
        )
    return data


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


def parse_float(data, field, minimum=None, maximum=None):
    """Returns (value, error). Accepts either a dict or a raw scalar value."""
    value = data.get(field) if isinstance(data, dict) else data
    if value is None or value == "":
        return None, None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"'{field}' must be a number."
    if minimum is not None and number < minimum:
        return None, f"'{field}' must be at least {minimum}."
    if maximum is not None and number > maximum:
        return None, f"'{field}' must be at most {maximum}."
    return number, None


async def _require_role(request: Request, role: str | tuple[str, ...], message: str):
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
    allowed = (role,) if isinstance(role, str) else role
    if user.get("role") not in allowed:
        raise HTTPException(status_code=403, detail={"message": message})
    return user


async def login_required(request: Request):
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
    return user


async def staff_required(request: Request):
    return await _require_role(request, ("admin", "librarian"),
                              "You do not have permission to perform this action.")


async def admin_required(request: Request):
    return await _require_role(request, "admin", "Administrator access is required for this action.")


# Backwards-compatible decorator support for older Flask-style callers.
def login_required_decorator(fn: Callable):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if request is None:
            raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
        return await fn(*args, **kwargs)
    return wrapper


def staff_required_decorator(fn: Callable):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if request is None:
            raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
        if user.get("role") not in ("admin", "librarian"):
            raise HTTPException(status_code=403, detail={"message": "You do not have permission to perform this action."})
        return await fn(*args, **kwargs)
    return wrapper


def admin_required_decorator(fn: Callable):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if request is None:
            raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=401, detail={"message": "Authentication required. Please sign in."})
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail={"message": "Administrator access is required for this action."})
        return await fn(*args, **kwargs)
    return wrapper
