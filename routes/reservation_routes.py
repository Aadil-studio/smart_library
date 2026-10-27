from fastapi import APIRouter, Depends, Request

from routes import (fail, get_controller, json_body, login_required,
                    ok, parse_int, require_fields)

router = APIRouter(prefix="/api/reservations")


@router.get("")
async def list_reservations(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    scope = request.query_params.get("scope", "mine")
    status = request.query_params.get("status", "").strip() or None
    search = request.query_params.get("q", "").strip() or None

    if scope == "all":
        if user["role"] not in ("admin", "librarian"):
            return fail("You do not have permission to view all reservations.", 403)
        reservations = controller.list_reservations(status=status, search=search)
    else:
        reservations = controller.list_reservations(student_id=user["user_id"], status=status)
    return ok(data={"reservations": reservations})


@router.post("")
async def create_reservation(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    if user["role"] not in ("student",):
        return fail("Only students can reserve books.", 403)
    data = await json_body(request)
    error = require_fields(data, "book_id")
    if error:
        return fail(error)

    book_id, error = parse_int(data.get("book_id"), "book_id", minimum=1)
    if error:
        return fail(error)

    book = controller.get_book(book_id)
    if not book:
        return fail("Book not found.", 404)
    success, message = controller.reserve_book(user["user_id"], book_id)
    if not success:
        return fail(message, 409)
    return ok(message=message)


@router.put("/{reservation_id}")
async def update_reservation(reservation_id: int, request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
    action = str(data.get("action", "")).strip().lower()
    if action not in ("approve", "reject", "fulfil", "cancel"):
        return fail("Action must be one of: approve, reject, fulfil, cancel.")

    if action in ("approve", "reject", "fulfil") and user["role"] not in ("admin", "librarian"):
        return fail("Only library staff can manage reservations.", 403)

    success, message = controller.update_reservation_status(reservation_id, action, user["user_id"])
    if not success:
        return fail(message, 409)
    return ok(message=message)
