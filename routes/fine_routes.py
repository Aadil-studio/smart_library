from flask import Blueprint, request

from routes import admin_required, current_user, fail, get_controller, json_body, ok, staff_required

fine_bp = Blueprint("fines", __name__, url_prefix="/api/fines")


@fine_bp.get("")
@staff_required
def list_fines():
    status = request.args.get("status", "").strip().lower() or None
    if status not in (None, "unpaid", "paid", "waived"):
        return fail("Status must be 'unpaid', 'paid' or 'waived'.")
    query = request.args.get("q", "").strip() or None
    controller = get_controller()
    fines = controller.list_fines(status=status, search=query)
    return ok(data={"fines": fines, "summary": controller.fine_summary()})


@fine_bp.post("/<int:fine_id>/collect")
@staff_required
def collect_fine(fine_id):
    success, message, fine = get_controller().collect_fine(fine_id, current_user()["user_id"])
    if not success:
        return fail(message, 404 if message == "Fine not found." else 409)
    return ok(data={"fine": fine}, message=message)


@fine_bp.post("/<int:fine_id>/waive")
@admin_required
def waive_fine(fine_id):
    controller = get_controller()
    data = json_body()
    reason = str(data.get("reason", "") or "").strip()
    if len(reason) < 5:
        return fail("A reason of at least 5 characters is required to waive a fine.")
    success, message, fine = controller.waive_fine(fine_id, current_user()["user_id"], reason)
    if not success:
        return fail(message, 404 if message == "Fine not found." else 409)
    return ok(data={"fine": fine}, message=message)
