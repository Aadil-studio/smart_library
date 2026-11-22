# Northstar Library Management System

A complete, production-style library management system for a university/library built with
**Python (FastAPI)**, **SQLite**, and a modern **HTML5/CSS3/JavaScript** frontend — no frontend
build step required. The frontend and backend communicate through a real REST API with
session authentication and backend-enforced role authorization.

## 1. Project Overview

Northstar Library manages the full circulation workflow of a campus library:

- **Students** browse and search the catalog, reserve books, track loans, fines, and
  notifications, and manage their profile and preferences.
- **Library staff (admin / librarian)** manage the catalog, students, issue and return
  books, approve reservations, send announcements, and view printable reports.

The backend follows a layered architecture (routes → controller → services/DAO → database)
with the original project's design patterns preserved: a **Singleton** database connection
and a **Strategy** pattern fine engine.

## 2. Features

| Area | What's included |
| --- | --- |
| Authentication | Register, login (student ID *or* email), logout, secure session cookies, show/hide password |
| Password security | Werkzeug PBKDF2/scrypt hashing; legacy SHA-256 hashes are upgraded automatically on login |
| Forgot password | Email → OTP (hashed, 10-minute expiry, single use) → verify → reset. SMTP delivery, resend cooldowns, and attempt limits |
| Roles | `student`, `librarian`, `admin` — enforced on the **backend** for every API call |
| Books | Full CRUD, search (title/author/ISBN/category/publisher), category/availability filters, shelf/rack, description, safe copy accounting |
| Borrow / Return | Issue with due dates, duplicate-loan & zero-copy protection, automatic availability updates, overdue detection, fine calculation (Strategy pattern) |
| Reservations | Students place requests; staff approve / decline / fulfil; issuing an approved book auto-fulfils it |
| Notifications | Registration, issue, return, reservation updates, due-soon and overdue alerts (de-duplicated), staff announcements; unread badge |
| Students (admin) | List/search/filter, view profile + history + reservations, activate/deactivate |
| Profile / Settings | Edit profile, change password, notification preferences |
| Reports | Live summary, top borrowed books, category distribution, overdue list; printable report + `generate_pdf.py` HTML report |
| UI | Glassmorphism dark theme, responsive sidebar/topbar, loading states, empty states, toasts, mobile-friendly tables |

## 3. Technologies

- **Backend:** Python 3, FastAPI, SQLite 3 (WAL mode), Werkzeug security helpers
- **Frontend:** HTML5, CSS3, vanilla JavaScript, Font Awesome (CDN)
- **Testing:** PyTest (unit + end-to-end API tests)
- **No other runtime dependencies** — see `requirements.txt`

## 4. Folder Structure

```
smart_library/
├── main.py                    # FastAPI app: /api/* REST API + serves ./frontend
├── seed_demo.py               # Optional development-only sample data
├── seed_northstar.py          # Optional Northstar catalog seed
├── requirements.txt
├── .env.example               # Safe environment-variable template
├── config/                    # SQLite schema and connection
├── controllers/               # Application/business facade
├── dao/                       # Database access and domain persistence
├── routes/                    # FastAPI routers and API authorization
├── services/                  # Email, fines, circulation, and reports
├── frontend/                  # Static HTML, CSS, and JavaScript
│   ├── admin/                  # Admin and librarian pages
│   ├── student/                # Student pages
│   ├── css/
│   └── js/
└── tests/                     # PyTest unit and API regression suite
```

## 5. Installation (Windows)

```bat
cd path\to\smart_library

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

## 6. Database Setup

No manual steps. On first run the app creates/opens `library.db` and applies an **additive**
schema migration (existing tables and data are preserved). Tables: `users`, `books`,
`transactions`, `reservations`, `fines`, `notifications`, `activity_logs`,
`password_reset_otps`, plus `categories`/`authors`.

Optional demo accounts (sample students, librarian, and 10 starter books):

```bat
.venv\Scripts\python.exe seed_demo.py
```

Add the complete 62-title Northstar catalog (safe to run repeatedly):

```bat
.venv\Scripts\python.exe seed_northstar.py
```

## 7. Environment Variables

Copy the template and edit it:

```bat
copy .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Random session-signing key; required when debug mode is off |
| `HOST` / `PORT` / `APP_DEBUG` | Server options (defaults: 127.0.0.1:8000, debug off) |
| `SESSION_COOKIE_SECURE` | Defaults to `1`; keep enabled when serving over HTTPS |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | First admin account, used only when the database has no admin |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_FROM` | SMTP server, port, and sender address for password-reset codes |
| `SMTP_USER` / `SMTP_PASS` | SMTP credentials when required by the provider |
| `APP_BASE_URL` | Public HTTPS URL used to build password-reset email links |
| `LIBRARY_DB_PATH` | Override the database file location |

Set `SECRET_KEY` to a new random value. Configure `ADMIN_EMAIL` and `ADMIN_PASSWORD`
before the first start of an empty database. Never commit a real `.env`.
For Gmail, set `SMTP_FROM` and `SMTP_USER` to the authorized Gmail sender and use a
Google App Password as `SMTP_PASS`. The admin-only `/api/auth/email-config` endpoint
reports which settings are detected and whether the active `.env` exists, without
returning any values.

## 8. Running the Application

```bat
.venv\Scripts\activate
python main.py
```

The app serves the frontend and API together over HTTPS at **https://127.0.0.1:8000**.
It generates a self-signed local certificate on first start; accept the browser's
development-certificate warning. Session cookies are `Secure` by default.

## 9. Demo Accounts

`seed_demo.py` creates development-only sample accounts with well-known test credentials.
Do not run it against a production database. Configure `ADMIN_EMAIL` and `ADMIN_PASSWORD`
to create an administrator when starting with an empty database; no default production
administrator credentials are provided.

## 10. API Overview

All endpoints return JSON: `{ "success": true|false, "message": "...", "data": { ... } }`.
Authentication uses the session cookie; roles are enforced server-side.

### Auth
| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | public | Create a student account (validates email, unique ID/email, password policy) |
| POST | `/api/auth/login` | public | Login with email **or** student ID |
| POST | `/api/auth/logout` | auth | Destroy the session |
| GET | `/api/auth/me` | any | Current session user |
| POST | `/api/auth/forgot-password` | public | Generate a hashed, expiring OTP and send it by email |
| POST | `/api/auth/resend-otp` | public | Send a new code, subject to cooldown and rate limits |
| POST | `/api/auth/verify-otp` | public | Verify the code once and issue a short-lived reset token |
| POST | `/api/auth/reset-password` | public | Set a new password using the short-lived verified reset token |
| GET | `/api/auth/email-config` | admin | Inspect SMTP configuration presence and source without exposing values |

### Books
| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/books?q=&category=&availability=&author=` | any signed-in user |
| GET | `/api/books/<id>` | any signed-in user |
| GET | `/api/books/cover-lookup?book_id=<id>` | any signed-in user (checks Google Books/Open Library ISBN-first, verifies title/author and image data, saves missing covers, and replaces a saved URL only after it fails) |
| POST | `/api/books` | staff |
| PUT | `/api/books/<id>` | staff |
| DELETE | `/api/books/<id>` | admin (blocked while copies are on loan) |

### Students
| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/students?q=&status=` | admin |
| GET | `/api/students/<user_id>` (profile + loans + reservations) | admin |
| PUT | `/api/students/<user_id>/status` | admin |
| GET | `/api/students/<user_id>/history` | self or admin |

### Borrow / Return
| Method | Endpoint | Access |
| --- | --- | --- |
| POST | `/api/borrow` `{student_id, book_id (ID or ISBN), days}` | staff |
| POST | `/api/borrow/<txn_id>/return` | staff |
| GET | `/api/borrow?scope=mine|all&status=` | signed-in (scope=all: staff) |
| GET | `/api/borrow/fines` | signed-in |

### Reservations
| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/reservations?scope=mine|all&status=` | signed-in (scope=all: staff) |
| POST | `/api/reservations` `{book_id}` | student |
| PUT | `/api/reservations/<id>` `{action: approve\|reject\|fulfil\|cancel}` | staff (cancel: owner) |

### Notifications
| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/notifications?unread=1` | signed-in |
| GET | `/api/notifications/unread-count` | signed-in |
| PUT | `/api/notifications/<id>/read` · `/read-all` | signed-in |
| POST | `/api/notifications/broadcast` | staff |

### Dashboards, reports, profile
| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/dashboard` | signed-in (role-aware payload) |
| GET | `/api/reports/summary` · `/borrowing?days=` · `/top-books` · `/overdue` | staff |
| GET/PUT | `/api/profile` | signed-in |
| PUT | `/api/profile/password` · `/api/profile/preferences` | signed-in |

## 11. How the Frontend Connects to the Backend

1. `frontend/js/northstar.js` drives the shared catalog, student views, navigation, and
   role-aware application interactions through the live API.
2. `frontend/js/admin-dashboard.js` provides distinct admin analytics and librarian
   operations; `frontend/js/book-covers.js` handles verified, lazy-loaded book covers.
3. API routes enforce access control server-side: a student calling a staff API receives
   `403`, and an unauthenticated call receives `401` — changing frontend URLs grants nothing.

## 12. Testing

```bat
.venv\Scripts\activate
python -m pytest tests/ -q
```

Covers: registration & validation, login (incl. legacy SHA-256 hash upgrade), role
authorization (student vs librarian vs admin), book CRUD + search, borrow/return cycle with
copy accounting and duplicate protection, reservation lifecycle, notifications & read state,
overdue sweep with de-duplication, the full OTP reset flow, profile/password/preferences,
dashboards and reports — all against an isolated in-memory database.

## 13. Reports / PDF

- In-app: **Reports** page → *Print / Save as PDF* (print-optimized stylesheet included).
- Standalone: `python generate_pdf.py` writes `report.html` from live data — open it in a
  browser and press `Ctrl+P → Save as PDF`.

## 14. Troubleshooting

| Problem | Fix |
| --- | --- |
| `Cannot reach the library server` toast | Start the FastAPI process with `python main.py` |
| Redirected to login immediately | Your session expired; sign in again |
| `database is locked` | The app already enables WAL + busy timeout; close other processes using `library.db` |
| OTP email not arriving | Sign in as admin and check `/api/auth/email-config`; configure missing SMTP values in the project-root `.env` and restart the server |
| Forgot the admin password | Use the configured password-reset email flow; preserve the database and contact the system administrator if SMTP is unavailable |
| Port 8000 already in use | Change `PORT` in `.env` and restart |
| Tests fail on first run | Ensure the venv is activated and `pip install -r requirements.txt` succeeded |

## 15. Security Notes

- Passwords: PBKDF2/scrypt hashes (Werkzeug); plain-text or unsalted hashes never stored
  (existing legacy rows are transparently upgraded at login).
- OTPs: only SHA-256 hashes are stored, expiring after 10 minutes, single-use.
- Parameterized SQL everywhere (SQLite) — no string-built queries.
- Password hashes and OTP codes are stripped from every API response.
- Errors return clean JSON messages; stack traces are logged server-side only.
- Secrets live in `.env` (git-ignored); `.env.example` documents every variable.
