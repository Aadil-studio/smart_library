from flask import Blueprint, request

from routes import (current_user, fail, get_controller, json_body, login_required,
                    ok, require_fields, staff_required)

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notification_bp.get("")
@login_required
def list_notifications():
    controller = get_controller()
    user = current_user()
    unread_only = request.args.get("unread") == "1"
    notifications = controller.list_notifications(user["user_id"], unread_only=unread_only)
    return ok(data={"notifications": notifications, "unread": controller.unread_count(user["user_id"])})


@notification_bp.get("/unread-count")
@login_required
def unread_count():
    controller = get_controller()
    return ok(data={"unread": controller.unread_count(current_user()["user_id"])})


@notification_bp.put("/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    success = get_controller().mark_notification_read(notification_id, current_user()["user_id"])
    if not success:
        return fail("Notification not found.", 404)
    return ok(message="Notification marked as read.")


@notification_bp.put("/read-all")
@login_required
def mark_all_read():
    message = get_controller().mark_all_notifications_read(current_user()["user_id"])
    return ok(message=message)


@notification_bp.post("/broadcast")
@staff_required
def broadcast():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "title", "message")
    if error:
        return fail(error)
    target = str(data.get("target_user_id", "") or "").strip() or None
    if target and not controller.get_user(target):
        return fail("Recipient not found.", 404)
    sent = controller.broadcast_notification(str(data["title"]).strip(),
                                             str(data["message"]).strip(), target_user_id=target)
    return ok(data={"sent": sent}, message=f"Announcement sent to {sent} recipient(s).")
