"""Administrator user management and the system-wide activity log."""
from fastapi import APIRouter, Depends, Request

from routes import (admin_required, fail, get_controller, json_body, ok)

router = APIRouter(prefix="/api/users")


@router.get("")
async def list_users(request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    role = request.query_params.get("role", "").strip().lower() or None
    if role not in (None, "student", "librarian", "admin"):
        return fail("Role must be 'student', 'librarian' or 'admin'.")
    status = request.query_params.get("status", "").strip().lower() or None
    search = request.query_params.get("q", "").strip() or None
    users = controller.list_all_users(role=role, search=search, status=status)
    return ok(data={"users": users})


@router.put("/{user_id}/role")
async def set_role(user_id: str, request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    data = await json_body(request)
    role = str(data.get("role", "")).strip().lower()
    if role not in ("student", "librarian", "admin"):
        return fail("Role must be 'student', 'librarian' or 'admin'.")
    success, message = controller.set_user_role(user_id, role, user["user_id"])
    if not success:
        return fail(message, 409)
    return ok(data={"user": controller.get_user(user_id)}, message=message)


@router.put("/{user_id}/status")
async def set_status(user_id: str, request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    account = controller.get_user(user_id)
    if not account:
        return fail("User not found.", 404)
    status = str((await json_body(request)).get("status", "")).strip().lower()
    if status not in ("active", "inactive"):
        return fail("Status must be 'active' or 'inactive'.")
    if user_id == user["user_id"]:
        return fail("You cannot change your own account status.", 409)
    if account["status"] == status:
        return ok(data={"user": account}, message=f"Account is already {status}.")
    _, message = controller.set_user_status(user_id, status)
    return ok(data={"user": controller.get_user(user_id)}, message=message)


@router.get("/{user_id}")
async def get_user(user_id: str, request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    account = controller.get_user(user_id)
    if not account:
        return fail("User not found.", 404)
    payload = {
        "user": account,
        "borrow_history": controller.borrow_dao.get_student_borrowed_books(user_id),
        "fines": controller.borrow_dao.get_student_fines(user_id),
    }
    if account["role"] == "student":
        payload["reservations"] = controller.reservation_dao.list_reservations(student_id=user_id)
    return ok(data=payload)


activity_router = APIRouter(prefix="/api/activity-logs")


@activity_router.get("")
async def activity_logs(request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    try:
        limit = min(500, max(1, int(request.query_params.get("limit", 200))))
    except ValueError:
        limit = 200
    action = request.query_params.get("action", "").strip().upper() or None
    search = request.query_params.get("q", "").strip().lower() or None
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
