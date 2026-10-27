"""End-to-end API tests: auth, role authorization, books, borrow/return, reservations,
notifications, overdue sweep, OTP reset, book fee + PDF receipt, profile — all against
an in-memory database."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from config.database import DatabaseConnection


@pytest.fixture
def api(monkeypatch):
    # Fixed environment so tests never depend on a local .env
    monkeypatch.setenv("ADMIN_EMAIL", "admin@library.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("OTP_DEV_MODE", "1")
    # the live server runs HTTPS with Secure cookies; the test client is plain HTTP
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")
    monkeypatch.delenv("SMTP_HOST", raising=False)

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


def add_book(controller, title="Clean Code", isbn="978-0132350884", copies=2):
    book_id = controller.register_book(title, "Robert C. Martin", isbn, category="Engineering",
                                       total_copies=copies)
    assert book_id
    return book_id


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
    assert wrong.json()["message"] == "Incorrect password."

    missing = client.post("/api/auth/login", json={"credential": "missing@library.com", "password": "secret12"})
    assert missing.status_code == 404
    assert missing.json()["message"] == "Account not found."

    deactivated = client.post("/api/auth/register", json={
        "student_id": "STU-2049", "full_name": "Inactive User", "email": "inactive@uni.edu",
        "password": "secret12", "confirm_password": "secret12"})
    assert deactivated.status_code == 200
    with DatabaseConnection().get_connection() as conn:
        conn.execute("UPDATE users SET status='inactive' WHERE email='inactive@uni.edu'")
    disabled = client.post("/api/auth/login", json={"credential": "inactive@uni.edu", "password": "secret12"})
    assert disabled.status_code == 403
    assert disabled.json()["message"] == "Your account has been disabled. Please contact the library administrator."

    login_as(client, "alex@uni.edu", "secret12")
    me = client.get("/api/auth/me").json()
    assert me["data"]["user"]["email"] == "alex@uni.edu"
    assert "password" not in me["data"]["user"]


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


def test_password_reset_otp_flow(api):
    client, _, _ = api
    response = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    otp = response.json()["data"]["dev_otp"]
    assert len(otp) == 6

    assert client.post("/api/auth/verify-otp", json={"email": "nina@library.com", "otp": "000000"}).status_code == 400
    assert client.post("/api/auth/verify-otp", json={"email": "nina@library.com", "otp": otp}).status_code == 200
    reset = client.post("/api/auth/reset-password", json={
        "email": "nina@library.com", "otp": otp, "new_password": "newpass99", "confirm_password": "newpass99"})
    assert reset.status_code == 200
    login_as(client, "nina@library.com", "newpass99")
    # The used OTP cannot reset the password a second time
    assert client.post("/api/auth/reset-password", json={
        "email": "nina@library.com", "otp": otp, "new_password": "another12",
        "confirm_password": "another12"}).status_code == 400
    # Unknown email gets a neutral answer (no account enumeration)
    assert client.post("/api/auth/forgot-password", json={"email": "ghost@nowhere.io"}).status_code == 200


def test_password_reset_requires_otp_verification_first(api):
    """The OTP is verified before the reset: a signed token unlocks the change,
    and it cannot be reused, and the reset is refused without OTP or token."""
    client, _, _ = api
    # Without a verified OTP (and without a token) the reset is rejected
    assert client.post("/api/auth/reset-password", json={
        "email": "nina@library.com", "otp": "000000", "new_password": "newpass99",
        "confirm_password": "newpass99"}).status_code == 400

    response = client.post("/api/auth/forgot-password", json={"email": "nina@library.com"})
    otp = response.json()["data"]["dev_otp"]
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
    client, _, _ = api
    assert client.get("/student/dashboard.html").status_code == 302
    assert client.get("/admin/dashboard.html").status_code == 302
    assert client.get("/admin/librarian-dashboard.html").status_code == 302

    login_as(client, "nina@library.com", "passw0rd1")
    assert client.get("/student/dashboard.html").status_code == 200
    assert client.get("/student/fines.html").status_code == 200
    assert client.get("/admin/dashboard.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.get("/admin/fines.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.get("/admin/librarian-dashboard.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.get("/admin/users.html").headers["Location"].endswith("/student/dashboard.html")
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/student/dashboard.html").headers["Location"].endswith("/login.html")
    assert client.get("/api/dashboard").status_code == 401

    login_as(client, "ray@library.com", "passw0rd1")
    assert client.get("/admin/dashboard.html").status_code == 200
    assert client.get("/admin/librarian-dashboard.html").status_code == 200
    assert client.get("/admin/fines.html").status_code == 200
    assert client.get("/admin/users.html").headers["Location"].endswith("/admin/dashboard.html")

    login_as(client, "admin@library.com", "admin123")
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
        "confirm_password": "passw0rd2"}).status_code == 403
    assert client.put("/api/profile/password", json={
        "current_password": "passw0rd1", "new_password": "passw0rd2",
        "confirm_password": "passw0rd2"}).status_code == 200
    login_as(client, "nina@library.com", "passw0rd2")

    prefs = client.put("/api/profile/preferences", json={"due_reminders": False})
    assert prefs.json()["data"]["preferences"]["due_reminders"] is False


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
