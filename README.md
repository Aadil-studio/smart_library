# Smart Library Management System

A complete, production-style library management system for a university/library built with
**Python (Flask)**, **SQLite**, and a modern **HTML5/CSS3/JavaScript** frontend — no frontend
build step required. The frontend and backend communicate through a real REST API with
session authentication and backend-enforced role authorization.

## 1. Project Overview

Smart Library manages the full circulation workflow of a campus library:

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
| Authentication | Register, login (student ID *or* email), logout, session cookies, Remember Me, show/hide password |
| Password security | Werkzeug PBKDF2/scrypt hashing; legacy SHA-256 hashes are upgraded automatically on login |
| Forgot password | Email → OTP (hashed, 10-minute expiry, single use) → verify → reset. Dev mode shows the code; SMTP supported |
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

- **Backend:** Python 3, Flask 3, SQLite 3 (WAL mode), Werkzeug security helpers
- **Frontend:** HTML5, CSS3, vanilla JavaScript, Font Awesome (CDN)
- **Testing:** PyTest (unit + end-to-end API tests)
- **No other runtime dependencies** — see `requirements.txt`

## 4. Folder Structure

```
smart_library/
├── app.py                     # Flask app: /api/* REST API + serves ./frontend
├── main.py                    # Original CLI demo (layered architecture demo)
├── seed_demo.py               # Optional development seed data (DEVELOPMENT ONLY)
├── generate_pdf.py            # Live HTML report -> report.html (print to PDF)
├── requirements.txt
├── .env.example               # Environment variable template
├── library.db                 # SQLite database (created/migrated automatically)
│
├── config/database.py         # Singleton SQLite connection + schema (WAL mode)
├── controllers/app_controller.py   # Business facade used by all routes
├── models/models.py           # Original entity classes
├── dao/                       # Data access layer
│   ├── user_dao.py            #   users, auth, OTPs, preferences, activity log
│   ├── book_dao.py            #   books CRUD + search/filters
│   ├── borrow_dao.py          #   transactions: issue/return/fines/overdue
│   ├── reservation_dao.py     #   reservations
│   └── notification_dao.py    #   notifications (+ de-duplication)
├── services/
│   ├── fine_strategy.py       # Strategy pattern fine engine (student/faculty)
│   ├── borrow_service.py      # Loan workflows (original service)
│   ├── report_service.py      # Aggregated statistics
│   └── email_service.py       # SMTP OTP delivery (optional)
├── routes/                    # Flask blueprints = REST API
│   ├── __init__.py            #   role decorators + validation helpers
│   ├── auth_routes.py  book_routes.py  student_routes.py  borrow_routes.py
│   ├── reservation_routes.py  notification_routes.py
│   └── report_routes.py  dashboard_routes.py  profile_routes.py
├── frontend/                  # Static frontend (served by Flask)
│   ├── index.html  login.html  signup.html  forgot-password.html  otp.html  reset-password.html
│   ├── student/               # dashboard, books, borrowed-books, reservations,
│   │                          # history, notifications, profile, settings
│   ├── admin/                 # dashboard, books, add-book, edit-book, students,
│   │                          # borrow-return, reservations, reports, notifications, settings
│   ├── css/style.css          # Design system (glassmorphism dark theme)
│   └── js/                    # api.js, common.js (shared shell), auth.js,
│                              # student.js, admin.js, books.js, borrow.js,
│                              # reservations.js, notifications.js
└── tests/                     # PyTest suite (unit + end-to-end API)
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
| `SECRET_KEY` | Flask session signing key — set a long random string |
| `HOST` / `PORT` / `FLASK_DEBUG` | Server options (defaults: 127.0.0.1:5000, debug on) |
| `REMEMBER_ME_DAYS` | "Remember me" session lifetime |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | First admin account, created only if no admin exists (**DEVELOPMENT ONLY** defaults `admin@library.com` / `admin123`) |
| `OTP_DEV_MODE` | `1` returns password-reset OTPs in the API response (no SMTP needed). Set `0` in production |
| `SMTP_HOST`/`SMTP_PORT`/`SMTP_FROM`/`SMTP_USER`/`SMTP_PASS` | Email real OTP codes instead of dev mode |
| `LIBRARY_DB_PATH` | Override the database file location |

Never commit a real `.env` (it is already in `.gitignore`).

## 8. Running the Application

```bat
.venv\Scripts\activate
python seed_demo.py
python seed_northstar.py
python app.py
```

The development server runs over HTTPS with a temporary ad-hoc certificate. Open
**https://127.0.0.1:5000** and accept the browser's local-certificate warning — the backend
and frontend run in this single process, so there is no separate frontend server to start.
Session cookies are marked `Secure`; use the HTTPS URL for sign-in and other authenticated
pages.

## 9. Demo Accounts

Created by `seed_demo.py` (or the first admin automatically on first run).
**All demo passwords are DEVELOPMENT ONLY — change them for anything real** (Profile →
Settings → Change password, or the `ADMIN_EMAIL`/`ADMIN_PASSWORD` variables).

| Role | Email | Student/Role ID | Password |
| --- | --- | --- | --- |
| Admin | `admin@library.com` | `ADMIN001` | `admin123` |
| Student | `student@smartlibrary.local` | `STU-1001` | `Student@123` |
| Student | `sara.khan@smartlibrary.local` | `STU-1002` | `Student@123` |
| Librarian | `librarian@smartlibrary.local` | `LIB-2001` | `Librarian@123` |

You can sign in with **either** the email or the Student/Role ID.
The Northstar sign-in shortcuts prefill the seeded account IDs; enter the password
shown above. The administrator defaults to `admin@library.com` / `admin123` when the
app creates the first admin account.

## 10. API Overview

All endpoints return JSON: `{ "success": true|false, "message": "...", "data": { ... } }`.
Authentication uses the session cookie; roles are enforced server-side.

### Auth
| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | public | Create a student account (validates email, unique ID/email, password policy) |
| POST | `/api/auth/login` | public | Login with email **or** student ID (`remember` extends the session) |
| POST | `/api/auth/logout` | auth | Destroy the session |
| GET | `/api/auth/me` | any | Current session user |
| POST | `/api/auth/forgot-password` | public | Generate a hashed, expiring OTP (dev mode returns `data.dev_otp`) |
| POST | `/api/auth/verify-otp` | public | Verify the code |
| POST | `/api/auth/reset-password` | public | Set a new password using the code |

### Books
| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/books?q=&category=&availability=&author=` | any signed-in user |
| GET | `/api/books/<id>` | any signed-in user |
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

1. `frontend/js/api.js` wraps `fetch` for every request (`credentials: 'same-origin'`),
   normalizes errors, and redirects to the login page on session expiry.
2. `frontend/js/common.js` guards each page (`requireAuth`) by calling `/api/auth/me`,
   then renders the shared sidebar/topbar (role-aware navigation, unread badge, search).
3. Page modules (`books.js`, `borrow.js`, `reservations.js`, `notifications.js`,
   `student.js`, `admin.js`) fetch live data from the API and render tables/cards;
   every form posts to a real endpoint. There is no hard-coded demo data.
4. Access control is server-side: a student calling a staff API receives `403`, and an
   unauthenticated call receives `401` — changing frontend URLs grants nothing.

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
| `Cannot reach the library server` toast | The Flask process isn't running — start it with `python app.py` |
| Redirected to login immediately | Your session expired; sign in again |
| `database is locked` | The app already enables WAL + busy timeout; close other processes using `library.db` |
| OTP email not arriving | SMTP isn't configured; with `OTP_DEV_MODE=1` the code is shown on the OTP page instead |
| Forgot the admin password | Delete the admin row (or the database) and restart — the app re-seeds from `ADMIN_EMAIL`/`ADMIN_PASSWORD` |
| Port 5000 already in use | Change `PORT` in `.env` and restart |
| Tests fail on first run | Ensure the venv is activated and `pip install -r requirements.txt` succeeded |

## 15. Security Notes

- Passwords: PBKDF2/scrypt hashes (Werkzeug); plain-text or unsalted hashes never stored
  (existing legacy rows are transparently upgraded at login).
- OTPs: only SHA-256 hashes are stored, expiring after 10 minutes, single-use.
- Parameterized SQL everywhere (SQLite) — no string-built queries.
- Password hashes and OTP codes are stripped from every API response.
- Errors return clean JSON messages; stack traces are logged server-side only.
- Secrets live in `.env` (git-ignored); `.env.example` documents every variable.
