from fastapi import APIRouter, Depends, Request

from routes import (fail, get_controller, json_body, login_required,
                    ok, require_fields, staff_required)

router = APIRouter(prefix="/api/notifications")


@router.get("")
async def list_notifications(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    unread_only = request.query_params.get("unread") == "1"
    notifications = controller.list_notifications(user["user_id"], unread_only=unread_only)
    return ok(data={"notifications": notifications, "unread": controller.unread_count(user["user_id"])})


@router.get("/unread-count")
async def unread_count(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    return ok(data={"unread": controller.unread_count(user["user_id"])})


@router.put("/{notification_id}/read")
async def mark_read(notification_id: int, request: Request, user: dict = Depends(login_required)):
    success = get_controller(request).mark_notification_read(notification_id, user["user_id"])
    if not success:
        return fail("Notification not found.", 404)
    return ok(message="Notification marked as read.")


@router.put("/read-all")
async def mark_all_read(request: Request, user: dict = Depends(login_required)):
    message = get_controller(request).mark_all_notifications_read(user["user_id"])
    return ok(message=message)


@router.post("/broadcast")
async def broadcast(request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "title", "message")
    if error:
        return fail(error)
    target = str(data.get("target_user_id", "") or "").strip() or None
    if target and not controller.get_user(target):
        return fail("Recipient not found.", 404)
    sent = controller.broadcast_notification(str(data["title"]).strip(),
                                             str(data["message"]).strip(), target_user_id=target)
    return ok(data={"sent": sent}, message=f"Announcement sent to {sent} recipient(s).")
