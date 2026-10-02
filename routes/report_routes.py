from flask import Blueprint, request

from routes import (admin_required, get_controller, ok, parse_int, staff_required)

report_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@report_bp.get("/summary")
@staff_required
def summary():
    controller = get_controller()
    controller.run_overdue_sweep()
    return ok(data=controller.report_summary())


@report_bp.get("/borrowing")
@staff_required
def borrowing():
    days, error = parse_int(request.args.get("days", 30), "days", minimum=1, maximum=365)
    if error:
        return ok(data=get_controller().borrowing_report(days=30))
    return ok(data=get_controller().borrowing_report(days=days))


@report_bp.get("/top-books")
@staff_required
def top_books():
    controller = get_controller()
    return ok(data={"books": controller.borrow_dao.most_borrowed_books(limit=10),
                    "categories": controller.book_dao.category_distribution()})


@report_bp.get("/overdue")
@staff_required
def overdue():
    get_controller().run_overdue_sweep()
    return ok(data={"overdue": get_controller().borrow_dao.get_overdue_transactions()})
