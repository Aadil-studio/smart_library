from flask import Blueprint

from routes import (current_user, get_controller, login_required, ok, staff_required)

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("")
@login_required
def dashboard():
    controller = get_controller()
    controller.run_overdue_sweep()
    user = current_user()
    if user["role"] in ("admin", "librarian"):
        data = controller.get_admin_dashboard()
        data["role_view"] = "staff"
    else:
        data = controller.get_student_dashboard(user)
        data["role_view"] = "student"
    return ok(data=data)
