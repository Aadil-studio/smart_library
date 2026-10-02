"""Aggregated statistics for admin reports and dashboards."""

from datetime import datetime

from config.database import DatabaseConnection


class ReportService:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    def summary(self):
        cursor = self.db.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        return {
            "total_books": cursor.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "available_copies": cursor.execute(
                "SELECT COALESCE(SUM(available_copies), 0) FROM books").fetchone()[0],
            "total_students": cursor.execute(
                "SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            "active_students": cursor.execute(
                "SELECT COUNT(*) FROM users WHERE role='student' AND status='active'").fetchone()[0],
            "borrowed": cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE status IN ('issued','overdue')").fetchone()[0],
            "overdue": cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE status='overdue' OR (status='issued' AND due_date < ?)",
                (today,),
            ).fetchone()[0],
            "returned_total": cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE status='returned'").fetchone()[0],
            "pending_reservations": cursor.execute(
                "SELECT COUNT(*) FROM reservations WHERE status='pending'").fetchone()[0],
            "unpaid_fines": cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM fines WHERE status='unpaid'").fetchone()[0],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def borrowing_report(self, days=30):
        cursor = self.db.cursor()
        date_from = cursor.execute(
            "SELECT DATE('now', ?)", (f"-{int(days)} days",)
        ).fetchone()[0]
        issued = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE issue_date >= ?", (date_from,)
        ).fetchone()[0]
        returned = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE return_date >= ?", (date_from,)
        ).fetchone()[0]
        overdue = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE status='overdue' OR (status='issued' AND due_date < ?)",
            (datetime.now().strftime("%Y-%m-%d"),),
        ).fetchone()[0]
        fines = cursor.execute(
            "SELECT COALESCE(SUM(fine_amount), 0) FROM transactions WHERE issue_date >= ?",
            (date_from,),
        ).fetchone()[0]
        return {
            "period_days": int(days),
            "date_from": date_from,
            "issued": issued,
            "returned": returned,
            "overdue": overdue,
            "fines_total": fines,
        }
