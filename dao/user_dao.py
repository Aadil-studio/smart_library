import hashlib
import json
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from config.database import DatabaseConnection

OTP_MINUTES_VALID = 10


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

    def authenticate(self, credential, password):
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE (email=? OR user_id=?) AND status='active'",
            (credential, credential),
        )
        user = cursor.fetchone()
        if not user:
            return None
        if not self._verify_password(user["password"], password):
            return None
        if user["password"].startswith(("pbkdf2:", "scrypt:")) is False:
            self._upgrade_legacy_hash(user["user_id"], password)
        self.log_activity(user["user_id"], user["name"], "LOGIN", "User logged in successfully")
        return self._public_user(user)

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
    def generate_otp(self, email):
        cursor = self.db.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        if not user:
            return None, "No account found with that email address."
        import random
        otp = str(random.randint(100000, 999999))
        expires_at = (datetime.now() + timedelta(minutes=OTP_MINUTES_VALID)).strftime("%Y-%m-%d %H:%M:%S")
        # Invalidate any previous unused codes, then store only a hash of the new one
        cursor.execute("UPDATE password_reset_otps SET used=1 WHERE user_id=? AND used=0", (user["user_id"],))
        cursor.execute(
            "INSERT INTO password_reset_otps (user_id, otp_hash, expires_at) VALUES (?, ?, ?)",
            (user["user_id"], hashlib.sha256(otp.encode()).hexdigest(), expires_at),
        )
        self.db.commit()
        self.log_activity(user["user_id"], user["name"], "OTP_GENERATE", "Password reset OTP generated")
        return otp, None

    def verify_otp(self, email, otp):
        cursor = self.db.cursor()
        cursor.execute("SELECT user_id FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        if not user:
            return False, "No account found with that email address."
        cursor.execute(
            """SELECT id, otp_hash, expires_at FROM password_reset_otps
               WHERE user_id=? AND used=0 ORDER BY id DESC LIMIT 1""",
            (user["user_id"],),
        )
        record = cursor.fetchone()
        if not record:
            return False, "No active verification code. Please request a new one."
        if record["otp_hash"] != hashlib.sha256(str(otp).encode()).hexdigest():
            return False, "That verification code is incorrect."
        if datetime.now() > datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S"):
            return False, "That verification code has expired. Please request a new one."
        return True, "OTP verified."

    def reset_password_with_otp(self, email, otp, new_password):
        ok, message = self.verify_otp(email, otp)
        if not ok:
            return False, message
        cursor = self.db.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        cursor.execute("UPDATE users SET password=? WHERE email=?", (self._hash_password(new_password), email))
        cursor.execute(
            "UPDATE password_reset_otps SET used=1 WHERE user_id=? AND used=0",
            (user["user_id"],),
        )
        self.db.commit()
        self.log_activity(user["user_id"], user["name"], "PASSWORD_RESET", "Password reset using OTP successfully")
        return True, "Password reset successfully. You can sign in now."

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
