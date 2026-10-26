"""Smart Library Management System — Flask application.

Serves two things from one process:
  * a JSON REST API under /api/*  (session-authenticated, role-authorized)
  * the static frontend in ./frontend (plain HTML/CSS/JS, no build step)

Run:  python app.py   (then open https://127.0.0.1:5000)
"""
import os
import secrets
from datetime import timedelta

from flask import (
    Flask,
    get_flashed_messages,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)

from config.database import DatabaseConnection
from controllers.app_controller import LibraryController
from routes.auth_routes import auth_bp
from routes.book_routes import book_bp
from routes.borrow_routes import borrow_bp
from routes.dashboard_routes import dashboard_bp
from routes.fine_routes import fine_bp
from routes.notification_routes import notification_bp
from routes.profile_routes import profile_bp
from routes.report_routes import report_bp
from routes.reservation_routes import reservation_bp
from routes.settings_routes import settings_bp
from routes.student_routes import student_bp
from routes.user_routes import activity_bp, user_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_env_file():
    """Tiny .env loader (no extra dependency). Existing environment variables win."""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def seed_default_admin(controller: LibraryController):
    """Idempotently ensure one admin account exists.

    DEVELOPMENT ONLY default credentials — override with ADMIN_EMAIL / ADMIN_PASSWORD
    environment variables (see .env.example) before any real deployment.
    """
    admins = controller.user_dao.get_users_by_role("admin")
    if admins:
        return
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if os.environ.get("FLASK_DEBUG", "1") != "1" and (not admin_email or not admin_password):
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD before starting without debug mode.")
    admin_email = admin_email or "admin@library.com"
    admin_password = admin_password or "admin123"
    controller.register(
        "ADMIN001", "System Administrator", admin_email, admin_password,
        role="admin", department="IT",
    )


def create_app():
    load_env_file()

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if os.environ.get("FLASK_DEBUG", "1") != "1":
            raise RuntimeError("Set SECRET_KEY before starting without debug mode.")
        secret_key = secrets.token_hex(32)

    frontend_dir = os.path.join(BASE_DIR, "frontend")
    app = Flask(
        __name__,
        template_folder=frontend_dir,
        static_folder=frontend_dir,
        static_url_path="/",
    )
    app.config.update(
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    app.permanent_session_lifetime = timedelta(days=int(os.environ.get("REMEMBER_ME_DAYS", "30")))

    controller = LibraryController()
    app.extensions["library_controller"] = controller

    for blueprint in (auth_bp, book_bp, student_bp, borrow_bp, fine_bp, reservation_bp,
                      notification_bp, report_bp, dashboard_bp, profile_bp, user_bp,
                      activity_bp, settings_bp):
        app.register_blueprint(blueprint)

    def render_dashboard(initial_view="dash"):
        user = session.get("user")
        if not user:
            return redirect("/login")

        controller = app.extensions["library_controller"]
        books = controller.filter_books()
        transactions = controller.list_transactions(
            student_id=user["user_id"] if user["role"] == "student" else None
        )
        journal_mode = DatabaseConnection().get_connection().execute(
            "PRAGMA journal_mode"
        ).fetchone()[0]
        backend_status = (
            "Backend Connected: Live SQLite WAL"
            if str(journal_mode).lower() == "wal"
            else f"Backend Connected: Live SQLite {str(journal_mode).upper()}"
        )
        template = "student/dashboard.html" if user["role"] == "student" else "admin/dashboard.html"
        return render_template(
            template,
            user=user,
            books=books,
            transactions=transactions,
            backend_status=backend_status,
            initial_view=initial_view,
        )

    # --- Page routes ---
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    def _dashboard_page_response(page_name, allowed_role=None):
        user = session.get("user")
        if not user:
            return redirect("/login.html")
        if allowed_role and user.get("role") != allowed_role:
            if user.get("role") == "student":
                return redirect("/student/dashboard.html")
            return redirect("/admin/dashboard.html")
        destinations = {
            "student-dashboard.html": "/student/dashboard.html",
            "librarian-dashboard.html": "/admin/dashboard.html",
            "admin-dashboard.html": "/admin/dashboard.html",
        }
        return redirect(destinations[page_name])

    ADMIN_ONLY_PAGES = ("users.html", "activity-logs.html", "system-settings.html")

    def _role_page_response(area, page_name, allowed_roles):
        if not page_name.endswith(".html"):
            return redirect("/")
        user = session.get("user")
        if not user:
            return redirect("/login.html")
        if area == "admin" and page_name in ADMIN_ONLY_PAGES and user.get("role") != "admin":
            destination = "/student/dashboard.html" if user.get("role") == "student" else "/admin/dashboard.html"
            return redirect(destination)
        if area == "admin" and page_name == "librarian-dashboard.html":
            if user.get("role") == "admin":
                return redirect("/admin/dashboard.html")
            if user.get("role") == "librarian":
                return render_dashboard()
            return redirect("/student/dashboard.html")
        if user.get("role") not in allowed_roles:
            destination = "/student/dashboard.html" if user.get("role") == "student" else "/admin/dashboard.html"
            return redirect(destination)
        if page_name == "dashboard.html":
            return render_dashboard()
        return send_from_directory(app.static_folder, f"{area}/{page_name}")

    @app.get("/student/<path:page_name>")
    def student_page(page_name):
        return _role_page_response("student", page_name, ("student",))

    @app.get("/admin/<path:page_name>")
    def staff_page(page_name):
        return _role_page_response("admin", page_name, ("admin", "librarian"))

    @app.get("/student-dashboard.html")
    def student_dashboard_page():
        return _dashboard_page_response("student-dashboard.html", "student")

    @app.get("/librarian-dashboard.html")
    def librarian_dashboard_page():
        return _dashboard_page_response("librarian-dashboard.html", "librarian")

    @app.get("/admin-dashboard.html")
    def admin_dashboard_page():
        return _dashboard_page_response("admin-dashboard.html", "admin")

    @app.get("/login.html")
    @app.get("/login")
    def login_page():
        if session.get("user"):
            role = session["user"].get("role")
            return redirect({"student": "/student/dashboard.html", "librarian": "/admin/dashboard.html", "admin": "/admin/dashboard.html"}.get(role, "/login.html"))
        return render_template("login.html", flash_messages=get_flashed_messages(with_categories=True))

    @app.get("/signup.html")
    @app.get("/register")
    def signup_page():
        return render_template("signup.html", flash_messages=get_flashed_messages(with_categories=True))

    @app.get("/forgot-password.html")
    @app.get("/forgot_password")
    def forgot_page():
        return render_template("forgot-password.html", flash_messages=get_flashed_messages(with_categories=True))

    @app.get("/otp.html")
    def otp_page():
        return render_template("otp.html")

    @app.get("/reset-password.html")
    @app.get("/reset_password")
    def reset_page():
        return render_template("reset-password.html", flash_messages=get_flashed_messages(with_categories=True))

    @app.get("/dashboard")
    def dashboard_page():
        return render_dashboard()

    @app.get("/books")
    def books_page():
        user = session.get("user")
        initial_view = "browse" if user and user["role"] == "student" else "books"
        return render_dashboard(initial_view)

    @app.post("/login")
    def login_submit():
        return app.view_functions["auth.login"]()

    @app.post("/register")
    def register_submit():
        return app.view_functions["auth.register"]()

    @app.post("/forgot_password")
    def forgot_password_submit():
        return app.view_functions["auth.forgot_password"]()

    @app.post("/reset_password")
    def reset_password_submit():
        return app.view_functions["auth.reset_password"]()

    @app.post("/books")
    def add_book_submit():
        return app.view_functions["books.add_book"]()

    @app.post("/issue_book")
    def issue_book_submit():
        return app.view_functions["borrow.issue_book"]()

    @app.post("/return_book")
    def return_book_submit():
        data = request.get_json(silent=True) or request.form
        transaction_id = data.get("transaction_id")
        try:
            transaction_id = int(transaction_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "'transaction_id' must be a whole number."}, 400
        return app.view_functions["borrow.return_book"](transaction_id)

    # --- Resolve the session user once per request; routes/decorators read it ---
    @app.before_request
    def resolve_session_user():
        request.environ["library_user"] = session.get("user")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Cache-Control", "no-store" if request.path.startswith("/api") else "no-cache")
        return response

    # --- Errors: JSON for API calls, friendly redirect for pages ---
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api"):
            return {"success": False, "message": "API endpoint not found."}, 404
        return redirect("/")

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith("/api"):
            return {"success": False, "message": "Method not allowed for this endpoint."}, 405
        return redirect("/")

    @app.errorhandler(500)
    def server_error(error):
        # Never leak Python stack traces to the client
        if request.path.startswith("/api"):
            app.logger.exception("Unhandled server error")
            return {"success": False, "message": "Something went wrong on our side. Please try again."}, 500
        return redirect("/")

    seed_default_admin(controller)
    return app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"Smart Library running at https://{host}:{port}")
    app.run(host=host, port=port, debug=debug, ssl_context="adhoc")
