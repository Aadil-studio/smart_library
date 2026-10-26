from flask import Blueprint, request

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, parse_int, require_fields, staff_required)

borrow_bp = Blueprint("borrow", __name__, url_prefix="/api/borrow")


@borrow_bp.post("")
@login_required
def issue_book():
    controller = get_controller()
    user = current_user()
    data = json_body()
    error = require_fields(data, "student_id", "book_id")
    if error:
        return fail(error)
    if "days" in data:
        days, error = parse_int(data["days"], "days", minimum=1, maximum=90)
        if error:
            return fail(error)
    else:
        days = controller.get_library_settings().get("loan_period_days", "14")
        try:
            days = max(1, min(90, int(days)))
        except (TypeError, ValueError):
            days = 14

    student_id = str(data["student_id"]).strip()
    # Students may borrow for themselves only; staff may issue to any member.
    if user["role"] not in ("admin", "librarian"):
        if student_id.lower() != user["user_id"].lower():
            return fail("You can only borrow books for your own account.", 403)

    # Accept a numeric book ID or an ISBN string
    book_ref = str(data["book_id"]).strip()
    try:
        book_id = int(book_ref)
    except ValueError:
        book = controller.book_dao.get_book_by_isbn(book_ref)
        if not book:
            return fail(f"No book found with ISBN '{book_ref}'.", 404)
        book_id = book["id"]

    result = controller.borrow_dao.issue_book(student_id, book_id, days)
    success, message = result[0], result[1]
    if not success:
        return fail(message, 409)
    return ok(message=message)


@borrow_bp.post("/<int:transaction_id>/return")
@login_required
def return_book(transaction_id):
    controller = get_controller()
    user = current_user()
    transaction = controller.borrow_dao.get_transaction_by_id(transaction_id)
    if not transaction:
        return fail("Active transaction not found (it may already have been returned).", 409)
    if user["role"] not in ("admin", "librarian") and transaction["student_id"] != user["user_id"]:
        return fail("You can only return books borrowed on your own account.", 403)
    success, message, _fine = controller.return_book(transaction_id, user["role"])
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
