from flask import Blueprint

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, password_problem, require_fields)

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.get("")
@login_required
def get_profile():
    controller = get_controller()
    user = current_user()
    return ok(data={
        "profile": controller.get_user(user["user_id"]),
        "preferences": controller.get_preferences(user["user_id"]),
        "stats": {
            "borrowed_total": len(controller.borrow_dao.get_student_borrowed_books(user["user_id"])),
            "active_loans": len(controller.borrow_dao.get_student_borrowed_books(user["user_id"], active_only=True)),
        },
    })


@profile_bp.put("")
@login_required
def update_profile():
    controller = get_controller()
    user = current_user()
    data = json_body()
    if not str(data.get("name", "")).strip():
        return fail("'name' cannot be empty.")
    success, message = controller.update_profile(
        user["user_id"],
        name=str(data.get("name")).strip(),
        phone=str(data.get("phone", "") or "").strip(),
        department=str(data.get("department", "") or "").strip(),
        semester=str(data.get("semester", "") or "").strip(),
    )
    if not success:
        return fail(message, 409)
    refreshed = controller.get_user(user["user_id"])
    from flask import session
    session["user"] = refreshed
    return ok(data={"profile": refreshed}, message=message)


@profile_bp.put("/password")
@login_required
def change_password():
    controller = get_controller()
    user = current_user()
    data = json_body()
    error = require_fields(data, "current_password", "new_password", "confirm_password")
    if error:
        return fail(error)
    if data["new_password"] != data["confirm_password"]:
        return fail("New passwords do not match.")
    if data["current_password"] == data["new_password"]:
        return fail("The new password must be different from the current one.")
    if problem := password_problem(data["new_password"]):
        return fail(problem)
    success, message = controller.change_password(user["user_id"], data["current_password"], data["new_password"])
    if not success:
        return fail(message, 403)
    return ok(message=message)


@profile_bp.put("/preferences")
@login_required
def update_preferences():
    controller = get_controller()
    user = current_user()
    data = json_body()
    current = controller.get_preferences(user["user_id"])
    if "due_reminders" in data:
        current["due_reminders"] = bool(data["due_reminders"])
    success, message = controller.set_preferences(user["user_id"], current)
    return ok(data={"preferences": controller.get_preferences(user["user_id"])}, message=message)
