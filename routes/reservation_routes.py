from flask import Blueprint, request

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, require_fields, staff_required)

reservation_bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")


@reservation_bp.get("")
@login_required
def list_reservations():
    controller = get_controller()
    user = current_user()
    scope = request.args.get("scope", "mine")
    status = request.args.get("status", "").strip() or None
    search = request.args.get("q", "").strip() or None

    if scope == "all":
        if user["role"] not in ("admin", "librarian"):
            return fail("You do not have permission to view all reservations.", 403)
        reservations = controller.list_reservations(status=status, search=search)
    else:
        reservations = controller.list_reservations(student_id=user["user_id"], status=status)
    return ok(data={"reservations": reservations})


@reservation_bp.post("")
@login_required
def create_reservation():
    controller = get_controller()
    user = current_user()
    if user["role"] not in ("student",):
        return fail("Only students can reserve books.", 403)
    data = json_body()
    error = require_fields(data, "book_id")
    if error:
        return fail(error)
    book = controller.get_book(int(data["book_id"]))
    if not book:
        return fail("Book not found.", 404)
    success, message = controller.reserve_book(user["user_id"], int(data["book_id"]))
    if not success:
        return fail(message, 409)
    return ok(message=message)


@reservation_bp.put("/<int:reservation_id>")
@login_required
def update_reservation(reservation_id):
    controller = get_controller()
    user = current_user()
    data = json_body()
    action = str(data.get("action", "")).strip().lower()
    if action not in ("approve", "reject", "fulfil", "cancel"):
        return fail("Action must be one of: approve, reject, fulfil, cancel.")

    if action in ("approve", "reject", "fulfil") and user["role"] not in ("admin", "librarian"):
        return fail("Only library staff can manage reservations.", 403)

    success, message = controller.update_reservation_status(reservation_id, action, user["user_id"])
    if not success:
        return fail(message, 409)
    return ok(message=message)
