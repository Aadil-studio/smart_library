"""Library system settings: staff can read, the administrator can edit."""
from flask import Blueprint

from routes import (admin_required, fail, get_controller, json_body, ok,
                    parse_int, staff_required)

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

EDITABLE = {
    "library_name": str,
    "loan_period_days": int,
    "fine_per_day": int,
    "due_soon_days": int,
}


@settings_bp.get("")
@staff_required
def get_settings():
    return ok(data=get_controller().get_library_settings())


@settings_bp.put("")
@admin_required
def update_settings():
    data = json_body()
    if not any(name in EDITABLE for name in data):
        return fail("Provide at least one setting to update.")
    updates = {}
    for name, value in data.items():
        if name not in EDITABLE:
            continue
        if EDITABLE[name] is int:
            parsed, error = parse_int(value, name, minimum=0, maximum=365 if name != "fine_per_day" else 1000)
            if error:
                return fail(error)
            updates[name] = parsed
        else:
            text = str(value).strip()
            if not text:
                return fail("'library_name' cannot be empty.")
            if len(text) > 60:
                return fail("'library_name' must be at most 60 characters.")
            updates[name] = text
    settings = get_controller().update_library_settings(updates)
    return ok(data=settings, message="Settings saved.")
