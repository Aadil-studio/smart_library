"""Library-wide settings stored in the settings table (edited by the administrator).

Keys: library_name, loan_period_days, fine_per_day, due_soon_days.
Values are strings in the DB; numeric getters coerce safely.
"""
from config.database import DatabaseConnection

DEFAULTS = {
    "library_name": "Smart Library",
    "loan_period_days": "14",
    "fine_per_day": "10",
    "due_soon_days": "3",
}


class SettingsService:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if row is not None:
            return row[0]
        return DEFAULTS.get(key, default)

    def get_int(self, key, default=0):
        try:
            return int(float(self.get(key, default)))
        except (TypeError, ValueError):
            return default

    def all(self):
        rows = self.db.execute("SELECT key, value FROM settings").fetchall()
        merged = dict(DEFAULTS)
        merged.update({row["key"]: row["value"] for row in rows})
        return merged

    def set(self, key, value):
        self.db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.db.commit()
