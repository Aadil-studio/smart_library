from fastapi import APIRouter, Depends, Request

from routes import (get_controller, login_required, ok)

router = APIRouter(prefix="/api/dashboard")


@router.get("")
async def dashboard(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    controller.run_overdue_sweep()
    if user["role"] in ("admin", "librarian"):
        data = controller.get_admin_dashboard()
        data["role_view"] = "staff"
    else:
        data = controller.get_student_dashboard(user)
        data["role_view"] = "student"
    return ok(data=data)
