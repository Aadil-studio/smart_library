"""Library system settings: staff can read, the administrator can edit."""
from fastapi import APIRouter, Depends, Request

from routes import (admin_required, fail, get_controller, json_body, ok,
                    parse_int, staff_required)

router = APIRouter(prefix="/api/settings")

EDITABLE = {
    "library_name": str,
    "loan_period_days": int,
    "fine_per_day": int,
    "due_soon_days": int,
    "book_fee": int,
}


@router.get("")
async def get_settings(request: Request, user: dict = Depends(staff_required)):
    return ok(data=get_controller(request).get_library_settings())


@router.put("")
async def update_settings(request: Request, user: dict = Depends(admin_required)):
    data = await json_body(request)
    if not any(name in EDITABLE for name in data):
        return fail("Provide at least one setting to update.")
    updates = {}
    for name, value in data.items():
        if name not in EDITABLE:
            continue
        if EDITABLE[name] is int:
            if name == "book_fee":
                parsed, error = parse_int(value, name, minimum=0, maximum=100000)
            else:
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
    settings = get_controller(request).update_library_settings(updates)
    return ok(data=settings, message="Settings saved.")
