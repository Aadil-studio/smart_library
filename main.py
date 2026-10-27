"""Smart Library Management System — FastAPI application (single entry point).

Serves two things from one process:
  * a JSON REST API under /api/*  (session-authenticated, role-authorized)
  * the static frontend in ./frontend (plain HTML/CSS/JS, no build step)

Run over HTTPS with:

    uvicorn main:app --reload --ssl-certfile localhost-cert.pem --ssl-keyfile localhost-key.pem

or simply:

    python main.py

A self-signed development certificate (localhost-cert.pem / localhost-key.pem) is
generated automatically on first start — accept your browser's local-certificate
warning. Session cookies are marked Secure.
"""
import os
import re
import secrets

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from config.database import DatabaseConnection
from controllers.app_controller import LibraryController
from routes.auth_routes import router as auth_router
from routes.book_routes import router as book_router
from routes.borrow_routes import router as borrow_router
from routes.dashboard_routes import router as dashboard_router
from routes.fine_routes import fee_router, router as fine_router
from routes.notification_routes import router as notification_router
from routes.profile_routes import router as profile_router
from routes.report_routes import router as report_router
from routes.reservation_routes import router as reservation_router
from routes.settings_routes import router as settings_router
from routes.student_routes import router as student_router
from routes.user_routes import activity_router, router as user_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAFE_PAGE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
CERT_FILE = os.path.join(BASE_DIR, "localhost-cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "localhost-key.pem")


def ensure_https_certificate():
    """Generate a self-signed certificate for local HTTPS (idempotent).

    Runtime artifacts, like library.db — never commit the private key.
    """
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    import datetime
    import ipaddress

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    with open(KEY_FILE, "wb") as handle:
        handle.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(CERT_FILE, "wb") as handle:
        handle.write(cert.public_bytes(serialization.Encoding.PEM))
    print("[INFO] Self-signed HTTPS certificate generated: localhost-cert.pem / localhost-key.pem")


# Generate the certificate BEFORE create_app() so the first start over HTTPS works,
# including `uvicorn main:app --reload --ssl-certfile ... --ssl-keyfile ...`.
ensure_https_certificate()


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


def debug_enabled() -> bool:
    return os.environ.get("APP_DEBUG", os.environ.get("FLASK_DEBUG", "1")) == "1"


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
    if not debug_enabled() and (not admin_email or not admin_password):
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD before starting without debug mode.")
    admin_email = admin_email or "admin@library.com"
    admin_password = admin_password or "admin123"
    controller.register(
        "ADMIN001", "System Administrator", admin_email, admin_password,
        role="admin", department="IT",
    )


def create_app() -> FastAPI:
    load_env_file()

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if not debug_enabled():
            raise RuntimeError("Set SECRET_KEY before starting without debug mode.")
        secret_key = secrets.token_hex(32)

    frontend_dir = os.path.join(BASE_DIR, "frontend")
    app = FastAPI(title="Smart Library API", docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json")
    app.state.secret_key = secret_key
    app.state.templates = Jinja2Templates(directory=frontend_dir)
    controller = LibraryController()
    app.state.library_controller = controller

    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="library_session",
        max_age=86400 * int(os.environ.get("REMEMBER_ME_DAYS", "30")),
        same_site="lax",
        # SESSION_COOKIE_SECURE=1 is set above because the server runs HTTPS
        https_only=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    )

    for router in (auth_router, book_router, student_router, borrow_router, fine_router,
                   fee_router, reservation_router, notification_router, report_router,
                   dashboard_router, profile_router, user_router, activity_router, settings_router):
        app.include_router(router)

    # --- Errors: JSON for API calls, friendly redirect for pages ---
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api"):
            detail = exc.detail
            message = detail.get("message") if isinstance(detail, dict) else detail
            return JSONResponse(status_code=exc.status_code,
                                content={"success": False, "message": str(message or "Request failed.")})
        return RedirectResponse("/", status_code=302)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=400,
                                content={"success": False, "message": "Invalid request data."})
        return RedirectResponse("/", status_code=302)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Never leak Python stack traces to the client
        import logging
        logging.getLogger("uvicorn.error").exception("Unhandled server error")
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=500,
                                content={"success": False,
                                         "message": "Something went wrong on our side. Please try again."})
        return RedirectResponse("/", status_code=302)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Cache-Control", "no-store" if request.url.path.startswith("/api") else "no-cache")
        return response

    templates = app.state.templates

    def render_dashboard(request: Request, initial_view="dash"):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login", status_code=302)

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
        return templates.TemplateResponse(
            request=request,
            name=template,
            context={
                "user": user,
                "books": books,
                "transactions": transactions,
                "backend_status": backend_status,
                "initial_view": initial_view,
            },
        )

    # --- Page routes ---
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    def _dashboard_page_response(request: Request, page_name, allowed_role=None):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login.html", status_code=302)
        if allowed_role and user.get("role") != allowed_role:
            if user.get("role") == "student":
                return RedirectResponse("/student/dashboard.html", status_code=302)
            return RedirectResponse("/admin/dashboard.html", status_code=302)
        destinations = {
            "student-dashboard.html": "/student/dashboard.html",
            "librarian-dashboard.html": "/admin/dashboard.html",
            "admin-dashboard.html": "/admin/dashboard.html",
        }
        return RedirectResponse(destinations[page_name], status_code=302)

    ADMIN_ONLY_PAGES = ("users.html", "activity-logs.html", "system-settings.html")

    def _role_page_response(request: Request, area, page_name, allowed_roles):
        if not page_name.endswith(".html") or not SAFE_PAGE_NAME.match(page_name):
            return RedirectResponse("/", status_code=302)
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login.html", status_code=302)
        if area == "admin" and page_name in ADMIN_ONLY_PAGES and user.get("role") != "admin":
            destination = "/student/dashboard.html" if user.get("role") == "student" else "/admin/dashboard.html"
            return RedirectResponse(destination, status_code=302)
        if area == "admin" and page_name == "librarian-dashboard.html":
            if user.get("role") == "admin":
                return RedirectResponse("/admin/dashboard.html", status_code=302)
            if user.get("role") == "librarian":
                return render_dashboard(request)
            return RedirectResponse("/student/dashboard.html", status_code=302)
        if user.get("role") not in allowed_roles:
            destination = "/student/dashboard.html" if user.get("role") == "student" else "/admin/dashboard.html"
            return RedirectResponse(destination, status_code=302)
        if page_name == "dashboard.html":
            return render_dashboard(request)
        return FileResponse(os.path.join(frontend_dir, area, page_name))

    @app.get("/student/{page_name}")
    async def student_page(request: Request, page_name: str):
        return _role_page_response(request, "student", page_name, ("student",))

    @app.get("/admin/{page_name}")
    async def staff_page(request: Request, page_name: str):
        return _role_page_response(request, "admin", page_name, ("admin", "librarian"))

    @app.get("/student-dashboard.html")
    async def student_dashboard_page(request: Request):
        return _dashboard_page_response(request, "student-dashboard.html", "student")

    @app.get("/librarian-dashboard.html")
    async def librarian_dashboard_page(request: Request):
        return _dashboard_page_response(request, "librarian-dashboard.html", "librarian")

    @app.get("/admin-dashboard.html")
    async def admin_dashboard_page(request: Request):
        return _dashboard_page_response(request, "admin-dashboard.html", "admin")

    @app.get("/login.html")
    @app.get("/login")
    async def login_page(request: Request):
        if request.session.get("user"):
            role = request.session["user"].get("role")
            return RedirectResponse(
                {"student": "/student/dashboard.html", "librarian": "/admin/dashboard.html",
                 "admin": "/admin/dashboard.html"}.get(role, "/login.html"), status_code=302)
        return templates.TemplateResponse(request=request, name="login.html",
                                          context={"flash_messages": []})

    @app.get("/signup.html")
    @app.get("/register")
    async def signup_page(request: Request):
        return templates.TemplateResponse(request=request, name="signup.html",
                                          context={"flash_messages": []})

    @app.get("/forgot-password.html")
    @app.get("/forgot_password")
    async def forgot_page(request: Request):
        return templates.TemplateResponse(request=request, name="forgot-password.html",
                                          context={"flash_messages": []})

    @app.get("/otp.html")
    async def otp_page(request: Request):
        return templates.TemplateResponse(request=request, name="otp.html", context={})

    @app.get("/reset-password.html")
    @app.get("/reset_password")
    async def reset_page(request: Request):
        return templates.TemplateResponse(request=request, name="reset-password.html",
                                          context={"flash_messages": []})

    @app.get("/dashboard")
    async def dashboard_page(request: Request):
        return render_dashboard(request)

    @app.get("/books")
    async def books_page(request: Request):
        user = request.session.get("user")
        initial_view = "browse" if user and user["role"] == "student" else "books"
        return render_dashboard(request, initial_view)

    # Static frontend last, so API and page routes always win
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    seed_default_admin(controller)
    return app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload_requested = os.environ.get("RELOAD", "1") == "1"
    # python main.py always serves HTTPS, so the session cookie is marked Secure.
    os.environ.setdefault("SESSION_COOKIE_SECURE", "1")
    print(f"Smart Library running at https://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=reload_requested,
                ssl_certfile=CERT_FILE, ssl_keyfile=KEY_FILE)
