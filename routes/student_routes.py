from fastapi import APIRouter, Depends, Request

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, staff_required)

router = APIRouter(prefix="/api/students")


@router.get("")
async def list_students(request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    students = controller.user_dao.get_users_by_role(
        "student",
        search=request.query_params.get("q", "").strip() or None,
        status=request.query_params.get("status", "").strip() or None,
    )
    # Enrich with per-member circulation stats for the member management table
    for student in students:
        loans = controller.borrow_dao.get_student_borrowed_books(student["user_id"], active_only=True)
        student["borrowed_count"] = len(loans)
        student["unpaid_fine"] = controller.borrow_dao.sum_unpaid_fines(student["user_id"])
    return ok(data={"students": students})


@router.get("/{user_id}")
async def get_student(user_id: str, request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    student = controller.get_user(user_id)
    if not student or student["role"] != "student":
        return fail("Student not found.", 404)
    return ok(data={
        "student": student,
        "borrow_history": controller.borrow_dao.get_student_borrowed_books(user_id),
        "active_loans": controller.borrow_dao.get_student_borrowed_books(user_id, active_only=True),
        "reservations": controller.reservation_dao.list_reservations(student_id=user_id),
        "fines": controller.borrow_dao.get_student_fines(user_id),
        "fees": controller.list_fees(student_id=user_id),
    })


@router.put("/{user_id}/status")
async def set_status(user_id: str, request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    student = controller.get_user(user_id)
    if not student or student["role"] != "student":
        return fail("Student not found.", 404)
    status = (await json_body(request)).get("status")
    if status not in ("active", "inactive"):
        return fail("Status must be 'active' or 'inactive'.")
    if student["status"] == status:
        return ok(message=f"Account is already {status}.")
    success, message = controller.set_user_status(user_id, status)
    return ok(data={"student": controller.get_user(user_id)}, message=message)


@router.get("/{user_id}/history")
async def student_history(user_id: str, request: Request, user: dict = Depends(login_required)):
    if user["role"] == "student" and user["user_id"] != user_id:
        return fail("You can only view your own history.", 403)
    controller = get_controller(request)
    return ok(data={"history": controller.borrow_dao.get_student_borrowed_books(user_id)})
