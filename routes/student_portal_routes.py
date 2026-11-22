from fastapi import APIRouter, Depends

from dao.student_portal_dao import StudentPortalDAO
from routes import fail, login_required, ok

router = APIRouter(prefix="/api/student")


def _student_only(user):
    if user.get("role") != "student":
        return fail("Student access only.", 403)
    return None


@router.get("/wishlist")
async def get_wishlist(user: dict = Depends(login_required)):
    denied = _student_only(user)
    if denied:
        return denied
    wishlist = StudentPortalDAO().list_wishlist(user["user_id"])
    return ok(data={"wishlist": wishlist})


@router.post("/wishlist/{book_id}")
async def toggle_wishlist(book_id: int, user: dict = Depends(login_required)):
    denied = _student_only(user)
    if denied:
        return denied
    saved = StudentPortalDAO().toggle_wishlist(user["user_id"], book_id)
    if saved is None:
        return fail("Book not found.", 404)
    return ok(
        data={"book_id": book_id, "saved": saved},
        message="Book saved to your wishlist." if saved else "Book removed from your wishlist.",
    )


@router.get("/loans/renewals")
async def get_renewed_loans(user: dict = Depends(login_required)):
    denied = _student_only(user)
    if denied:
        return denied
    loan_ids = StudentPortalDAO().renewed_loan_ids(user["user_id"])
    return ok(data={"renewed_loan_ids": loan_ids})


@router.post("/loans/{loan_id}/renew")
async def renew_student_loan(loan_id: int, user: dict = Depends(login_required)):
    denied = _student_only(user)
    if denied:
        return denied
    due_date, error, status = StudentPortalDAO().renew_loan(user["user_id"], loan_id)
    if error:
        return fail(error, status)
    return ok(
        data={"loan_id": loan_id, "due_date": due_date},
        message="Loan renewed by 7 days.",
    )
