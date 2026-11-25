from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
import time
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from config.database import DatabaseConnection

OTP_MINUTES_VALID = 10
OTP_REQUEST_COOLDOWN_SECONDS = 60
OTP_EMAIL_REQUESTS_PER_HOUR = 5
OTP_IP_REQUESTS_PER_HOUR = 10
OTP_MAX_VERIFICATION_ATTEMPTS = 5


class UserDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    # --- Password hashing (Werkzeug PBKDF2; legacy SHA-256 hashes are upgraded on login) ---
    def _hash_password(self, password: str) -> str:
        return generate_password_hash(password)

    def _verify_password(self, stored_hash: str, password: str) -> bool:
        if not stored_hash:
            return False
        if stored_hash.startswith(("pbkdf2:", "scrypt:")):
            try:
                return check_password_hash(stored_hash, password)
            except ValueError:
                return False
        # Legacy unsalted SHA-256 rows (pre-migration accounts)
        if len(stored_hash) == 64:
            return hashlib.sha256(password.encode()).hexdigest() == stored_hash
        return False

    def _upgrade_legacy_hash(self, user_id: str, password: str):
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE users SET password=? WHERE user_id=?",
            (generate_password_hash(password), user_id),
        )
        self.db.commit()

    @staticmethod
    def _public_user(row) -> dict | None:
        """User dict with the password hash and OTP columns stripped."""
        if not row:
            return None
        user = dict(row)
        user.pop("password", None)
        user.pop("otp", None)
        return user

    # --- Registration & authentication ---
    def register_user(self, user_id, name, email, password, role="student", department="", semester="", phone=""):
        cursor = self.db.cursor()
        try:
            cursor.execute(
                """INSERT INTO users (user_id, name, email, password, role, department, semester, phone)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, name, email, self._hash_password(password), role, department, semester, phone)
            )
            self.db.commit()
        except Exception as e:
            message = str(e).lower()
            if "unique constraint failed: users.email" in message:
                return False, "This email address is already registered."
            if "unique constraint failed: users.user_id" in message:
                return False, "This Student / Role ID is already taken."
            return False, f"Registration failed: {str(e)}"
        self.log_activity(user_id, name, "REGISTRATION", f"Registered as {role}")
        return True, "User registered successfully."

    def get_users_by_credential(self, credential):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT * FROM users
               WHERE LOWER(email)=LOWER(?)
                  OR REPLACE(LOWER(user_id), '/', '-')=REPLACE(LOWER(?), '/', '-')
               ORDER BY id""",
            (credential, credential),
        )
        users = list(cursor.fetchall())
        seen_user_ids = {user["user_id"].casefold() for user in users}

        cursor.execute(
            """SELECT users.* FROM users
               JOIN user_login_aliases ON user_login_aliases.user_id=users.user_id
               WHERE REPLACE(LOWER(user_login_aliases.alias), '/', '-') =
                     REPLACE(LOWER(?), '/', '-')
               ORDER BY users.id""",
            (credential,),
        )
        for user in cursor.fetchall():
            user_id = user["user_id"].casefold()
            if user_id not in seen_user_ids:
                users.append(user)
                seen_user_ids.add(user_id)
        return users

    def get_user_by_credential(self, credential):
        users = self.get_users_by_credential(credential)
        return users[0] if users else None

    def _find_authenticated_user(self, credential, password):
        users = self.get_users_by_credential(credential)
        if not users:
            return None, "Account not found."

        disabled_match = False
        for user in users:
            if not self._verify_password(user["password"], password):
                continue
            if user["status"] != "active":
                disabled_match = True
                continue
            return user, None

        if disabled_match:
            return None, "Your account has been disabled. Please contact the library administrator."
        return None, "Incorrect password."

    def _finish_authentication(self, user, password):
        if user["password"].startswith(("pbkdf2:", "scrypt:")) is False:
            self._upgrade_legacy_hash(user["user_id"], password)
        self.log_activity(user["user_id"], user["name"], "LOGIN", "User logged in successfully")
        return self._public_user(user)

    def authenticate(self, credential, password):
        user, _ = self._find_authenticated_user(str(credential).strip(), password)
        if not user:
            return None
        return self._finish_authentication(user, password)

    def authenticate_with_reason(self, credential, password):
        user, reason = self._find_authenticated_user(str(credential).strip(), password)
        if not user:
            return None, reason
        return self._finish_authentication(user, password), None

    def email_exists(self, email) -> bool:
        cursor = self.db.cursor()
        return cursor.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone() is not None

    def user_id_exists(self, user_id) -> bool:
        cursor = self.db.cursor()
        return cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone() is not None

    # --- Profile & settings ---
    def get_user_by_id(self, user_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return self._public_user(cursor.fetchone())

    def update_avatar_url(self, user_id, avatar_url):
        cursor = self.db.cursor()
        cursor.execute("UPDATE users SET avatar_url=? WHERE user_id=?", (avatar_url, user_id))
        self.db.commit()
        return self.get_user_by_id(user_id)

    def update_profile(self, user_id, name=None, email=None, phone=None, department=None, semester=None):
        fields, values = [], []
        for column, value in (("name", name), ("email", email), ("phone", phone),
                              ("department", department), ("semester", semester)):
            if value is not None:
                fields.append(f"{column}=?")
                values.append(value)
        if not fields:
            return True, "Nothing to update."
        values.append(user_id)
        cursor = self.db.cursor()
        try:
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id=?", values)
            self.db.commit()
        except Exception:
            return False, "That email address is already in use by another account."
        return True, "Profile updated successfully."

    def change_password(self, user_id, current_password, new_password):
        cursor = self.db.cursor()
        cursor.execute("SELECT password FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        if not row or not self._verify_password(row["password"], current_password):
            return False, "Your current password is incorrect."
        cursor.execute("UPDATE users SET password=? WHERE user_id=?",
                       (self._hash_password(new_password), user_id))
        self.db.commit()
        self.log_activity(user_id, user_id, "PASSWORD_CHANGE", "Password changed from account settings")
        return True, "Password changed successfully."

    def set_user_status(self, user_id, status):
        cursor = self.db.cursor()
        cursor.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
        self.db.commit()

    def get_preferences(self, user_id) -> dict:
        cursor = self.db.cursor()
        row = cursor.execute("SELECT preferences FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row and row["preferences"]:
            try:
                return json.loads(row["preferences"])
            except (ValueError, TypeError):
                return {}
        return {}

    def set_preferences(self, user_id, preferences: dict):
        cursor = self.db.cursor()
        cursor.execute("UPDATE users SET preferences=? WHERE user_id=?", (json.dumps(preferences), user_id))
        self.db.commit()

    # --- Password reset OTPs (hashed + expiring, stored in password_reset_otps) ---
    @staticmethod
    def _otp_rate_key(value: str, secret_key: str) -> str:
        return hmac.new(secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()

    def check_otp_request_limit(self, email, ip_address, secret_key):
        """Record a request without storing the raw email address or client IP."""
        now = time.time()
        email_key = self._otp_rate_key(email, secret_key)
        ip_key = self._otp_rate_key(ip_address or "unknown", secret_key)
        cursor = self.db.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("DELETE FROM otp_request_limits WHERE requested_at < ?", (now - 86400,))

        latest = cursor.execute(
            "SELECT requested_at FROM otp_request_limits WHERE email_key=? ORDER BY requested_at DESC LIMIT 1",
            (email_key,),
        ).fetchone()
        if latest:
            wait = math.ceil(latest["requested_at"] + OTP_REQUEST_COOLDOWN_SECONDS - now)
            if wait > 0:
                self.db.rollback()
                return False, wait

        email_count, email_oldest = cursor.execute(
            """SELECT COUNT(*), MIN(requested_at) FROM otp_request_limits
               WHERE email_key=? AND requested_at > ?""",
            (email_key, now - 3600),
        ).fetchone()
        if email_count >= OTP_EMAIL_REQUESTS_PER_HOUR:
            self.db.rollback()
            return False, max(1, math.ceil(email_oldest + 3600 - now))

        ip_count, ip_oldest = cursor.execute(
            """SELECT COUNT(*), MIN(requested_at) FROM otp_request_limits
               WHERE ip_key=? AND requested_at > ?""",
            (ip_key, now - 3600),
        ).fetchone()
        if ip_count >= OTP_IP_REQUESTS_PER_HOUR:
            self.db.rollback()
            return False, max(1, math.ceil(ip_oldest + 3600 - now))

        cursor.execute(
            "INSERT INTO otp_request_limits (email_key, ip_key, requested_at) VALUES (?, ?, ?)",
            (email_key, ip_key, now),
        )
        self.db.commit()
        return True, OTP_REQUEST_COOLDOWN_SECONDS

    def generate_otp(self, email):
        cursor = self.db.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        if not user:
            return None, "No account found with that email address."
        otp = str(secrets.randbelow(900000) + 100000)
        expires_at = (datetime.now() + timedelta(minutes=OTP_MINUTES_VALID)).strftime("%Y-%m-%d %H:%M:%S")
        # Invalidate any previous unused codes, then store only a hash of the new one
        cursor.execute("UPDATE password_reset_otps SET used=1 WHERE user_id=? AND used=0", (user["user_id"],))
        cursor.execute(
            "INSERT INTO password_reset_otps (user_id, otp_hash, expires_at) VALUES (?, ?, ?)",
            (user["user_id"], generate_password_hash(otp), expires_at),
        )
        self.db.commit()
        self.log_activity(user["user_id"], user["name"], "OTP_GENERATE", "Password reset OTP generated")
        return otp, None

    def invalidate_otp(self, email):
        cursor = self.db.cursor()
        cursor.execute(
            """UPDATE password_reset_otps SET used=1
               WHERE user_id=(SELECT user_id FROM users WHERE email=?) AND used=0""",
            (email,),
        )
        self.db.commit()

    def verify_otp(self, email, otp):
        """Returns (ok, message, otp_hash). The hash (never the raw code) backs the
        signed reset token issued after a successful verification."""
        cursor = self.db.cursor()
        cursor.execute("SELECT user_id FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        if not user:
            return False, "No account found with that email address.", None
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """SELECT id, otp_hash, expires_at, verified, attempts FROM password_reset_otps
               WHERE user_id=? AND used=0 ORDER BY id DESC LIMIT 1""",
            (user["user_id"],),
        )
        record = cursor.fetchone()
        if not record:
            self.db.rollback()
            return False, "No active verification code. Please request a new one.", None
        if datetime.now() > datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S"):
            cursor.execute("UPDATE password_reset_otps SET used=1 WHERE id=?", (record["id"],))
            self.db.commit()
            return False, "That verification code has expired. Please request a new one.", None
        if record["verified"]:
            self.db.rollback()
            return False, "That verification code has already been used. Continue resetting your password.", None
        if record["attempts"] >= OTP_MAX_VERIFICATION_ATTEMPTS:
            cursor.execute("UPDATE password_reset_otps SET used=1 WHERE id=?", (record["id"],))
            self.db.commit()
            return False, "Too many incorrect attempts. Please request a new code.", None
        try:
            is_correct = check_password_hash(record["otp_hash"], str(otp))
        except ValueError:
            is_correct = False
        if not is_correct:
            attempts = record["attempts"] + 1
            cursor.execute(
                "UPDATE password_reset_otps SET attempts=?, used=? WHERE id=?",
                (attempts, int(attempts >= OTP_MAX_VERIFICATION_ATTEMPTS), record["id"]),
            )
            self.db.commit()
            if attempts >= OTP_MAX_VERIFICATION_ATTEMPTS:
                return False, "Too many incorrect attempts. Please request a new code.", None
            return False, "That verification code is incorrect.", None
        cursor.execute("UPDATE password_reset_otps SET verified=1 WHERE id=?", (record["id"],))
        self.db.commit()
        return True, "OTP verified.", record["otp_hash"]

    def reset_password_with_hash(self, email, otp_hash, new_password):
        """Complete the reset using the OTP hash carried inside a verified reset token."""
        cursor = self.db.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        if not user:
            return False, "No account found with that email address."
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """SELECT id, expires_at FROM password_reset_otps
               WHERE user_id=? AND used=0 AND verified=1 AND otp_hash=? ORDER BY id DESC LIMIT 1""",
            (user["user_id"], otp_hash),
        )
        record = cursor.fetchone()
        if not record:
            self.db.rollback()
            return False, "That verification code is invalid or was already used."
        if datetime.now() > datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S"):
            self.db.rollback()
            return False, "That verification code has expired. Please request a new one."
        cursor.execute("UPDATE users SET password=? WHERE email=?", (self._hash_password(new_password), email))
        cursor.execute("UPDATE password_reset_otps SET used=1 WHERE id=?", (record["id"],))
        self.db.commit()
        self.log_activity(user["user_id"], user["name"], "PASSWORD_RESET", "Password reset using OTP successfully")
        return True, "Password reset successfully. You can sign in now."

    def reset_password_with_otp(self, email, otp, new_password):
        ok, message, otp_hash = self.verify_otp(email, otp)
        if not ok:
            return False, message
        return self.reset_password_with_hash(email, otp_hash, new_password)

    # --- Activity logs ---
    def log_activity(self, user_id, user_name, action, details):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (user_id, user_name, action, details) VALUES (?, ?, ?, ?)",
            (user_id, user_name, action, details)
        )
        self.db.commit()

    def get_all_activity_logs(self, limit=100):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC, id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # --- User management (admin) ---
    def get_users_by_role(self, role, search=None, status=None):
        cursor = self.db.cursor()
        query = "SELECT * FROM users WHERE role=?"
        params = [role]
        if search:
            query += " AND (name LIKE ? OR email LIKE ? OR user_id LIKE ?)"
            like = f"%{search}%"
            params += [like, like, like]
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY created_at DESC, id DESC"
        cursor.execute(query, params)
        return [self._public_user(row) for row in cursor.fetchall()]

    def count_users_by_role(self, role, status=None):
        cursor = self.db.cursor()
        if status:
            row = cursor.execute("SELECT COUNT(*) FROM users WHERE role=? AND status=?", (role, status)).fetchone()
        else:
            row = cursor.execute("SELECT COUNT(*) FROM users WHERE role=?", (role,)).fetchone()
        return row[0]

    def get_all_users(self, role=None, search=None, status=None):
        """All accounts regardless of role — administrator user management."""
        cursor = self.db.cursor()
        clauses, params = [], []
        if role:
            clauses.append("role=?")
            params.append(role)
        if search:
            like = f"%{search}%"
            clauses.append("(name LIKE ? OR email LIKE ? OR user_id LIKE ?)")
            params += [like, like, like]
        if status:
            clauses.append("status=?")
            params.append(status)
        query = "SELECT * FROM users"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, id DESC"
        cursor.execute(query, params)
        return [self._public_user(row) for row in cursor.fetchall()]

    def set_user_role(self, user_id, role):
        cursor = self.db.cursor()
        cursor.execute("UPDATE users SET role=? WHERE user_id=?", (role, user_id))
        self.db.commit()
        return cursor.rowcount > 0

    def user_growth(self, months=6):
        """Registrations per month for the administrator growth chart."""
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS total
               FROM users
               WHERE created_at >= DATE('now', ?)
               GROUP BY month ORDER BY month ASC""",
            (f"-{int(months)} months",),
        )
        return [dict(row) for row in cursor.fetchall()]

