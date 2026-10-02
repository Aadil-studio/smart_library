"""End-to-end API tests: auth, role authorization, books, borrow/return, reservations,
notifications, overdue sweep, OTP reset, profile — all against an in-memory database."""
import sqlite3

import pytest

from config.database import DatabaseConnection


@pytest.fixture
def api(monkeypatch):
    # Fixed environment so tests never depend on a local .env
    monkeypatch.setenv("ADMIN_EMAIL", "admin@library.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("OTP_DEV_MODE", "1")
    monkeypatch.delenv("SMTP_HOST", raising=False)

    instance = object.__new__(DatabaseConnection)
    instance.connection = sqlite3.connect(":memory:", check_same_thread=False)
    instance.connection.row_factory = sqlite3.Row
    instance.connection.execute("PRAGMA foreign_keys = ON")
    monkeypatch.setattr(DatabaseConnection, "_instance", instance)

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, DEBUG=False)

    controller = flask_app.extensions["library_controller"]
    controller.register("STU999", "Nina Wells", "nina@library.com", "passw0rd1", role="student",
                        department="CS", semester="4")
    controller.register("STAFF01", "Librarian Ray", "ray@library.com", "passw0rd1", role="librarian")

    client = flask_app.test_client()
    yield client, controller, flask_app
    instance.connection.close()


def login_as(client, credential, password):
    response = client.post("/api/auth/login", json={"credential": credential, "password": password})
    assert response.status_code == 200, response.get_json()
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
    assert response.get_json()["data"]["user"]["role"] == "student"

    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"credential": "alex@uni.edu", "password": "wrongpass"}).status_code == 401
    login_as(client, "alex@uni.edu", "secret12")
    me = client.get("/api/auth/me").get_json()
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
    otp = response.get_json()["data"]["dev_otp"]
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


# --- Role authorization ---
def test_students_cannot_reach_admin_apis(api):
    client, _, _ = api
    login_as(client, "nina@library.com", "passw0rd1")
    assert client.get("/api/students").status_code == 403
    assert client.post("/api/books", json={"title": "X", "author": "Y", "isbn": "Z"}).status_code == 403
    assert client.delete("/api/books/1").status_code == 403
    assert client.get("/api/reports/summary").status_code == 403
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": 1}).status_code == 403


def test_librarian_manages_but_only_admin_deletes(api):
    client, _, _ = api
    login_as(client, "ray@library.com", "passw0rd1")
    assert client.get("/api/students").status_code == 403  # user management is admin-only
    created = client.post("/api/books", json={"title": "Refactoring", "author": "M. Fowler",
                                              "isbn": "978-0201485677", "total_copies": 1})
    assert created.status_code == 200
    book_id = created.get_json()["data"]["book"]["id"]
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
    book_id = created.get_json()["data"]["book"]["id"]

    assert client.post("/api/books", json={"title": "No Author", "author": "", "isbn": "x"}).status_code == 400
    assert client.post("/api/books", json={"title": "Dup", "author": "A", "isbn": "978-0132350884"}).status_code == 409
    assert client.post("/api/books", json={"title": "Bad", "author": "A", "isbn": "y", "total_copies": -2}).status_code == 400

    updated = client.put(f"/api/books/{book_id}", json={"total_copies": 1, "shelf_no": "C1"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["book"]["available_copies"] == 1

    listing = client.get("/api/books?q=clean").get_json()["data"]["books"]
    assert [b["id"] for b in listing] == [book_id]
    assert client.get("/api/books?availability=available").status_code == 200
    assert client.get(f"/api/books/{book_id}").status_code == 200
    assert client.get("/api/books/9999").status_code == 404


# --- Borrow / Return ---
def test_borrow_return_cycle_and_guards(api):
    client, controller, flask_app = api
    login_as(client, "ray@library.com", "passw0rd1")
    book_id = add_book(controller, copies=1)

    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 200
    assert controller.get_book(book_id)["available_copies"] == 0
    # no copies left -> rejected; duplicate active loan -> rejected
    assert client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id}).status_code == 409

    loans = client.get("/api/borrow?scope=all").get_json()["data"]["transactions"]
    loan_id = loans[0]["id"]

    # duplicate return protection
    assert client.post(f"/api/borrow/{loan_id}/return").status_code == 200
    assert client.post(f"/api/borrow/{loan_id}/return").status_code == 409
    assert controller.get_book(book_id)["available_copies"] == 1

    # the student sees the return notification on their own session
    student_client = flask_app.test_client()
    login_as(student_client, "nina@library.com", "passw0rd1")
    notes = student_client.get("/api/notifications").get_json()["data"]["notifications"]
    assert any(n.get("type") == "return" for n in notes)


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
    data = client.get("/api/notifications").get_json()["data"]
    assert data["unread"] >= 1
    note_id = data["notifications"][0]["id"]
    assert client.put(f"/api/notifications/{note_id}/read").status_code == 200
    assert client.put("/api/notifications/read-all").status_code == 200
    assert client.get("/api/notifications/unread-count").get_json()["data"]["unread"] == 0


# --- Profile & settings ---
def test_profile_update_change_password_and_preferences(api):
    client, _, _ = api
    login_as(client, "nina@library.com", "passw0rd1")

    updated = client.put("/api/profile", json={"name": "Nina C. Wells", "phone": "0300-1234567"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["profile"]["name"] == "Nina C. Wells"

    assert client.put("/api/profile/password", json={
        "current_password": "wrongpass", "new_password": "passw0rd2",
        "confirm_password": "passw0rd2"}).status_code == 403
    assert client.put("/api/profile/password", json={
        "current_password": "passw0rd1", "new_password": "passw0rd2",
        "confirm_password": "passw0rd2"}).status_code == 200
    login_as(client, "nina@library.com", "passw0rd2")

    prefs = client.put("/api/profile/preferences", json={"due_reminders": False})
    assert prefs.get_json()["data"]["preferences"]["due_reminders"] is False


# --- Dashboards & reports ---
def test_dashboards_and_reports(api):
    client, controller, _ = api
    book_id = add_book(controller)
    login_as(client, "admin@library.com", "admin123")
    client.post("/api/borrow", json={"student_id": "STU999", "book_id": book_id})

    login_as(client, "nina@library.com", "passw0rd1")
    student_view = client.get("/api/dashboard").get_json()["data"]
    assert student_view["role_view"] == "student"
    assert student_view["stats"]["active_loans"] == 1

    login_as(client, "admin@library.com", "admin123")
    admin_view = client.get("/api/dashboard").get_json()["data"]
    assert admin_view["role_view"] == "staff"
    assert admin_view["stats"]["total_books"] >= 1
    assert client.get("/api/reports/summary").status_code == 200
    assert client.get("/api/reports/borrowing?days=7").status_code == 200
    assert client.get("/api/reports/top-books").status_code == 200
    assert client.get("/api/reports/overdue").status_code == 200
