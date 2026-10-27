from fastapi import APIRouter, Depends, Request

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, parse_int, require_fields, staff_required)

router = APIRouter(prefix="/api/borrow")


@router.post("")
async def issue_book(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
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

    # Book-fee gate: books are only issued once the member's book fee is paid
    unpaid_fees = controller.list_fees(student_id=student_id, status="unpaid")
    if unpaid_fees:
        total = sum(f["amount"] for f in unpaid_fees)
        if user["role"] in ("admin", "librarian"):
            return fail(f"{student_id} has an unpaid book fee of Rs. {total:.2f}. "
                        "The admin must mark the fee paid before books can be issued.", 403)
        return fail(f"You have an unpaid book fee of Rs. {total:.2f}. "
                    "Pay it at the library admin portal before borrowing books.", 403)

    result = controller.borrow_dao.issue_book(student_id, book_id, days)
    success, message = result[0], result[1]
    if not success:
        return fail(message, 409)
    return ok(message=message)


@router.post("/{transaction_id}/return")
async def return_book(transaction_id: int, request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    transaction = controller.borrow_dao.get_transaction_by_id(transaction_id)
    if not transaction:
        return fail("Active transaction not found (it may already have been returned).", 409)
    if user["role"] not in ("admin", "librarian") and transaction["student_id"] != user["user_id"]:
        return fail("You can only return books borrowed on your own account.", 403)
    success, message, _fine = controller.return_book(transaction_id, user["role"])
    if not success:
        return fail(message, 409)
    return ok(message=message)


@router.get("")
async def list_borrows(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    scope = request.query_params.get("scope", "mine")
    status = request.query_params.get("status", "").strip() or None
    search = request.query_params.get("q", "").strip() or None

    if scope == "all":
        if user["role"] not in ("admin", "librarian"):
            return fail("You do not have permission to view all loans.", 403)
        transactions = controller.list_transactions(status=status, search=search)
    else:
        transactions = controller.list_transactions(student_id=user["user_id"], status=status)
    return ok(data={"transactions": transactions})


@router.get("/fines")
async def my_fines(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    fines = controller.borrow_dao.get_student_fines(user["user_id"])
    unpaid = sum(f["amount"] for f in fines if f["status"] == "unpaid")
    fees = controller.list_fees(student_id=user["user_id"])
    fees_unpaid = sum(f["amount"] for f in fees if f["status"] == "unpaid")
    return ok(data={"fines": fines, "unpaid_total": unpaid,
                    "fees": fees, "fees_unpaid_total": fees_unpaid})
