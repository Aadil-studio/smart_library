from fastapi import APIRouter, Depends, Request

from routes import (get_controller, ok, parse_int, staff_required)

router = APIRouter(prefix="/api/reports")


@router.get("/summary")
async def summary(request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    controller.run_overdue_sweep()
    return ok(data=controller.report_summary())


@router.get("/borrowing")
async def borrowing(request: Request, user: dict = Depends(staff_required)):
    days, error = parse_int(request.query_params.get("days", 30), "days", minimum=1, maximum=365)
    if error:
        return ok(data=get_controller(request).borrowing_report(days=30))
    return ok(data=get_controller(request).borrowing_report(days=days))


@router.get("/top-books")
async def top_books(request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    return ok(data={"books": controller.borrow_dao.most_borrowed_books(limit=10),
                    "categories": controller.book_dao.category_distribution()})


@router.get("/overdue")
async def overdue(request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    controller.run_overdue_sweep()
    return ok(data={"overdue": controller.borrow_dao.get_overdue_transactions()})
