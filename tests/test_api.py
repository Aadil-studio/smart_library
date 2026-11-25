"""End-to-end API tests: auth, role authorization, books, borrow/return, reservations,
notifications, overdue sweep, OTP reset, book fee + PDF receipt, profile — all against
an in-memory database."""
import sqlite3
import base64

import pytest
from fastapi.testclient import TestClient

from config.database import DatabaseConnection


@pytest.fixture
def api(monkeypatch):
    # Fixed environment so tests never depend on a local .env
    monkeypatch.setenv("ADMIN_EMAIL", "admin@library.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("APP_DEBUG", "1")
    monkeypatch.setenv("SECRET_KEY", "isolated-test-session-secret")
    # the live server runs HTTPS with Secure cookies; the test client is plain HTTP
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")
    for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_FROM", "SMTP_USER", "SMTP_PASSWORD", "SMTP_PASS", "APP_BASE_URL"):
        monkeypatch.setenv(key, "")

    instance = object.__new__(DatabaseConnection)
    instance.connection = sqlite3.connect(":memory:", check_same_thread=False)
    instance.connection.row_factory = sqlite3.Row
    instance.connection.execute("PRAGMA foreign_keys = ON")
    monkeypatch.setattr(DatabaseConnection, "_instance", instance)

    import main as main_module
    fastapi_app = main_module.create_app()

    controller = fastapi_app.state.library_controller
    controller.register("STU999", "Nina Wells", "nina@library.com", "passw0rd1", role="student",
                        department="CS", semester="4")
    controller.register("STAFF01", "Librarian Ray", "ray@library.com", "passw0rd1", role="librarian")

    from fastapi.testclient import TestClient
    client = TestClient(fastapi_app, follow_redirects=False)
    yield client, controller, fastapi_app
    instance.connection.close()


def login_as(client, credential, password):
    response = client.post("/api/auth/login", json={"credential": credential, "password": password})
    assert response.status_code == 200, response.json()
    return response


def capture_otp_delivery(monkeypatch):
    sent_codes = []

    def fake_send(_to_email, otp, _reset_url=None):
        sent_codes.append(otp)
        return True, "A verification code has been emailed to you."

    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "library@example.test")
    monkeypatch.setenv("APP_BASE_URL", "https://library.example.test")
    monkeypatch.setattr("services.email_service.send_otp_email", fake_send)
    return sent_codes


def add_book(controller, title="Clean Code", isbn="978-0132350884", copies=2):
    book_id = controller.register_book(title, "Robert C. Martin", isbn, category="Engineering",
                                       total_copies=copies)
    assert book_id
    return book_id


def test_database_initialization_enables_foreign_keys(monkeypatch, tmp_path):
    previous_instance = DatabaseConnection._instance
    monkeypatch.setattr(DatabaseConnection, "_instance", None)
    monkeypatch.setenv("LIBRARY_DB_PATH", str(tmp_path / "foreign-keys.sqlite"))
    database = DatabaseConnection()
    try:
        assert database.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert database.connection.execute(
            "SELECT value FROM settings WHERE key='library_name'"
        ).fetchone()[0] == "Northstar Library"
        with pytest.raises(sqlite3.IntegrityError):
            database.connection.execute(
                "INSERT INTO transactions (student_id, book_id, due_date) VALUES (?, ?, ?)",
                ("missing-student", -1, "2099-01-01"),
            )
    finally:
        database.connection.close()
        DatabaseConnection._instance = previous_instance


# --- Auth ---
def test_register_login_and_me(api):
    client, _, _ = api
    response = client.post("/api/auth/register", json={
        "student_id": "STU-2048", "full_name": "Alex Morgan", "email": "alex@uni.edu",
        "password": "secret12", "confirm_password": "secret12"})
    assert response.status_code == 200
    assert response.json()["data"]["user"]["role"] == "student"

    client.post("/api/auth/logout")
    wrong = client.post("/api/auth/login", json={"credential": "alex@uni.edu", "password": "wrongpass"})
    assert wrong.status_code == 401
    assert wrong.json()["message"] == "Invalid email or password."

    missing = client.post("/api/auth/login", json={"credential": "missing@library.com", "password": "secret12"})
    assert missing.status_code == 401
    assert missing.json()["message"] == wrong.json()["message"]

    deactivated = client.post("/api/auth/register", json={
        "student_id": "STU-2049", "full_name": "Inactive User", "email": "inactive@uni.edu",
        "password": "secret12", "confirm_password": "secret12"})
    assert deactivated.status_code == 200
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE users SET status='inactive' WHERE email='inactive@uni.edu'")
    disabled = client.post("/api/auth/login", json={"credential": "inactive@uni.edu", "password": "secret12"})
    assert disabled.status_code == 401
    assert disabled.json()["message"] == wrong.json()["message"]

    login_as(client, "alex@uni.edu", "secret12")
    me = client.get("/api/auth/me").json()
    assert me["data"]["user"]["email"] == "alex@uni.edu"
    assert "password" not in me["data"]["user"]


def test_development_accounts_login_by_case_insensitive_id_and_email(api):
    client, controller, _ = api
    from seed_northstar import DEVELOPMENT_ACCOUNTS, seed_development_accounts

    seed_development_accounts(controller)
    credentials = (
        ("stu-1001", "Student@123", "student"),
        ("STUDENT@SMARTLIBRARY.LOCAL", "Student@123", "student"),
        ("lib-1001", "Librarian@123", "librarian"),
        ("LIBRARIAN@SMARTLIBRARY.LOCAL", "Librarian@123", "librarian"),
        ("adm-1001", "admin123", "admin"),
        ("admin@library.com", "admin123", "admin"),
        ("ADMIN@SMARTLIBRARY.LOCAL", "admin123", "admin"),
    )

    assert len(DEVELOPMENT_ACCOUNTS) == 3
    for credential, password, role in credentials:
        response = client.post(
            "/api/auth/login",
            json={"credential": credential, "password": password},
        )
        assert response.status_code == 200, response.json()
        assert response.json()["data"]["user"]["role"] == role

    registered = client.post("/api/auth/register", json={
        "student_id": "2k24/swee/01",
        "full_name": "Case Sensitive",
        "email": "case-sensitive@library.com",
        "password": "casepass123",
        "confirm_password": "casepass123",
    })
    assert registered.status_code == 200, registered.json()
    uppercase_id_login = client.post(
        "/api/auth/login",
        json={"credential": "2K24/SWEE/01", "password": "casepass123"},
    )
    assert uppercase_id_login.status_code == 200, uppercase_id_login.json()
    assert uppercase_id_login.json()["data"]["user"]["user_id"] == "2k24/swee/01"


@pytest.mark.parametrize(
    ("credential", "original_password", "password_endpoint"),
    [
        ("2k24/swee/01", "Student@123", "/api/profile/password"),
        ("LIB-1001", "Librarian@123", "/api/profile/password"),
        ("ADM-1001", "admin123", "/api/admin/change-password"),
    ],
    ids=("student", "librarian", "admin"),
)
def test_development_account_seed_preserves_changed_password(
    api, credential, original_password, password_endpoint,
):
    client, controller, _ = api
    from seed_northstar import seed_development_accounts

    seed_development_accounts(controller)
    login_as(client, credential, original_password)
    changed_password = "ChangedPass123"
    changed = client.post(password_endpoint, json={
        "current_password": original_password,
        "new_password": changed_password,
        "confirm_password": changed_password,
    })
    assert changed.status_code == 200, changed.json()
    client.post("/api/auth/logout")

    seed_development_accounts(controller)
    assert client.post("/api/auth/login", json={
        "credential": credential, "password": original_password,
    }).status_code == 401
    assert client.post("/api/auth/login", json={
        "credential": credential, "password": changed_password,
    }).status_code == 200
    login_as(client, credential, changed_password)
    restored = client.post(password_endpoint, json={
        "current_password": changed_password,
        "new_password": original_password,
        "confirm_password": original_password,
    })
    assert restored.status_code == 200, restored.json()
    client.post("/api/auth/logout")
    login_as(client, credential, original_password)


def test_student_login_alias_accepts_separator_variants_and_email_field(api):
    client, controller, _ = api
    controller.register(
        "2k24/swee/01", "Existing Borrower", "borrower@library.com",
        "Borrower@123", role="student",
    )
    from seed_northstar import seed_development_accounts

    seed_development_accounts(controller)

    hyphen_login = client.post(
        "/api/auth/login",
        json={"credential": "2K24-SWEE-01", "password": "Student@123"},
    )
    assert hyphen_login.status_code == 200, hyphen_login.json()
    assert hyphen_login.json()["data"]["user"]["role"] == "student"
    assert hyphen_login.json()["data"]["user"]["user_id"] == "STU-1001"

    email_field_login = client.post(
        "/api/auth/login",
        json={"email": "2K24/SWEE/01", "password": "Student@123"},
    )
    assert email_field_login.status_code == 200, email_field_login.json()
    assert email_field_login.json()["data"]["user"]["user_id"] == "STU-1001"

    borrower_login = client.post(
        "/api/auth/login",
        json={"credential": "2k24/swee/01", "password": "Borrower@123"},
    )
    assert borrower_login.status_code == 200, borrower_login.json()
    assert borrower_login.json()["data"]["user"]["user_id"] == "2k24/swee/01"


def test_register_validation(api):
    client, _, _ = api
    base = {"student_id": "STU-777", "full_name": "Kim Doe", "email": "kim@uni.edu",
            "password": "secret12", "confirm_password": "secret12"}
    assert client.post("/api/auth/register", json={**base, "email": "not-an-email"}).status_code == 400
    assert client.post("/api/auth/register", json={**base, "confirm_password": "different"}).status_code == 400
    assert client.post("/api/auth/register", json={**base, "password": "short"}).status_code == 400
    assert client.post("/api/auth/register", json=base).status_code == 200
    duplicate_email = client.post("/api/auth/register", json={
        "student_id": "STU-778", "full_name": "Kim Clone", "email": "kim@uni.edu",
        "password": "secret12", "confirm_password": "secret12"})
    assert duplicate_email.status_code == 409
    duplicate_id = client.post("/api/auth/register", json={
        "student_id": "STU-777", "full_name": "Other Name", "email": "other@uni.edu",
        "password": "secret12", "confirm_password": "secret12"})
    assert duplicate_id.status_code == 409


def test_production_startup_requires_session_secret(api, monkeypatch):
    _, _, _ = api
    monkeypatch.setenv("APP_DEBUG", "0")
    monkeypatch.setenv("SECRET_KEY", "")
    import main as main_module
    with pytest.raises(RuntimeError, match="Set SECRET_KEY"):
        main_module.create_app()


def test_legacy_password_hashes_are_upgraded(api):
    """The original app stored unsalted SHA-256; login must still work and rehash."""
    client, controller, _ = api
    import hashlib
    controller.register("LEGACY1", "Old Account", "legacy@library.com", "oldpass1")
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE users SET password=? WHERE user_id='LEGACY1'",
                     (hashlib.sha256(b"oldpass1").hexdigest(),))
    login_as(client, "legacy@library.com", "oldpass1")
    with DatabaseConnection().get_connection() as conn:
        stored = conn.execute("SELECT password FROM users WHERE user_id='LEGACY1'").fetchone()[0]
    assert stored.startswith(("pbkdf2:", "scrypt:"))  # upgraded to a salted werkzeug hash


def test_password_reset_otp_flow(api, monkeypatch):
    client, _, _ = api
    sent_codes = capture_otp_delivery(monkeypatch)
    response = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    otp = sent_codes[-1]
    assert response.status_code == 200
    assert "dev_otp" not in response.json().get("data", {})
    assert len(otp) == 6

    invalid = client.post("/api/auth/verify-otp", json={"email": "nina@library.com", "otp": "000000"})
    assert invalid.status_code == 400
    assert invalid.json()["message"] == "That verification code is incorrect."
    verified = client.post("/api/auth/verify-otp", json={"email": "nina@library.com", "otp": otp})
    assert verified.status_code == 200
    assert client.post("/api/auth/verify-otp", json={"email": "nina@library.com", "otp": otp}).status_code == 400
    reset = client.post("/api/auth/reset-password", json={
        "reset_token": verified.json()["data"]["reset_token"],
        "new_password": "newpass99", "confirm_password": "newpass99"})
    assert reset.status_code == 200
    login_as(client, "nina@library.com", "newpass99")
    # A reset token is single-use, and the raw OTP cannot bypass verification.
    assert client.post("/api/auth/reset-password", json={
        "email": "nina@library.com", "otp": otp, "new_password": "another12",
        "confirm_password": "another12"}).status_code == 400
    # Unknown email gets a neutral answer (no account enumeration)
    assert client.post("/api/auth/forgot-password", json={"email": "ghost@nowhere.io"}).status_code == 200


def test_email_config_diagnostic_is_admin_only_and_never_returns_values(api):
    client, _, _ = api
    assert client.get("/api/auth/email-config").status_code == 401

    login_as(client, "admin@library.com", "admin123")
    response = client.get("/api/auth/email-config")
    assert response.status_code == 200
    status = response.json()["data"]
    assert status["env_file_path"].endswith(r"\smart_library\.env")
    assert status["env_file_exists"] is True
    assert status["smtp_host_detected"] is False
    assert status["smtp_sender_detected"] is False
    assert status["smtp_password_detected"] is False
    assert status["smtp_password_source"] == "missing"
    assert status["sources"]["SMTP_HOST"] == "process"
    assert status["sources"]["SMTP_PASSWORD"] == "process"
    assert "isolated-test-session-secret" not in response.text


def test_gmail_smtp_configuration_requires_authentication(api, monkeypatch):
    _, _, _ = api
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASS", "")
    from services.email_service import smtp_configuration_status

    status = smtp_configuration_status()
    assert status["smtp_auth_required"] is True
    assert status["ready"] is False
    assert any("SMTP_USER and SMTP_PASS" in issue for issue in status["issues"])


def test_gmail_smtp_password_variable_and_implicit_tls(api, monkeypatch):
    import smtplib
    from services.email_service import send_otp_email, smtp_configuration_status

    sent = {}

    class FakeSMTPSSL:
        def __init__(self, host, port, timeout, context=None):
            sent["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def login(self, username, password):
            sent["credentials"] = (username, password)

        def send_message(self, _message):
            sent["sent"] = True

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTPSSL)
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_FROM", "library@gmail.com")
    monkeypatch.setenv("SMTP_USER", "library@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.setenv("SMTP_PASS", "legacy-password")

    status = smtp_configuration_status()
    assert status["ready"] is True
    assert status["smtp_password_source"] == "SMTP_PASSWORD"
    success, message = send_otp_email("member@example.com", "123456")

    assert success is True
    assert message == "A verification code has been emailed to you."
    assert sent["connection"] == ("smtp.gmail.com", 465, 10)
    assert sent["credentials"] == ("library@gmail.com", "abcdefghijklmnop")
    assert sent["sent"] is True


def test_gmail_authentication_error_is_logged_without_credentials(api, monkeypatch, caplog):
    import logging
    import smtplib
    from services.email_service import send_otp_email

    username = "private-user@gmail.com"
    password = "private-app-password"

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, context=None):
            pass

        def login(self, _username, _password):
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", username)
    monkeypatch.setenv("SMTP_USER", username)
    monkeypatch.setenv("SMTP_PASSWORD", password)

    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        success, message = send_otp_email("member@example.com", "123456")

    assert success is False
    assert "Google App Password" in message
    assert "SMTP 535: 5.7.8 Username and Password not accepted" in caplog.text
    assert username not in caplog.text
    assert password not in caplog.text


def test_otp_configuration_expiry_attempts_and_resend(api, monkeypatch):
    client, controller, _ = api
    missing_mail = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    assert missing_mail.status_code == 503
    assert "SMTP_HOST" in missing_mail.json()["message"]

    sent_codes = capture_otp_delivery(monkeypatch)
    first = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    assert first.status_code == 200
    first_code = sent_codes[-1]
    blocked = client.post("/api/auth/resend-otp", json={"email": "nina@library.com"})
    assert blocked.status_code == 429
    assert blocked.json()["data"]["retry_after_seconds"] > 0

    connection = controller.user_dao.db
    connection.execute("UPDATE otp_request_limits SET requested_at=requested_at-61")
    connection.commit()
    resent = client.post("/api/auth/resend-otp", json={"email": "nina@library.com"})
    assert resent.status_code == 200
    second_code = sent_codes[-1]
    assert second_code != first_code
    assert client.post("/api/auth/verify-otp", json={
        "email": "nina@library.com", "otp": first_code}).json()["message"] == \
        "That verification code is incorrect."
    assert client.post("/api/auth/verify-otp", json={
        "email": "nina@library.com", "otp": second_code}).status_code == 200

    connection.execute(
        "UPDATE password_reset_otps SET expires_at='2000-01-01 00:00:00' WHERE user_id='STU999'"
    )
    connection.commit()
    expired = client.post("/api/auth/verify-otp", json={
        "email": "nina@library.com", "otp": sent_codes[-1]})
    assert expired.status_code == 400
    assert "expired" in expired.json()["message"].lower()


def test_otp_verification_attempt_limit(api, monkeypatch):
    client, _, _ = api
    capture_otp_delivery(monkeypatch)
    assert client.post("/api/auth/forgot-password", json={"email": "nina@library.com"}).status_code == 200
    for attempt in range(5):
        response = client.post("/api/auth/verify-otp", json={
            "email": "nina@library.com", "otp": f"{attempt:06d}"})
    assert response.status_code == 400
    assert "too many incorrect attempts" in response.json()["message"].lower()


def test_smtp_password_reset_sends_otp_and_reset_link(api, monkeypatch):
    import smtplib

    client, controller, _ = api
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["connection"] = (host, port, timeout)
            sent.setdefault("messages", [])

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, context=None):
            sent["tls"] = True

        def login(self, username, password):
            sent["credentials"] = (username, password)

        def send_message(self, message):
            if sent.get("fail_delivery"):
                raise smtplib.SMTPException("test transport failure")
            sent["message"] = message.as_string()
            sent["messages"].append(sent["message"])

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "library@example.test")
    monkeypatch.setenv("SMTP_USER", "smtp-user")
    monkeypatch.setenv("SMTP_PASS", "smtp-password")
    monkeypatch.setenv("APP_BASE_URL", "https://library.example.test")

    response = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    assert response.status_code == 200
    assert "dev_otp" not in response.json().get("data", {})
    assert sent["connection"] == ("smtp.example.test", 587, 10)
    assert sent["tls"] is True
    assert sent["credentials"] == ("smtp-user", "smtp-password")
    from email import message_from_string
    message = message_from_string(sent["message"])
    body = next(part for part in message.walk() if part.get_content_type() == "text/plain")
    body = body.get_payload(decode=True).decode(body.get_content_charset())
    assert "password reset code" in body
    assert "10 minutes" in body
    assert "https://library.example.test/reset-password.html?email=nina%40library.com" in body

    controller.register("STU998", "Kim Wells", "kim@library.com", "passw0rd1", role="student")
    response = client.post("/api/auth/forgot-password", json={"email": "kim@library.com"})
    assert response.status_code == 200
    message = message_from_string(sent["message"])
    assert message["To"] == "kim@library.com"
    body = next(part for part in message.walk() if part.get_content_type() == "text/plain")
    body = body.get_payload(decode=True).decode(body.get_content_charset())
    kim_otp = body.split("code is ", 1)[1].split(".", 1)[0]
    verified = client.post("/api/auth/verify-otp", json={"email": "kim@library.com", "otp": kim_otp})
    assert verified.status_code == 200

    controller.register("STU997", "Jordan Wells", "jordan@library.com", "passw0rd1", role="student")
    sent["fail_delivery"] = True
    failed_delivery = client.post("/api/auth/forgot-password", json={"email": "jordan@library.com"})
    assert failed_delivery.status_code == 502
    assert controller.user_dao.verify_otp("jordan@library.com", "000000")[1] == \
        "No active verification code. Please request a new one."
    unknown_account = client.post("/api/auth/forgot-password", json={"email": "ghost@nowhere.io"})
    assert unknown_account.status_code == 200


def test_json_body_rejects_malformed_and_non_object_requests(api):
    client, _, _ = api
    login_as(client, "nina@library.com", "passw0rd1")
    malformed = client.put(
        "/api/profile/preferences",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    non_object = client.put("/api/profile/preferences", json=["not", "an", "object"])
    assert malformed.status_code == 400
    assert non_object.status_code == 400
    assert malformed.json()["message"] == non_object.json()["message"]


def test_existing_sessions_respect_role_and_status_changes(api):
    admin_client, _, app = api
    librarian_client = TestClient(app, follow_redirects=False)
    login_as(admin_client, "admin@library.com", "admin123")
    login_as(librarian_client, "ray@library.com", "passw0rd1")

    changed_role = admin_client.put("/api/users/STAFF01/role", json={"role": "student"})
    assert changed_role.status_code == 200
    assert librarian_client.get("/api/students").status_code == 403
    assert librarian_client.get("/admin/users.html").headers["Location"].endswith("/student/dashboard.html")

    restored_role = admin_client.put("/api/users/STAFF01/role", json={"role": "librarian"})
    assert restored_role.status_code == 200
    assert librarian_client.get("/api/students").status_code == 200
    deactivated = admin_client.put("/api/users/STAFF01/status", json={"status": "inactive"})
    assert deactivated.status_code == 200
    assert librarian_client.get("/api/dashboard").status_code == 401
    assert librarian_client.get("/admin/dashboard.html").headers["Location"].endswith("/login.html")


def test_password_reset_requires_otp_verification_first(api, monkeypatch):
    """The OTP is verified before the reset: a signed token unlocks the change,
    and it cannot be reused, and the reset is refused without OTP or token."""
    client, _, _ = api
    sent_codes = capture_otp_delivery(monkeypatch)
    # Without a verified OTP (and without a token) the reset is rejected
    assert client.post("/api/auth/reset-password", json={
        "email": "nina@library.com", "otp": "000000", "new_password": "newpass99",
        "confirm_password": "newpass99"}).status_code == 400

    response = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    assert response.status_code == 200
    otp = sent_codes[-1]
    verified = client.post("/api/auth/verify-otp", json={"email": "nina@library.com", "otp": otp})
    token = verified.json()["data"]["reset_token"]
    assert token

    reset = client.post("/api/auth/reset-password", json={
        "reset_token": token, "new_password": "brandnew9", "confirm_password": "brandnew9"})
    assert reset.status_code == 200
    login_as(client, "nina@library.com", "brandnew9")
    # A verified token is single-use
    again = client.post("/api/auth/reset-password", json={
        "reset_token": token, "new_password": "onemore99", "confirm_password": "onemore99"})
    assert again.status_code == 400
    # Forged tokens are refused
    assert client.post("/api/auth/reset-password", json={
        "reset_token": "forged-token", "new_password": "hackpass9",
        "confirm_password": "hackpass9"}).status_code == 400


# --- Role authorization ---
def test_students_cannot_reach_admin_apis(api):
    client, _, _ = api
    login_as(client, "nina@library.com", "passw0rd1")
    assert client.get("/api/students").status_code == 403
    assert client.post("/api/books", json={"title": "X", "author": "Y", "isbn": "Z"}).status_code == 403
    assert client.delete("/api/books/1").status_code == 403
    assert client.get("/api/reports/summary").status_code == 403
    assert client.post("/api/borrow", json={"student_id": "STU-OTHER", "book_id": 1}).status_code == 403


def test_dashboard_pages_require_a_session_and_matching_role(api):
    client, controller, _ = api
    assert client.get("/").headers["Location"].endswith("/login.html")
    assert client.get("/student/dashboard.html").status_code == 302
    assert client.get("/admin/dashboard.html").status_code == 302
    assert client.get("/admin/librarian-dashboard.html").status_code == 302

    book_id = add_book(controller, title="Dashboard book", isbn="978-7777777777")
    student_login = login_as(client, "nina@library.com", "passw0rd1")
    assert student_login.json()["data"]["user"]["role"] == "student"
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    assert client.get("/").headers["Location"].endswith("/student/dashboard.html")
    student_dashboard = client.get("/student/dashboard.html")
    assert student_dashboard.status_code == 200
    assert 'data-need="student"' in student_dashboard.text
    assert 'data-page="dash"' in student_dashboard.text
    assert "url=admin/dashboard.html" not in student_dashboard.text
    assert "Dashboard book" in student_dashboard.text
    assert "Robert C. Martin" in student_dashboard.text
    assert client.get("/api/auth/me").json()["data"]["user"]["role"] == "student"
    assert client.get("/student/fines.html").status_code == 200
    assert client.get("/admin/dashboard.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.get("/admin/fines.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.get("/admin/librarian-dashboard.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.get("/admin/users.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/student/dashboard.html").headers["Location"].endswith("/login.html")
    assert client.get("/api/dashboard").status_code == 401

    librarian_login = login_as(client, "ray@library.com", "passw0rd1")
    assert librarian_login.json()["data"]["user"]["role"] == "librarian"
    assert client.get("/").headers["Location"].endswith("/admin/dashboard.html")
    librarian_dashboard = client.get("/admin/dashboard.html")
    assert librarian_dashboard.status_code == 200
    assert 'data-need="staff"' in librarian_dashboard.text
    assert client.get("/admin/librarian-dashboard.html").status_code == 200
    assert client.get("/admin/fines.html").status_code == 200
    assert client.get("/admin/users.html").headers["Location"].endswith("/admin/dashboard.html")

    admin_login = login_as(client, "admin@library.com", "admin123")
    assert admin_login.json()["data"]["user"]["role"] == "admin"
    assert client.get("/").headers["Location"].endswith("/admin/dashboard.html")
    admin_dashboard = client.get("/admin/dashboard.html")
    assert admin_dashboard.status_code == 200
    assert 'data-need="staff"' in admin_dashboard.text
    assert client.get("/admin/users.html").status_code == 200
    assert client.get("/admin/system-settings.html").status_code == 200
    assert client.get("/admin/fines.html").status_code == 200


def test_students_can_return_only_their_own_books(api):
    client, controller, _ = api
    book_id = add_book(controller)
    login_as(client, "nina@library.com", "passw0rd1")
    issued = client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id})
    assert issued.status_code == 200
    transaction_id = controller.list_transactions(student_id="STU999")[0]["id"]
    assert client.post(f"/api/borrow/{transaction_id}/return").status_code == 200
    assert client.post(f"/api/borrow/{transaction_id}/return").status_code == 409


def test_students_cannot_return_another_members_loan(api):
    client, controller, _ = api
    book_id = add_book(controller)
    assert controller.register("STUOTHER", "Other Member", "other@library.com", "passw0rd1",
                               role="student")[0]
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.post("/api/borrow", json={"student_id": "STUOTHER", "book_id": book_id}).status_code == 200
    transaction_id = controller.list_transactions(student_id="STUOTHER")[0]["id"]
    login_as(client, "nina@library.com", "passw0rd1")
    response = client.post(f"/api/borrow/{transaction_id}/return")
    assert response.status_code == 403


def test_librarian_manages_but_only_admin_deletes(api):
    client, _, _ = api
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.get("/api/students").status_code == 200
    assert client.get("/api/students/STU999").status_code == 200
    assert client.put("/api/students/STU999/status", json={"status": "inactive"}).status_code == 200
    assert client.put("/api/students/STU999/status", json={"status": "active"}).status_code == 200
    created = client.post("/api/books", json={"title": "Refactoring", "author": "M. Fowler",
                                              "isbn": "978-0201485677", "total_copies": 1})
    assert created.status_code == 200
    book_id = created.json()["data"]["book"]["id"]
    assert client.delete(f"/api/books/{book_id}").status_code == 403

    login_as(client, "admin@library.com", "admin123")
    assert client.delete(f"/api/books/{book_id}").status_code == 200


# --- Books ---
def test_book_crud_and_search(api):
    client, _, _ = api
    login_as(client, "admin@library.com", "admin123")

    created = client.post("/api/books", json={
        "title": "Clean Code", "author": "Robert C. Martin", "isbn": "978-0132350884",
        "category": "Engineering", "total_copies": 3, "publication_year": 2008,
        "shelf_no": "B2", "description": "A handbook of agile software craftsmanship."})
    assert created.status_code == 200
    book_id = created.json()["data"]["book"]["id"]
    # Every book carries the Rs. 4000 library fee by default
    assert created.json()["data"]["book"]["fee"] == 4000

    assert client.post("/api/books", json={"title": "No Author", "author": "", "isbn": "x"}).status_code == 400
    assert client.post("/api/books", json={"title": "Dup", "author": "A", "isbn": "978-0132350884"}).status_code == 409
    assert client.post("/api/books", json={"title": "Bad", "author": "A", "isbn": "y", "total_copies": -2}).status_code == 400

    updated = client.put(f"/api/books/{book_id}", json={"total_copies": 1, "shelf_no": "C1"})
    assert updated.status_code == 200
    assert updated.json()["data"]["book"]["available_copies"] == 1

    # Custom fee per title can be set and updated
    priced = client.put(f"/api/books/{book_id}", json={"fee": 2500})
    assert priced.status_code == 200
    assert priced.json()["data"]["book"]["fee"] == 2500

    listing = client.get("/api/books?q=clean").json()["data"]["books"]
    assert [b["id"] for b in listing] == [book_id]
    assert client.get("/api/books?availability=available").status_code == 200
    assert client.get(f"/api/books/{book_id}").status_code == 200
    assert client.get("/api/books/9999").status_code == 404


def test_book_cover_url_validation_upload_and_permissions(api, monkeypatch, tmp_path):
    client, _, _ = api
    login_as(client, "admin@library.com", "admin123")
    created = client.post("/api/books", json={
        "title": "Verified Cover Book", "author": "Cover Author", "isbn": "978-0000000001",
        "cover_url": "https://books.google.com/books/content?id=verified&printsec=frontcover&img=1",
    })
    assert created.status_code == 200
    book_id = created.json()["data"]["book"]["id"]
    assert created.json()["data"]["book"]["cover_url"].startswith("https://books.google.com/")
    assert client.put(f"/api/books/{book_id}", json={"cover_url": "javascript:alert(1)"}).status_code == 400

    import routes.book_routes as book_routes
    cover_dir = tmp_path / "book-covers"
    monkeypatch.setattr(book_routes, "BOOK_COVER_DIR", cover_dir)
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/b+8AAAAASUVORK5CYII="
    )
    uploaded = client.put(f"/api/books/{book_id}/cover", json={
        "content_type": "image/png", "image": base64.b64encode(png).decode("ascii"),
    })
    assert uploaded.status_code == 200
    cover_url = uploaded.json()["data"]["book"]["cover_url"]
    cover_path = cover_dir / cover_url.rsplit("/", 1)[-1]
    assert cover_path.is_file()
    assert cover_path.read_bytes() == png

    assert client.put(f"/api/books/{book_id}/cover", json={
        "content_type": "image/png", "image": "not-base64",
    }).status_code == 400
    client.post("/api/auth/logout")
    login_as(client, "nina@library.com", "passw0rd1")
    assert client.put(f"/api/books/{book_id}/cover", json={
        "content_type": "image/png", "image": base64.b64encode(png).decode("ascii"),
    }).status_code == 403


def test_book_cover_lookup_requires_exact_metadata(api, monkeypatch):
    client, _, _ = api
    import routes.book_routes as book_routes

    monkeypatch.setattr(book_routes, "COVER_LOOKUP_CACHE", {})
    monkeypatch.setattr(book_routes, "GOOGLE_BOOKS_COOLDOWN_UNTIL", 0)
    searches = []

    async def no_google_results(_params):
        return []

    async def search_open_library(params):
        searches.append(params)
        if "isbn" in params:
            return [
                {"title": "Unrelated Title", "author_name": ["Other Author"],
                 "isbn": ["9780132350884"], "cover_i": 111},
                {"title": "Clean Code", "author_name": ["Robert C. Martin"],
                 "isbn": ["9780132350884"], "cover_i": 8065615},
            ]
        if "author" in params:
            return [{"title": "Rare Exact Title", "author_name": ["Wrong Author"], "cover_i": 222}]
        return [{"title": "Rare Exact Title", "author_name": ["Cover Author"], "cover_i": 333}]

    monkeypatch.setattr(book_routes, "_search_open_library", search_open_library)
    monkeypatch.setattr(book_routes, "_search_google_books", no_google_results)
    monkeypatch.setattr(book_routes, "_verify_cover_image", lambda _url: _true_async())
    assert client.get("/api/books/cover-lookup", params={
        "isbn": "9780132350884", "title": "Clean Code", "author": "Robert C. Martin",
    }).status_code == 401

    login_as(client, "nina@library.com", "passw0rd1")
    isbn_match = client.get("/api/books/cover-lookup", params={
        "isbn": "9780132350884", "title": "Clean Code", "author": "Robert C. Martin",
    })
    assert isbn_match.json()["data"]["cover_url"] == (
        "https://covers.openlibrary.org/b/id/8065615-L.jpg?default=false"
    )
    assert searches[0] == {"isbn": "9780132350884"}

    title_match = client.get("/api/books/cover-lookup", params={
        "isbn": "NS-9001", "title": "Rare Exact Title", "author": "Cover Author",
    })
    assert title_match.json()["data"]["cover_url"] == (
        "https://covers.openlibrary.org/b/id/333-L.jpg?default=false"
    )
    assert searches[-1] == {"title": "Rare Exact Title"}

    assert book_routes._same_author("Kurose & Ross", ["James F. Kurose", "Keith W. Ross"])
    assert book_routes._same_author("Cormen et al.", ["Thomas H. Cormen", "Charles E. Leiserson"])
    assert book_routes._normalized_book_title(
        "The Pragmatic Bookshelf: Python Crash Course"
    ) == book_routes._normalized_book_title("Python Crash Course")
    assert book_routes._normalized_book_title(
        "A People's History of the United States"
    ) == book_routes._normalized_book_title("A People's History")
    assert book_routes._normalized_book_title(
        "Discrete Mathematics and Its Applications"
    ) == book_routes._normalized_book_title("Discrete Mathematics")
    assert book_routes._open_library_query({
        "title": 'A "Quoted" Title', "author": "Robert C. Martin",
    }) == 'title:"A \\"Quoted\\" Title" AND author:"Robert C. Martin"'
    assert book_routes._open_library_query({
        "title": "The Pragmatic Bookshelf: Python Crash Course", "author": "Eric Matthes",
    }) == 'title:"Python Crash Course" AND author:"Eric Matthes"'
    assert book_routes._book_match(
        {
            "title": "Python Crash Course, 2nd Edition",
            "author_name": ["Eric Matthes"],
            "isbn": ["9781593279288"],
            "cover_i": 8800209,
        },
        "The Pragmatic Bookshelf: Python Crash Course",
        "Eric Matthes",
        "9781593279288",
    )


async def _true_async():
    return True


def test_book_cover_lookup_uses_google_then_open_library_and_saves_only_missing(api, monkeypatch):
    client, controller, _ = api
    import routes.book_routes as book_routes

    monkeypatch.setattr(book_routes, "COVER_LOOKUP_CACHE", {})
    monkeypatch.setattr(book_routes, "GOOGLE_BOOKS_COOLDOWN_UNTIL", 0)
    book_id = add_book(controller)
    google_url = "https://books.google.com/books/content?id=clean-code"
    open_library_url = "https://covers.openlibrary.org/b/id/8065615-L.jpg?default=false"
    google_queries = []
    open_library_queries = []

    async def google_results(params):
        google_queries.append(params)
        if "isbn" not in params:
            return []
        return [{
            "volumeInfo": {
                "title": "Clean Code",
                "authors": ["Robert C. Martin"],
                "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780132350884"}],
                "imageLinks": {"thumbnail": google_url},
            },
        }]

    async def open_library_results(params):
        open_library_queries.append(params)
        if "isbn" not in params:
            return []
        return [{
            "title": "Clean Code",
            "author_name": ["Robert C. Martin"],
            "isbn": ["9780132350884"],
            "cover_i": 8065615,
        }]

    async def verify(url):
        return url == open_library_url

    monkeypatch.setattr(book_routes, "_search_google_books", google_results)
    monkeypatch.setattr(book_routes, "_search_open_library", open_library_results)
    monkeypatch.setattr(book_routes, "_verify_cover_image", verify)
    login_as(client, "nina@library.com", "passw0rd1")

    response = client.get("/api/books/cover-lookup", params={"book_id": book_id})
    assert response.status_code == 200
    assert response.json()["data"]["cover_url"] == open_library_url
    assert google_queries[0] == {"isbn": "9780132350884"}
    assert open_library_queries[0] == {"isbn": "9780132350884"}
    assert controller.get_book(book_id)["cover_url"] == open_library_url

    existing_url = "https://covers.openlibrary.org/b/id/999-L.jpg?default=false"
    assert controller.update_book(book_id, cover_url=existing_url)[0]
    second_book_id = controller.register_book(
        "Clean Code", "Robert C. Martin", "978-0132350885", category="Engineering",
        total_copies=1, cover_url=existing_url,
    )
    second = client.get("/api/books/cover-lookup", params={"book_id": second_book_id})
    assert second.status_code == 200
    assert controller.get_book(second_book_id)["cover_url"] == existing_url


def test_book_cover_lookup_reports_provider_failure(api, monkeypatch):
    client, _, _ = api
    import httpx
    import routes.book_routes as book_routes

    login_as(client, "nina@library.com", "passw0rd1")
    monkeypatch.setattr(book_routes, "COVER_LOOKUP_CACHE", {})

    async def unavailable(_params):
        raise httpx.ConnectError("provider unavailable", request=httpx.Request("GET", "https://openlibrary.org"))

    monkeypatch.setattr(book_routes, "_search_open_library", unavailable)
    response = client.get("/api/books/cover-lookup", params={
        "isbn": "9780132350884", "title": "Clean Code", "author": "Robert C. Martin",
    })
    assert response.status_code == 502
    assert response.json()["message"] == "Book cover lookup is temporarily unavailable."


def test_book_cover_lookup_replaces_only_a_failed_saved_cover(api, monkeypatch):
    client, controller, _ = api
    import routes.book_routes as book_routes

    monkeypatch.setattr(book_routes, "COVER_LOOKUP_CACHE", {})
    book_id = add_book(controller)
    failed_url = "https://covers.openlibrary.org/b/id/999-L.jpg?default=false"
    valid_url = "https://covers.openlibrary.org/b/id/8065615-L.jpg?default=false"
    assert controller.update_book(book_id, cover_url=failed_url)[0]

    async def google_results(_params):
        return []

    async def open_library_results(params):
        if "isbn" in params:
            return [{
                "title": "Clean Code",
                "author_name": ["Robert C. Martin"],
                "isbn": ["9780132350884"],
                "cover_i": 8065615,
            }]
        return []

    async def verify(url):
        return url == valid_url

    monkeypatch.setattr(book_routes, "_search_google_books", google_results)
    monkeypatch.setattr(book_routes, "_search_open_library", open_library_results)
    monkeypatch.setattr(book_routes, "_verify_cover_image", verify)
    login_as(client, "nina@library.com", "passw0rd1")

    response = client.get(
        "/api/books/cover-lookup",
        params={"book_id": book_id, "exclude": failed_url},
    )
    assert response.status_code == 200
    assert response.json()["data"]["cover_url"] == valid_url
    assert controller.get_book(book_id)["cover_url"] == valid_url


# --- Borrow / Return ---
def test_borrow_return_cycle_and_guards(api):
    client, controller, fastapi_app = api
    login_as(client, "ray@library.com", "passw0rd1")
    book_id = add_book(controller, copies=1)

    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    assert controller.get_book(book_id)["available_copies"] == 0
    # no copies left -> rejected; duplicate active loan -> rejected
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 409

    loans = client.get("/api/borrow?scope=all").json()["data"]["transactions"]
    loan_id = loans[0]["id"]

    # duplicate return protection
    assert client.post(f"/api/borrow/{loan_id}/return").status_code == 200
    assert client.post(f"/api/borrow/{loan_id}/return").status_code == 409
    assert controller.get_book(book_id)["available_copies"] == 1

    # the student sees the return notification on their own session
    student_client = TestClient(fastapi_app, follow_redirects=False)
    login_as(student_client, "nina@library.com", "passw0rd1")
    notes = student_client.get("/api/notifications").json()["data"]["notifications"]
    assert any(n.get("type") == "return" for n in notes)


def test_staff_fine_collection_updates_records_and_notifies_student(api):
    client, controller, fastapi_app = api
    book_id = add_book(controller, isbn="978-4444444444")
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    transaction_id = controller.borrow_dao.list_transactions(student_id="STU999")[0]["id"]
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE transactions SET due_date=DATE('now', '-5 days') WHERE id=?", (transaction_id,))
    assert client.post(f"/api/borrow/{transaction_id}/return").status_code == 200

    fines_response = client.get("/api/fines?status=unpaid")
    assert fines_response.status_code == 200, fines_response.json()
    fines = fines_response.json()["data"]["fines"]
    assert len(fines) == 1
    fine_id = fines[0]["id"]
    assert fines[0]["student_name"] == "Nina Wells"
    assert fines[0]["status"] == "unpaid"
    assert client.get(f"/api/fines?q={fine_id}").json()["data"]["fines"][0]["id"] == fine_id
    member_details = client.get("/api/students/STU999").json()["data"]
    assert member_details["fines"][0]["id"] == fine_id
    assert member_details["borrow_history"][0]["return_date"]

    student_client = TestClient(fastapi_app, follow_redirects=False)
    login_as(student_client, "nina@library.com", "passw0rd1")
    assert student_client.post(f"/api/fines/{fine_id}/collect").status_code == 403

    collected = client.post(f"/api/fines/{fine_id}/collect")
    assert collected.status_code == 200, collected.json()
    fine = collected.json()["data"]["fine"]
    assert fine["status"] == "paid"
    assert fine["collected_by"] == "STAFF01"
    assert fine["payment_date"]
    assert client.post(f"/api/fines/{fine_id}/collect").status_code == 409

    student_fines = student_client.get("/api/borrow/fines").json()["data"]["fines"]
    assert student_fines[0]["status"] == "paid"
    student_notes = student_client.get("/api/notifications").json()["data"]["notifications"]
    assert any(note["type"] == "fine" for note in student_notes)
    assert any(log["action"] == "FINE_COLLECTED" for log in controller.get_activity_logs())


def test_overdue_detection_and_sweep(api):
    client, controller, _ = api
    login_as(client, "ray@library.com", "passw0rd1")
    book_id = add_book(controller, isbn="978-1111111111")
    client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id, "days": 1})
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE transactions SET due_date = DATE('now', '-5 days')")
    result = controller.run_overdue_sweep()
    assert result["newly_marked_overdue"] >= 1
    notes = controller.notification_dao.get_user_notifications("STU999")
    assert any(n["type"] == "overdue" for n in notes)
    # a second sweep must not duplicate notifications or re-mark anything
    sweep_again = controller.run_overdue_sweep()
    overdue_notes = [n for n in controller.notification_dao.get_user_notifications("STU999")
                     if n["type"] == "overdue"]
    assert len(overdue_notes) == 1
    assert sweep_again["newly_marked_overdue"] == 0


# --- Book fee (Rs. 4000): admin uploads, admin grants paid, unpaid blocks borrowing ---
def test_admin_uploads_fee_and_controls_payment(api):
    client, controller, fastapi_app = api
    book_id = add_book(controller, isbn="978-8888888888", copies=1)
    controller.register("STUOTHER", "Other Member", "other@library.com", "passw0rd1", role="student")

    # only the ADMIN can upload a fee (librarian and student are refused)
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.post("/api/fees", json={"student_id": "STU999"}).status_code == 403
    login_as(client, "nina@library.com", "passw0rd1")
    assert client.post("/api/fees", json={"student_id": "STU999"}).status_code == 403

    # the admin uploads the fee — default amount is the library fee (Rs. 4000)
    login_as(client, "admin@library.com", "admin123")
    uploaded = client.post("/api/fees", json={"student_id": "STU999", "book_id": book_id})
    assert uploaded.status_code == 200, uploaded.json()
    fee = uploaded.json()["data"]["fee"]
    assert fee["amount"] == 4000
    assert fee["status"] == "unpaid"
    assert fee["uploaded_by"] == "ADMIN001"

    # the fee is published to the student portal automatically
    login_as(client, "nina@library.com", "passw0rd1")
    my_fees = client.get("/api/fees").json()["data"]["fees"]
    assert [f["id"] for f in my_fees] == [fee["id"]]
    assert my_fees[0]["status"] == "unpaid"

    # unpaid fee -> no book: borrowing is blocked until the fee is paid
    blocked = client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id})
    assert blocked.status_code == 403
    assert "unpaid book fee" in blocked.json()["message"]

    # the student cannot grant "paid", and neither can the librarian — admin only
    assert client.post(f"/api/fees/{fee['id']}/pay").status_code == 403
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.post(f"/api/fees/{fee['id']}/pay").status_code == 403

    # the admin grants paid -> the student portal shows it automatically
    login_as(client, "admin@library.com", "admin123")
    paid = client.post(f"/api/fees/{fee['id']}/pay")
    assert paid.status_code == 200, paid.json()
    assert paid.json()["data"]["fee"]["status"] == "paid"
    assert paid.json()["data"]["fee"]["collected_by"] == "ADMIN001"

    # fee paid -> the book is issued, and the student portal shows the paid fee
    login_as(client, "nina@library.com", "passw0rd1")
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    portal = client.get("/api/fees").json()["data"]["fees"]
    assert portal[0]["status"] == "paid"
    # the student was notified about the upload and the payment
    notes = controller.notification_dao.get_user_notifications("STU999")
    assert any(n["type"] == "fee" for n in notes)
    assert any(log["action"] == "FEE_UPLOADED" for log in controller.get_activity_logs())
    # the PDF receipt is still downloadable (also after payment)
    receipt = client.get(f"/api/fees/{fee['id']}/receipt.pdf")
    assert receipt.status_code == 200
    assert receipt.headers["content-type"].startswith("application/pdf")
    assert receipt.content.startswith(b"%PDF")


def test_fee_upload_defaults_to_configured_amount(api):
    client, controller, _ = api
    login_as(client, "admin@library.com", "admin123")
    assert client.put("/api/settings", json={"book_fee": 500}).status_code == 200
    uploaded = client.post("/api/fees", json={"student_id": "STU999"})
    assert uploaded.status_code == 200, uploaded.json()
    assert uploaded.json()["data"]["fee"]["amount"] == 500
    # unknown member and invalid amounts are rejected
    assert client.post("/api/fees", json={"student_id": "GHOST"}).status_code == 404
    assert client.post("/api/fees", json={"student_id": "STU999", "amount": 0}).status_code == 400


# --- Reservations ---
def test_reservation_lifecycle(api):
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-2222222222")
    login_as(client, "nina@library.com", "passw0rd1")

    assert client.post("/api/reservations", json={"book_id": book_id}).status_code == 200
    reservation_id = controller.reservation_dao.list_reservations(student_id="STU999")[0]["id"]
    # duplicate active reservation blocked
    assert client.post("/api/reservations", json={"book_id": book_id}).status_code == 409

    login_as(client, "ray@library.com", "passw0rd1")
    assert client.put(f"/api/reservations/{reservation_id}", json={"action": "approve"}).status_code == 200
    assert client.put(f"/api/reservations/{reservation_id}", json={"action": "approve"}).status_code == 409
    # issuing the book auto-fulfils the approved reservation
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    assert controller.reservation_dao.get_by_id(reservation_id)["status"] == "fulfilled"

    notes = controller.notification_dao.get_user_notifications("STU999")
    assert any(n.get("type") == "reservation" for n in notes)


def test_student_cannot_cancel_others_reservation(api):
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-3333333333")
    controller.register("STU777", "Zoe Ray", "zoe@library.com", "passw0rd1")
    controller.reserve_book("STU777", book_id)
    reservation_id = controller.reservation_dao.list_reservations(student_id="STU777")[0]["id"]

    login_as(client, "nina@library.com", "passw0rd1")
    assert client.put(f"/api/reservations/{reservation_id}", json={"action": "cancel"}).status_code == 409
    assert controller.reservation_dao.get_by_id(reservation_id)["status"] == "pending"

    login_as(client, "ray@library.com", "passw0rd1")
    assert client.put(f"/api/reservations/{reservation_id}", json={"action": "reject"}).status_code == 200


# --- Notifications ---
def test_notification_read_state(api):
    client, controller, _ = api
    login_as(client, "nina@library.com", "passw0rd1")
    controller.notification_dao.notify("STU999", "Hello", "Test message")
    data = client.get("/api/notifications").json()["data"]
    assert data["unread"] >= 1
    note_id = data["notifications"][0]["id"]
    assert client.put(f"/api/notifications/{note_id}/read").status_code == 200
    assert client.put("/api/notifications/read-all").status_code == 200
    assert client.get("/api/notifications/unread-count").json()["data"]["unread"] == 0


# --- Profile & settings ---
def test_profile_update_change_password_and_preferences(api):
    client, _, _ = api
    login_as(client, "nina@library.com", "passw0rd1")

    updated = client.put("/api/profile", json={"name": "Nina C. Wells", "phone": "0300-1234567"})
    assert updated.status_code == 200
    assert updated.json()["data"]["profile"]["name"] == "Nina C. Wells"

    assert client.put("/api/profile/password", json={
        "current_password": "wrongpass", "new_password": "passw0rd2",
        "confirm_password": "passw0rd2"}).status_code == 400
    assert client.put("/api/profile/password", json={
        "current_password": "passw0rd1", "new_password": "passw0rd2",
        "confirm_password": "passw0rd2"}).status_code == 200
    login_as(client, "nina@library.com", "passw0rd2")

    prefs = client.put("/api/profile/preferences", json={"due_reminders": False})
    assert prefs.json()["data"]["preferences"]["due_reminders"] is False


def test_student_avatar_upload_replace_and_remove(api):
    from io import BytesIO
    from pathlib import Path

    from PIL import Image

    client, _, _ = api
    image_data = BytesIO()
    Image.new("RGB", (12, 12), color=(96, 72, 180)).save(image_data, format="PNG")
    png = image_data.getvalue()

    assert client.post("/api/profile/avatar", files={"file": ("avatar.png", png, "image/png")}).status_code == 401
    login_as(client, "ray@library.com", "passw0rd1")
    librarian_upload = client.post(
        "/api/profile/avatar",
        files={"file": ("avatar.png", png, "image/png")},
    )
    assert librarian_upload.status_code == 200
    librarian_url = librarian_upload.json()["data"]["profile"]["avatar_url"]
    librarian_path = Path(__file__).resolve().parents[1] / "frontend" / librarian_url.lstrip("/")
    assert librarian_path.is_file()
    assert client.delete("/api/profile/avatar").status_code == 200
    assert not librarian_path.exists()
    client.post("/api/auth/logout")

    login_as(client, "nina@library.com", "passw0rd1")
    invalid = client.post(
        "/api/profile/avatar",
        files={"file": ("avatar.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 400
    too_large = client.post(
        "/api/profile/avatar",
        files={"file": ("large.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")},
    )
    assert too_large.status_code == 413

    uploaded = client.post(
        "/api/profile/avatar",
        files={"file": ("avatar.png", png, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.json()
    first_url = uploaded.json()["data"]["profile"]["avatar_url"]
    first_path = Path(__file__).resolve().parents[1] / "frontend" / first_url.lstrip("/")
    assert first_path.is_file()
    assert client.get(first_url).status_code == 200
    assert client.get("/api/profile").json()["data"]["profile"]["avatar_url"] == first_url
    assert client.get("/api/auth/me").json()["data"]["user"]["avatar_url"] == first_url

    replacement = client.post(
        "/api/profile/avatar",
        files={"file": ("avatar.png", png, "image/png")},
    )
    assert replacement.status_code == 200, replacement.json()
    second_url = replacement.json()["data"]["profile"]["avatar_url"]
    second_path = Path(__file__).resolve().parents[1] / "frontend" / second_url.lstrip("/")
    assert second_url != first_url
    assert not first_path.exists()
    assert second_path.is_file()

    removed = client.delete("/api/profile/avatar")
    assert removed.status_code == 200
    assert removed.json()["data"]["profile"]["avatar_url"] is None
    assert not second_path.exists()
    assert client.get("/api/auth/me").json()["data"]["user"]["avatar_url"] is None


def test_librarian_profile_page_and_account_endpoints(api):
    client, _, _ = api
    assert client.get("/librarian/profile.html").status_code == 302
    login_as(client, "ray@library.com", "passw0rd1")

    page = client.get("/librarian/profile.html")
    assert page.status_code == 200
    assert "Workspace" in page.text
    assert "My Profile" in page.text
    assert "Change password" in page.text

    profile = client.get("/api/profile")
    assert profile.status_code == 200
    assert profile.json()["data"]["profile"]["role"] == "librarian"

    updated = client.put("/api/profile", json={
        "name": "librarian ray", "phone": "555-0101",
        "department": "", "semester": "",
    })
    assert updated.status_code == 200
    assert updated.json()["data"]["profile"]["phone"] == "555-0101"

    wrong_password = client.post("/api/profile/password", json={
        "current_password": "wrongpass", "new_password": "newpass123",
        "confirm_password": "newpass123",
    })
    assert wrong_password.status_code == 400
    changed = client.post("/api/profile/password", json={
        "current_password": "passw0rd1", "new_password": "newpass123",
        "confirm_password": "newpass123",
    })
    assert changed.status_code == 200
    client.post("/api/auth/logout")
    login_as(client, "nina@library.com", "passw0rd1")
    restricted_page = client.get("/librarian/profile.html", follow_redirects=False)
    assert restricted_page.status_code == 302
    assert restricted_page.headers["location"] == "/student/dashboard.html"


def test_librarian_profile_and_password_endpoints(api):
    client, _, _ = api
    assert client.get("/api/librarian/profile").status_code == 401

    login_as(client, "nina@library.com", "passw0rd1")
    assert client.get("/api/librarian/profile").status_code == 403
    client.post("/api/auth/logout")

    login_as(client, "admin@library.com", "admin123")
    assert client.get("/api/librarian/profile").status_code == 403
    client.post("/api/auth/logout")

    login_as(client, "ray@library.com", "passw0rd1")
    profile = client.get("/api/librarian/profile")
    assert profile.status_code == 200
    assert profile.json()["data"]["profile"] == {
        "user_id": "STAFF01",
        "name": "Librarian Ray",
        "email": "ray@library.com",
        "role": "librarian",
    }

    invalid_email = client.put("/api/librarian/profile", json={
        "name": "Librarian Ray", "email": "not-an-email",
    })
    assert invalid_email.status_code == 400
    duplicate_email = client.put("/api/librarian/profile", json={
        "name": "Librarian Ray", "email": "nina@library.com",
    })
    assert duplicate_email.status_code == 409

    updated = client.put("/api/librarian/profile", json={
        "name": "Ray Northstar", "email": "ray.northstar@library.com",
    })
    assert updated.status_code == 200
    assert updated.json()["data"]["profile"]["name"] == "Ray Northstar"
    assert updated.json()["data"]["profile"]["email"] == "ray.northstar@library.com"
    assert client.get("/api/auth/me").json()["data"]["user"]["email"] == "ray.northstar@library.com"

    wrong_password = client.post("/api/librarian/change-password", json={
        "current_password": "wrongpass", "new_password": "newpass2",
        "confirm_password": "newpass2",
    })
    assert wrong_password.status_code == 400
    short_password = client.post("/api/librarian/change-password", json={
        "current_password": "passw0rd1", "new_password": "short",
        "confirm_password": "short",
    })
    assert short_password.status_code == 400
    mismatch = client.post("/api/librarian/change-password", json={
        "current_password": "passw0rd1", "new_password": "newpass2",
        "confirm_password": "different",
    })
    assert mismatch.status_code == 400
    changed = client.post("/api/librarian/change-password", json={
        "current_password": "passw0rd1", "new_password": "newp12",
        "confirm_password": "newp12",
    })
    assert changed.status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={
        "credential": "ray.northstar@library.com", "password": "newp12",
    }).status_code == 200


# --- Dashboards & reports ---
def test_dashboards_and_reports(api):
    client, controller, _ = api
    book_id = add_book(controller)
    login_as(client, "admin@library.com", "admin123")
    client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id})

    login_as(client, "nina@library.com", "passw0rd1")
    student_view = client.get("/api/dashboard").json()["data"]
    assert student_view["role_view"] == "student"
    assert student_view["stats"]["active_loans"] == 1

    login_as(client, "admin@library.com", "admin123")
    admin_view = client.get("/api/dashboard").json()["data"]
    assert admin_view["role_view"] == "staff"
    assert admin_view["stats"]["total_books"] >= 1
    assert client.get("/api/reports/summary").status_code == 200
    assert client.get("/api/reports/borrowing?days=7").status_code == 200
    assert client.get("/api/reports/top-books").status_code == 200
    assert client.get("/api/reports/overdue").status_code == 200


# --- Fine collection & waiver ---
def create_overdue_fine(api):
    """Helper: issue a book, backdate it, return it -> an unpaid fine exists."""
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-4444444444", copies=1)
    controller.borrow_dao.issue_book("STU999", book_id, 1)
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE transactions SET due_date = DATE('now', '-6 days')")
    controller.return_book(1)
    fines = controller.list_fines(status="unpaid")
    assert fines, "expected an unpaid fine after a late return"
    return fines[0]["id"]


def test_fine_collect_flow(api):
    client, controller, _ = api
    fine_id = create_overdue_fine(api)
    login_as(client, "ray@library.com", "passw0rd1")

    listing = client.get("/api/fines").json()["data"]
    assert listing["summary"]["outstanding"] > 0
    assert any(f["id"] == fine_id for f in listing["fines"])

    collected = client.post(f"/api/fines/{fine_id}/collect")
    assert collected.status_code == 200
    assert collected.json()["data"]["fine"]["status"] == "paid"
    assert collected.json()["data"]["fine"]["collected_by"]
    # duplicate payment is rejected
    assert client.post(f"/api/fines/{fine_id}/collect").status_code == 409
    # student was notified
    notes = controller.notification_dao.get_user_notifications("STU999")
    assert any(n["type"] == "fine" for n in notes)
    logs = controller.user_dao.get_all_activity_logs(limit=50)
    assert any(log["action"] == "FINE_COLLECTED" for log in logs)


def test_fine_waive_requires_admin_and_reason(api):
    client, controller, _ = api
    fine_id = create_overdue_fine(api)

    login_as(client, "ray@library.com", "passw0rd1")
    assert client.post(f"/api/fines/{fine_id}/waive", json={"reason": "damaged barcode"}).status_code == 403

    login_as(client, "admin@library.com", "admin123")
    assert client.post(f"/api/fines/{fine_id}/waive", json={"reason": "ok"}).status_code == 400
    waived = client.post(f"/api/fines/{fine_id}/waive", json={"reason": "barcode damaged, goodwill waiver"})
    assert waived.status_code == 200
    assert waived.json()["data"]["fine"]["status"] == "waived"
    assert waived.json()["data"]["fine"]["waived_by"] == "ADMIN001"
    logs = controller.user_dao.get_all_activity_logs(limit=50)
    assert any(log["action"] == "FINE_WAIVED" for log in logs)


# --- Administrator user management ---
def test_admin_user_management(api):
    client, controller, _ = api
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.get("/api/users").status_code == 403  # staff but not admin

    login_as(client, "admin@library.com", "admin123")
    users = client.get("/api/users?role=librarian").json()["data"]["users"]
    assert [u["role"] for u in users] == ["librarian"]
    assert client.put("/api/users/STAFF01/status", json={"status": "inactive"}).status_code == 200
    assert controller.get_user("STAFF01")["status"] == "inactive"
    assert client.put("/api/users/STAFF01/status", json={"status": "active"}).status_code == 200
    assert client.put("/api/users/ADMIN001/status", json={"status": "inactive"}).status_code == 409

    promoted = client.put("/api/users/STAFF01/role", json={"role": "admin"})
    assert promoted.status_code == 200
    assert promoted.json()["data"]["user"]["role"] == "admin"
    # self role change blocked
    assert client.put("/api/users/ADMIN001/role", json={"role": "student"}).status_code == 409
    assert client.put("/api/users/STAFF01/role", json={"role": "bogus"}).status_code == 400


def test_admin_creates_staff_and_manages_own_profile_security(api):
    client, controller, _ = api
    assert client.get("/api/admin/profile").status_code == 401
    assert client.post("/api/admin/change-password", json={
        "current_password": "admin123", "new_password": "newpass99",
        "confirm_password": "newpass99",
    }).status_code == 401
    staff_payload = {
        "user_id": "LIBR002",
        "name": "Librarian Two",
        "email": "librarian.two@library.com",
        "role": "librarian",
        "password": "secure123",
        "confirm_password": "secure123",
    }
    assert client.post("/api/users", json=staff_payload).status_code == 401

    login_as(client, "nina@library.com", "passw0rd1")
    assert client.post("/api/users", json=staff_payload).status_code == 403
    client.post("/api/auth/logout")

    login_as(client, "admin@library.com", "admin123")
    created = client.post("/api/users", json=staff_payload)
    assert created.status_code == 200
    assert created.json()["data"]["user"]["role"] == "librarian"
    assert "password" not in created.json()["data"]["user"]
    assert client.post("/api/users", json=staff_payload).status_code == 409
    assert client.post("/api/users", json={**staff_payload, "role": "admin", "user_id": "ADMIN002"}).status_code == 400
    student_payload = {
        **staff_payload,
        "user_id": "STU998",
        "name": "Student Example",
        "email": "student.example@library.com",
        "role": "student",
    }
    created_student = client.post("/api/users", json=student_payload)
    assert created_student.status_code == 200
    assert created_student.json()["data"]["user"]["role"] == "student"

    profile = client.get("/api/admin/profile")
    assert profile.status_code == 200
    assert profile.json()["data"]["profile"]["user_id"] == "ADMIN001"
    assert "password" not in profile.json()["data"]["profile"]

    assert client.put("/api/admin/profile", json={
        "name": "System Administrator", "email": "invalid",
    }).status_code == 400
    assert client.put("/api/admin/profile", json={
        "name": "System Administrator", "email": "nina@library.com",
    }).status_code == 409
    updated = client.put("/api/admin/profile", json={
        "name": "System Admin", "email": "sysadmin@library.com",
    })
    assert updated.status_code == 200
    assert client.get("/api/auth/me").json()["data"]["user"]["email"] == "sysadmin@library.com"

    assert client.post("/api/admin/change-password", json={
        "current_password": "wrongpass", "new_password": "newpass99",
        "confirm_password": "newpass99",
    }).status_code == 400
    changed = client.post("/api/admin/change-password", json={
        "current_password": "admin123", "new_password": "newpass99",
        "confirm_password": "newpass99",
    })
    assert changed.status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={
        "credential": "sysadmin@library.com", "password": "newpass99",
    }).status_code == 200
    assert controller.get_user("LIBR002")["role"] == "librarian"


# --- System settings ---
def test_system_settings_read_and_write(api):
    client, _, _ = api
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.get("/api/settings").status_code == 200
    assert client.put("/api/settings", json={"fine_per_day": 5}).status_code == 403

    login_as(client, "admin@library.com", "admin123")
    saved = client.put("/api/settings", json={"fine_per_day": 12, "library_name": "Northstar Library"})
    assert saved.status_code == 200
    assert saved.json()["data"]["fine_per_day"] == "12"
    assert client.put("/api/settings", json={"loan_period_days": -3}).status_code == 400
    # the Rs. 4000 book fee is administrator-editable
    assert client.put("/api/settings", json={"book_fee": 3500}).status_code == 200
    assert client.put("/api/settings", json={"book_fee": -1}).status_code == 400


def test_setting_driven_fine_rate(api):
    client, controller, _ = api
    login_as(client, "admin@library.com", "admin123")
    client.put("/api/settings", json={"fine_per_day": 3})
    book_id = add_book(controller, isbn="978-5555555555", copies=1)
    controller.borrow_dao.issue_book("STU999", book_id, 1)
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE transactions SET due_date = DATE('now', '-4 days')")
    success, _msg, fine = controller.return_book(1)
    assert success
    assert fine == 12.0  # 4 overdue days x Rs. 3 configured rate


def test_due_soon_notifications_use_configured_window(api):
    client, controller, _ = api
    login_as(client, "admin@library.com", "admin123")
    client.put("/api/settings", json={"due_soon_days": 1})
    book_id = add_book(controller, isbn="978-7777777777")
    success, _, transaction_id = controller.borrow_dao.issue_book("STU999", book_id, 14)
    assert success
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE transactions SET due_date=DATE('now', '+2 days') WHERE id=?", (transaction_id,))
    controller.run_overdue_sweep()
    notifications = controller.notification_dao.get_user_notifications("STU999")
    assert not any(note["type"] == "due_soon" for note in notifications)

    client.put("/api/settings", json={"due_soon_days": 3})
    controller.run_overdue_sweep()
    notifications = controller.notification_dao.get_user_notifications("STU999")
    assert any(note["type"] == "due_soon" for note in notifications)


# --- Student self-service borrowing ---
def test_student_self_borrow(api):
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-6666666666", copies=2)

    login_as(client, "nina@library.com", "passw0rd1")
    ok = client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id, "days": 7})
    assert ok.status_code == 200
    # cannot borrow on behalf of someone else
    other = client.post("/api/borrow", json={"student_id": "STU555", "book_id": book_id})
    assert other.status_code == 403


# --- Book catalog sorting ---
def test_book_sorting(api):
    client, controller, _ = api
    controller.register_book("Aardvark Tales", "Ann Author", "978-7777777771", category="Fiction")
    controller.register_book("Zebra Nights", "Zoe Author", "978-7777777772", category="Fiction")

    login_as(client, "nina@library.com", "passw0rd1")
    titles_title = [b["title"] for b in
                    client.get("/api/books?sort=title").json()["data"]["books"]]
    assert titles_title == sorted(titles_title, key=str.lower)
    assert client.get("/api/books?sort=bogus").status_code == 400


# --- Student wishlist and loan renewal ---
def test_student_wishlist_toggle_is_private_and_student_only(api):
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-8888888881")
    assert client.get("/api/student/wishlist").status_code == 401

    login_as(client, "nina@library.com", "passw0rd1")
    saved = client.post(f"/api/student/wishlist/{book_id}")
    assert saved.status_code == 200
    assert saved.json()["data"]["saved"] is True
    wishlist = client.get("/api/student/wishlist")
    assert [item["book_id"] for item in wishlist.json()["data"]["wishlist"]] == [book_id]

    removed = client.post(f"/api/student/wishlist/{book_id}")
    assert removed.status_code == 200
    assert removed.json()["data"]["saved"] is False
    assert client.get("/api/student/wishlist").json()["data"]["wishlist"] == []
    assert client.post("/api/student/wishlist/999999").status_code == 404

    client.post("/api/auth/logout")
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.get("/api/student/wishlist").status_code == 403


def test_student_loan_can_be_renewed_once_by_seven_days(api):
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-8888888882", copies=1)
    login_as(client, "nina@library.com", "passw0rd1")
    borrowed = client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id, "days": 14})
    assert borrowed.status_code == 200

    with DatabaseConnection().get_connection() as conn:
        loan_id = conn.execute(
            "SELECT id FROM transactions WHERE student_id='STU999' AND book_id=?",
            (book_id,),
        ).fetchone()["id"]
        original_due_date = conn.execute(
            "SELECT due_date FROM transactions WHERE id=?",
            (loan_id,),
        ).fetchone()["due_date"]

    renewed = client.post(f"/api/student/loans/{loan_id}/renew")
    assert renewed.status_code == 200, renewed.json()
    expected_due_date = DatabaseConnection().get_connection().execute(
        "SELECT DATE(?, '+7 days')",
        (original_due_date,),
    ).fetchone()[0]
    assert renewed.json()["data"]["due_date"] == expected_due_date
    assert loan_id in client.get("/api/student/loans/renewals").json()["data"]["renewed_loan_ids"]

    second_attempt = client.post(f"/api/student/loans/{loan_id}/renew")
    assert second_attempt.status_code == 409
    with DatabaseConnection().get_connection() as conn:
        assert conn.execute(
            "SELECT due_date FROM transactions WHERE id=?",
            (loan_id,),
        ).fetchone()["due_date"] == expected_due_date


def test_student_cannot_renew_another_or_overdue_loan(api):
    client, controller, _ = api
    book_id = add_book(controller, isbn="978-8888888883", copies=1)
    assert controller.register(
        "STUOTHER", "Other Member", "other@library.com", "passw0rd1", role="student",
        department="CS", semester="4",
    )
    login_as(client, "nina@library.com", "passw0rd1")
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    with DatabaseConnection().get_connection() as conn:
        loan_id = conn.execute(
            "SELECT id FROM transactions WHERE student_id='STU999' AND book_id=?",
            (book_id,),
        ).fetchone()["id"]

    client.post("/api/auth/logout")
    login_as(client, "other@library.com", "passw0rd1")
    assert client.post(f"/api/student/loans/{loan_id}/renew").status_code == 404

    client.post("/api/auth/logout")
    login_as(client, "nina@library.com", "passw0rd1")
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE transactions SET due_date=DATE('now', '-1 day') WHERE id=?", (loan_id,))
    overdue = client.post(f"/api/student/loans/{loan_id}/renew")
    assert overdue.status_code == 409
    assert overdue.json()["message"] == "Overdue loans cannot be renewed."
