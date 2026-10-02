from config.database import DatabaseConnection


class NotificationDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    def notify(self, user_id, title, message, ntype=None, ref_id=None):
        cursor = self.db.cursor()
        if ntype and ref_id is not None:
            # De-duplicate event-driven notifications (e.g. one overdue alert per loan)
            existing = cursor.execute(
                "SELECT 1 FROM notifications WHERE user_id=? AND type=? AND ref_id=?",
                (user_id, ntype, ref_id),
            ).fetchone()
            if existing:
                return None
        cursor.execute(
            "INSERT INTO notifications (user_id, title, message, type, ref_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, message, ntype, ref_id),
        )
        self.db.commit()
        return cursor.lastrowid

    def get_user_notifications(self, user_id, unread_only=False):
        cursor = self.db.cursor()
        sql = "SELECT * FROM notifications WHERE user_id=?"
        if unread_only:
            sql += " AND is_read=0"
        sql += " ORDER BY created_at DESC, id DESC"
        cursor.execute(sql, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    def unread_count(self, user_id):
        cursor = self.db.cursor()
        row = cursor.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user_id,)
        ).fetchone()
        return row[0]

    def mark_read(self, notification_id, user_id):
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
            (notification_id, user_id),
        )
        self.db.commit()
        return cursor.rowcount > 0

    def mark_all_read(self, user_id):
        cursor = self.db.cursor()
        cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
        self.db.commit()

    def get_student_notifications(self, student_id: str):
        """Backward-compatible alias used by the original controller."""
        return self.get_user_notifications(student_id)
