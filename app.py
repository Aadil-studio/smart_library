"""Smart Library Management System — Flask application.

Serves two things from one process:
  * a JSON REST API under /api/*  (session-authenticated, role-authorized)
  * the static frontend in ./frontend (plain HTML/CSS/JS, no build step)

Run:  python app.py   (then open http://127.0.0.1:5000)
"""
import os
from datetime import timedelta

from flask import Flask, redirect, request, send_from_directory, session

from config.database import DatabaseConnection
from controllers.app_controller import LibraryController
from routes.auth_routes import auth_bp
from routes.book_routes import book_bp
from routes.borrow_routes import borrow_bp
from routes.dashboard_routes import dashboard_bp
from routes.notification_routes import notification_bp
from routes.profile_routes import profile_bp
from routes.report_routes import report_bp
from routes.reservation_routes import reservation_bp
from routes.student_routes import student_bp

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
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@library.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    controller.register(
        "ADMIN001", "System Administrator", admin_email, admin_password,
        role="admin", department="IT",
    )


def create_app():
    load_env_file()

    app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "frontend"), static_url_path="/")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-in-.env"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    app.permanent_session_lifetime = timedelta(days=int(os.environ.get("REMEMBER_ME_DAYS", "30")))

    controller = LibraryController()
    app.extensions["library_controller"] = controller

    for blueprint in (auth_bp, book_bp, student_bp, borrow_bp, reservation_bp,
                      notification_bp, report_bp, dashboard_bp, profile_bp):
        app.register_blueprint(blueprint)

    # --- Page routes (static frontend) ---
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

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
    print(f"Smart Library running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
