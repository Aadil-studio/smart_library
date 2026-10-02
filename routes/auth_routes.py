import os

from flask import Blueprint, request, session

from routes import (admin_required, current_user, fail, get_controller, json_body,
                    login_required, ok, password_problem, require_fields, valid_email)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "student_id", "full_name", "email", "password", "confirm_password")
    if error:
        return fail(error)

    student_id = str(data["student_id"]).strip()
    full_name = str(data["full_name"]).strip()
    email = str(data["email"]).strip().lower()

    if len(student_id) < 3 or len(student_id) > 20:
        return fail("Student / Role ID must be between 3 and 20 characters.")
    if not valid_email(email):
        return fail("Please enter a valid email address.")
    if len(full_name) < 3:
        return fail("Please enter your full name.")
    if data["password"] != data["confirm_password"]:
        return fail("Passwords do not match.")
    if problem := password_problem(data["password"]):
        return fail(problem)

    success, message = controller.register(
        student_id, full_name, email, data["password"],
        role="student",
        department=str(data.get("department", "") or "").strip(),
        semester=str(data.get("semester", "") or "").strip(),
        phone=str(data.get("phone", "") or "").strip(),
    )
    if not success:
        return fail(message, 409)
    user = controller.login(email, data["password"])
    controller.notification_dao.notify(
        user["user_id"], "Welcome to Smart Library",
        f"Hi {user['name']}, your account was created successfully. Explore the catalog and reserve books!",
        ntype="account",
    )
    session["user"] = user
    return ok(data={"user": user}, message="Registration successful. Welcome aboard!")


@auth_bp.post("/login")
def login():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "credential", "password")
    if error:
        return fail("Please enter your login credentials.")

    credential = str(data["credential"]).strip()
    user = controller.login(credential, data["password"])
    if not user:
        return fail("Invalid credentials or inactive account.", 401)

    session["user"] = user
    # Remember me keeps the session cookie across browser restarts (lifetime set in create_app)
    session.permanent = bool(data.get("remember"))
    return ok(data={"user": user}, message=f"Welcome back, {user['name']}!")


@auth_bp.post("/logout")
@login_required
def logout():
    session.clear()
    return ok(message="You have been signed out.")


@auth_bp.get("/me")
def me():
    user = current_user()
    if not user:
        return fail("Not signed in.", 401)
    return ok(data={"user": user})


@auth_bp.post("/forgot-password")
def forgot_password():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "email")
    if error:
        return fail(error)
    email = str(data["email"]).strip().lower()
    if not valid_email(email):
        return fail("Please enter a valid email address.")

    success, otp_or_msg = controller.generate_otp(email)
    if not success:
        # Do not reveal whether an email is registered to an attacker probing accounts
        return ok(message="If that email is registered, a verification code has been sent.")

    from services.email_service import send_otp_email
    message = "If that email is registered, a verification code has been sent."
    response_data = None
    if os.environ.get("SMTP_HOST"):
        sent, send_message = send_otp_email(email, otp_or_msg)
        message = send_message if sent else "Email delivery failed. Please try again later."
    elif os.environ.get("OTP_DEV_MODE", "1") == "1":
        # DEVELOPMENT ONLY: no SMTP server configured, so the code is returned for testing.
        response_data = {"dev_otp": otp_or_msg}
        message = "Development mode: use the verification code shown below."
    return ok(data=response_data, message=message)


@auth_bp.post("/verify-otp")
def verify_otp():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "email", "otp")
    if error:
        return fail(error)
    ok_result, message = controller.user_dao.verify_otp(str(data["email"]).strip().lower(), str(data["otp"]).strip())
    if not ok_result:
        return fail(message)
    return ok(message=message)


@auth_bp.post("/reset-password")
def reset_password():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "email", "otp", "new_password", "confirm_password")
    if error:
        return fail(error)
    if data["new_password"] != data["confirm_password"]:
        return fail("Passwords do not match.")
    if problem := password_problem(data["new_password"]):
        return fail(problem)
    success, message = controller.reset_password(
        str(data["email"]).strip().lower(), str(data["otp"]).strip(), data["new_password"])
    if not success:
        return fail(message)
    return ok(message=message)
