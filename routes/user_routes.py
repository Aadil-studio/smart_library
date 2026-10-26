"""Administrator user management and the system-wide activity log."""
from flask import Blueprint, request

from routes import (admin_required, current_user, fail, get_controller, json_body, ok)

user_bp = Blueprint("users", __name__, url_prefix="/api/users")


@user_bp.get("")
@admin_required
def list_users():
    controller = get_controller()
    role = request.args.get("role", "").strip().lower() or None
    if role not in (None, "student", "librarian", "admin"):
        return fail("Role must be 'student', 'librarian' or 'admin'.")
    status = request.args.get("status", "").strip().lower() or None
    search = request.args.get("q", "").strip() or None
    users = controller.list_all_users(role=role, search=search, status=status)
    return ok(data={"users": users})


@user_bp.put("/<user_id>/role")
@admin_required
def set_role(user_id):
    controller = get_controller()
    data = json_body()
    role = str(data.get("role", "")).strip().lower()
    if role not in ("student", "librarian", "admin"):
        return fail("Role must be 'student', 'librarian' or 'admin'.")
    success, message = controller.set_user_role(user_id, role, current_user()["user_id"])
    if not success:
        return fail(message, 409)
    return ok(data={"user": controller.get_user(user_id)}, message=message)


@user_bp.put("/<user_id>/status")
@admin_required
def set_status(user_id):
    controller = get_controller()
    user = controller.get_user(user_id)
    if not user:
        return fail("User not found.", 404)
    status = str(json_body().get("status", "")).strip().lower()
    if status not in ("active", "inactive"):
        return fail("Status must be 'active' or 'inactive'.")
    if user_id == current_user()["user_id"]:
        return fail("You cannot change your own account status.", 409)
    if user["status"] == status:
        return ok(data={"user": user}, message=f"Account is already {status}.")
    _, message = controller.set_user_status(user_id, status)
    return ok(data={"user": controller.get_user(user_id)}, message=message)


@user_bp.get("/<user_id>")
@admin_required
def get_user(user_id):
    controller = get_controller()
    user = controller.get_user(user_id)
    if not user:
        return fail("User not found.", 404)
    payload = {
        "user": user,
        "borrow_history": controller.borrow_dao.get_student_borrowed_books(user_id),
        "fines": controller.borrow_dao.get_student_fines(user_id),
    }
    if user["role"] == "student":
        payload["reservations"] = controller.reservation_dao.list_reservations(student_id=user_id)
    return ok(data=payload)


activity_bp = Blueprint("activity", __name__, url_prefix="/api/activity-logs")


@activity_bp.get("")
@admin_required
def activity_logs():
    controller = get_controller()
    try:
        limit = min(500, max(1, int(request.args.get("limit", 200))))
    except ValueError:
        limit = 200
    action = request.args.get("action", "").strip().upper() or None
    search = request.args.get("q", "").strip().lower() or None
    logs = controller.user_dao.get_all_activity_logs(limit=limit)
    if action:
        logs = [log for log in logs if log.get("action") == action]
    if search:
        logs = [log for log in logs if search in (log.get("details") or "").lower()
                or search in (log.get("user_name") or "").lower()
                or search in (log.get("user_id") or "").lower()]
    actions = sorted({log.get("action") for log in controller.user_dao.get_all_activity_logs(limit=500)
                      if log.get("action")})
    return ok(data={"logs": logs, "actions": actions})
