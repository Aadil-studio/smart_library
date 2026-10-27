from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from routes import (admin_required, fail, get_controller, json_body, login_required,
                    ok, parse_float, parse_int, require_fields, staff_required)

router = APIRouter(prefix="/api/fines")
fee_router = APIRouter(prefix="/api/fees")


@router.get("")
async def list_fines(request: Request, user: dict = Depends(staff_required)):
    status = request.query_params.get("status", "").strip().lower() or None
    if status not in (None, "unpaid", "paid", "waived"):
        return fail("Status must be 'unpaid', 'paid' or 'waived'.")
    query = request.query_params.get("q", "").strip() or None
    controller = get_controller(request)
    fines = controller.list_fines(status=status, search=query)
    return ok(data={"fines": fines, "summary": controller.fine_summary(),
                    "fee_summary": controller.fee_summary()})


@router.post("/{fine_id}/collect")
async def collect_fine(fine_id: int, request: Request, user: dict = Depends(staff_required)):
    success, message, fine = get_controller(request).collect_fine(fine_id, user["user_id"])
    if not success:
        return fail(message, 404 if message == "Fine not found." else 409)
    return ok(data={"fine": fine}, message=message)


@router.post("/{fine_id}/waive")
async def waive_fine(fine_id: int, request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    data = await json_body(request)
    reason = str(data.get("reason", "") or "").strip()
    if len(reason) < 5:
        return fail("A reason of at least 5 characters is required to waive a fine.")
    success, message, fine = controller.waive_fine(fine_id, user["user_id"], reason)
    if not success:
        return fail(message, 404 if message == "Fine not found." else 409)
    return ok(data={"fine": fine}, message=message)


# --- Book fees: uploaded by the ADMIN only, published to the student portal
# automatically; only the admin grants "paid" ---

@fee_router.get("")
async def list_fees(request: Request, user: dict = Depends(login_required)):
    """Students see their own book fees; library staff see all of them."""
    controller = get_controller(request)
    status = request.query_params.get("status", "").strip().lower() or None
    if status not in (None, "unpaid", "paid"):
        return fail("Status must be 'unpaid' or 'paid'.")
    query = request.query_params.get("q", "").strip() or None
    if user["role"] in ("admin", "librarian"):
        fees = controller.list_fees(status=status, search=query)
    else:
        fees = controller.list_fees(student_id=user["user_id"], status=status)
    unpaid = sum(f["amount"] for f in fees if f["status"] == "unpaid")
    return ok(data={"fees": fees, "unpaid_total": unpaid,
                    "summary": controller.fee_summary()})


@fee_router.post("")
async def upload_fee(request: Request, user: dict = Depends(admin_required)):
    """Admin uploads a book fee for a member. It is published to the student's
    portal immediately; the member cannot borrow books until it is paid."""
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "student_id")
    if error:
        return fail(error)
    student_id = str(data["student_id"]).strip()
    student = controller.get_user(student_id)
    if not student or student["role"] != "student":
        return fail("Student not found.", 404)

    amount, error = parse_float(data, "amount", minimum=1, maximum=100000)
    if error:
        return fail(error)
    if amount is None:
        # Default to the library book fee (Rs. 4000 unless changed in settings)
        from services.settings_service import SettingsService
        amount = SettingsService().get_int("book_fee", 4000)

    book_id = None
    if data.get("book_id") not in (None, ""):
        book_id, error = parse_int(data.get("book_id"), "book_id", minimum=1)
        if error:
            return fail(error)
        if not controller.get_book(book_id):
            return fail("Book not found.", 404)

    fee = controller.create_fee(student_id, amount, book_id=book_id, uploaded_by=user["user_id"])
    controller.notification_dao.notify(
        student_id, "Book fee uploaded",
        f"A book fee of Rs. {float(amount):.2f} has been uploaded to your account. "
        f"Pay it at the library admin portal — books can only be issued once your fee is paid.",
        ntype="fee", ref_id=fee["id"],
    )
    admin = controller.get_user(user["user_id"])
    controller.user_dao.log_activity(
        user["user_id"], admin["name"] if admin else user["user_id"],
        "FEE_UPLOADED", f"Uploaded book fee Rs. {float(amount):.2f} for {student_id} (fee #{fee['id']}).")
    return ok(data={"fee": fee}, message=f"Book fee of Rs. {float(amount):.2f} uploaded for {student['name']}. "
                                         f"It is now visible in the student portal.")


@fee_router.post("/{fee_id}/pay")
async def pay_fee(fee_id: int, request: Request, user: dict = Depends(admin_required)):
    """Only the ADMIN can grant 'paid'. The student portal updates automatically."""
    success, message, fee = get_controller(request).collect_fee(fee_id, user["user_id"])
    if not success:
        return fail(message, 404 if message == "Fee not found." else 409)
    return ok(data={"fee": fee}, message=message)


@fee_router.get("/{fee_id}/receipt.pdf")
async def fee_receipt(fee_id: int, request: Request, user: dict = Depends(login_required)):
    """Generate and download the book-fee receipt as a PDF."""
    controller = get_controller(request)
    fee = controller.get_fee(fee_id)
    if not fee:
        return fail("Fee not found.", 404)
    if user["role"] not in ("admin", "librarian") and fee["student_id"] != user["user_id"]:
        return fail("You can only download your own fee receipts.", 403)

    from generate_pdf import build_fee_receipt_pdf
    pdf_bytes, error = build_fee_receipt_pdf(fee)
    if error:
        return fail(error, 500)
    filename = f"book-fee-receipt-{fee_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
