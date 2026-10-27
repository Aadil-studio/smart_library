import os

from fastapi import APIRouter, Depends, Request

from routes import (admin_required, current_user, fail, get_controller, json_body,
                    login_required, ok, password_problem, require_fields, valid_email)

router = APIRouter(prefix="/api/auth")


@router.post("/register")
async def register(request: Request):
    controller = get_controller(request)
    data = await json_body(request)
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

    user = controller.get_user(student_id)
    if user:
        controller.notification_dao.notify(
            user["user_id"], "Welcome to Smart Library",
            f"Hi {user['name']}, your account was created successfully. Explore the catalog and reserve books!",
            ntype="account",
        )
        # Library staff keep an eye on new members
        for staff in controller.list_all_users(role="librarian") + controller.list_all_users(role="admin"):
            controller.notification_dao.notify(
                staff["user_id"], "New member registered",
                f"{user['name']} ({user['user_id']}) joined the library.",
                ntype="account",
            )

    return ok(data={"user": user}, message="Account created successfully. Please login.")


@router.post("/login")
async def login(request: Request):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "credential", "password")
    if error:
        return fail("Please enter your login credentials.")

    credential = str(data["credential"]).strip()
    user, reason = controller.user_dao.authenticate_with_reason(credential, data["password"])
    if not user:
        if reason == "Account not found.":
            return fail(reason, 404)
        if reason == "Your account has been disabled. Please contact the library administrator.":
            return fail(reason, 403)
        if reason == "Incorrect password.":
            return fail(reason, 401)
        return fail("Invalid email or password.", 401)

    request.session["user"] = user
    return ok(data={"user": user}, message=f"Welcome back, {user['name']}!")


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(login_required)):
    request.session.clear()
    return ok(message="You have been signed out.")


@router.get("/me")
async def me(request: Request):
    user = current_user(request)
    if not user:
        return fail("Not signed in.", 401)
    return ok(data={"user": user})


@router.post("/forgot-password")
async def forgot_password(request: Request):
    controller = get_controller(request)
    data = await json_body(request)
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
    if os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"):
        # Real delivery: the 6-digit code AND a reset link land in the user's Gmail inbox.
        base_url = os.environ.get("APP_BASE_URL", "https://127.0.0.1:8000").rstrip("/")
        reset_url = f"{base_url}/reset-password.html?email={email}"
        sent, send_message = send_otp_email(email, otp_or_msg, reset_url)
        message = send_message if sent else "Email delivery failed. Please try again later."
    elif os.environ.get("OTP_DEV_MODE", "1") == "1":
        # DEVELOPMENT ONLY: no SMTP configured, so the code is returned for testing.
        response_data = {"dev_otp": otp_or_msg}
        message = "Development mode: use the verification code shown below."
    return ok(data=response_data, message=message)


@router.post("/verify-otp")
async def verify_otp(request: Request):
    """Step 1 of the reset: the user enters the code emailed to their Gmail.
    On success a short-lived signed token is returned — only then is the
    change-password step unlocked."""
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "email", "otp")
    if error:
        return fail(error)
    email = str(data["email"]).strip().lower()
    verified, message, otp_hash = controller.user_dao.verify_otp(email, str(data["otp"]).strip())
    if not verified:
        return fail(message)

    from itsdangerous import URLSafeTimedSerializer
    signer = URLSafeTimedSerializer(request.app.state.secret_key, salt="password-reset")
    token = signer.dumps({"email": email, "otp_hash": otp_hash})
    return ok(data={"reset_token": token}, message=message)


@router.post("/reset-password")
async def reset_password(request: Request):
    """Step 2 of the reset: allowed only with a token from a verified OTP
    (or the raw code, verified again server-side)."""
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "new_password", "confirm_password")
    if error:
        return fail(error)
    if not data.get("reset_token") and (error := require_fields(data, "email", "otp")):
        return fail(error)
    if data["new_password"] != data["confirm_password"]:
        return fail("Passwords do not match.")
    if problem := password_problem(data["new_password"]):
        return fail(problem)

    if data.get("reset_token"):
        from itsdangerous import BadData, URLSafeTimedSerializer
        signer = URLSafeTimedSerializer(request.app.state.secret_key, salt="password-reset")
        try:
            payload = signer.loads(str(data["reset_token"]), max_age=600)
        except BadData:
            return fail("Your verification has expired. Please enter the code again.")
        success, message = controller.user_dao.reset_password_with_hash(
            payload["email"], payload["otp_hash"], data["new_password"])
    else:
        success, message = controller.reset_password(
            str(data["email"]).strip().lower(), str(data["otp"]).strip(), data["new_password"])
    if not success:
        return fail(message)
    return ok(message=message)
