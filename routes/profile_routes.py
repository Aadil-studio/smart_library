from fastapi import APIRouter, Depends, Request

from routes import (fail, get_controller, json_body, login_required,
                    ok, password_problem, require_fields)

router = APIRouter(prefix="/api/profile")


@router.get("")
async def get_profile(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    return ok(data={
        "profile": controller.get_user(user["user_id"]),
        "preferences": controller.get_preferences(user["user_id"]),
        "stats": {
            "borrowed_total": len(controller.borrow_dao.get_student_borrowed_books(user["user_id"])),
            "active_loans": len(controller.borrow_dao.get_student_borrowed_books(user["user_id"], active_only=True)),
        },
    })


@router.put("")
async def update_profile(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
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
    request.session["user"] = refreshed
    return ok(data={"profile": refreshed}, message=message)


@router.put("/password")
async def change_password(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
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


@router.put("/preferences")
async def update_preferences(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
    current = controller.get_preferences(user["user_id"])
    if "due_reminders" in data:
        current["due_reminders"] = bool(data["due_reminders"])
    success, message = controller.set_preferences(user["user_id"], current)
    return ok(data={"preferences": controller.get_preferences(user["user_id"])}, message=message)
