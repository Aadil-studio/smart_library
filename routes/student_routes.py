from flask import Blueprint, request

from routes import (admin_required, current_user, fail, get_controller, login_required, ok)

student_bp = Blueprint("students", __name__, url_prefix="/api/students")


@student_bp.get("")
@admin_required
def list_students():
    controller = get_controller()
    students = controller.user_dao.get_users_by_role(
        "student",
        search=request.args.get("q", "").strip() or None,
        status=request.args.get("status", "").strip() or None,
    )
    return ok(data={"students": students})


@student_bp.get("/<user_id>")
@admin_required
def get_student(user_id):
    controller = get_controller()
    student = controller.get_user(user_id)
    if not student or student["role"] != "student":
        return fail("Student not found.", 404)
    return ok(data={
        "student": student,
        "borrow_history": controller.borrow_dao.get_student_borrowed_books(user_id),
        "active_loans": controller.borrow_dao.get_student_borrowed_books(user_id, active_only=True),
        "reservations": controller.reservation_dao.list_reservations(student_id=user_id),
        "fines": controller.borrow_dao.get_student_fines(user_id),
    })


@student_bp.put("/<user_id>/status")
@admin_required
def set_status(user_id):
    controller = get_controller()
    student = controller.get_user(user_id)
    if not student or student["role"] != "student":
        return fail("Student not found.", 404)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ("active", "inactive"):
        return fail("Status must be 'active' or 'inactive'.")
    if student["status"] == status:
        return ok(message=f"Account is already {status}.")
    success, message = controller.set_user_status(user_id, status)
    return ok(data={"student": controller.get_user(user_id)}, message=message)


@student_bp.get("/<user_id>/history")
@login_required
def student_history(user_id):
    user = current_user()
    if user["role"] == "student" and user["user_id"] != user_id:
        return fail("You can only view your own history.", 403)
    controller = get_controller()
    return ok(data={"history": controller.borrow_dao.get_student_borrowed_books(user_id)})
