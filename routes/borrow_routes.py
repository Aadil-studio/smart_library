from flask import Blueprint, request

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, parse_int, require_fields, staff_required)

borrow_bp = Blueprint("borrow", __name__, url_prefix="/api/borrow")


@borrow_bp.post("")
@staff_required
def issue_book():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "student_id", "book_id")
    if error:
        return fail(error)
    days, error = parse_int(data.get("days", 14), "days", minimum=1, maximum=90)
    if error:
        return fail(error)

    result = controller.borrow_dao.issue_book(str(data["student_id"]).strip(), int(data["book_id"]), days)
    success, message = result[0], result[1]
    if not success:
        return fail(message, 409)
    return ok(message=message)


@borrow_bp.post("/<int:transaction_id>/return")
@staff_required
def return_book(transaction_id):
    success, message, _fine = get_controller().return_book(transaction_id)
    if not success:
        return fail(message, 409)
    return ok(message=message)


@borrow_bp.get("")
@login_required
def list_borrows():
    controller = get_controller()
    user = current_user()
    scope = request.args.get("scope", "mine")
    status = request.args.get("status", "").strip() or None
    search = request.args.get("q", "").strip() or None

    if scope == "all":
        if user["role"] not in ("admin", "librarian"):
            return fail("You do not have permission to view all loans.", 403)
        transactions = controller.list_transactions(status=status, search=search)
    else:
        transactions = controller.list_transactions(student_id=user["user_id"], status=status)
    return ok(data={"transactions": transactions})


@borrow_bp.get("/fines")
@login_required
def my_fines():
    controller = get_controller()
    user = current_user()
    fines = controller.borrow_dao.get_student_fines(user["user_id"])
    unpaid = sum(f["amount"] for f in fines if f["status"] == "unpaid")
    return ok(data={"fines": fines, "unpaid_total": unpaid})
