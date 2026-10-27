from datetime import datetime, timedelta

from config.database import DatabaseConnection
from dao.notification_dao import NotificationDAO
from services.fine_strategy import FineContext, FacultyFineStrategy, StudentFineStrategy


class BorrowDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()
        self.notification_dao = NotificationDAO()

    # --- Issue ---
    def issue_book(self, student_id: str, book_id: int, days=14):
        cursor = self.db.cursor()
        cursor.execute("SELECT available_copies, title, status, fee FROM books WHERE id=?", (book_id,))
        book = cursor.fetchone()
        if not book:
            return False, "Book not found.", None
        if book["status"] != "active":
            return False, "This book is currently marked inactive and cannot be issued.", None
        if book["available_copies"] < 1:
            return False, "Book is not available for issue.", None

        cursor.execute("SELECT name, status FROM users WHERE user_id=?", (student_id,))
        member = cursor.fetchone()
        if not member:
            return False, "Student not found.", None
        if member["status"] != "active":
            return False, "That student account is deactivated.", None

        duplicate = cursor.execute(
            "SELECT 1 FROM transactions WHERE student_id=? AND book_id=? AND status IN ('issued', 'overdue')",
            (student_id, book_id),
        ).fetchone()
        if duplicate:
            return False, "That student already has an active loan for this book.", None

        issue_date = datetime.now().strftime("%Y-%m-%d")
        due_date = (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d")

        cursor.execute(
            """INSERT INTO transactions (student_id, book_id, issue_date, due_date, status)
               VALUES (?, ?, ?, ?, 'issued')""",
            (student_id, book_id, issue_date, due_date)
        )
        transaction_id = cursor.lastrowid

        new_copies = book["available_copies"] - 1
        cursor.execute(
            "UPDATE books SET available_copies=?, is_available=? WHERE id=?",
            (new_copies, 1 if new_copies > 0 else 0, book_id)
        )

        # If an approved reservation exists for this member + book, it is now fulfilled
        reservation = cursor.execute(
            "SELECT id FROM reservations WHERE student_id=? AND book_id=? AND status='approved'",
            (student_id, book_id),
        ).fetchone()
        if reservation:
            cursor.execute("UPDATE reservations SET status='fulfilled' WHERE id=?", (reservation["id"],))

        self.db.commit()
        self.notification_dao.notify(
            student_id,
            "Book issued",
            f"'{book['title']}' has been issued to you. Due date: {due_date}.",
            ntype="borrow",
            ref_id=transaction_id,
        )
        return True, f"Book issued successfully. Due date: {due_date}", transaction_id

    # --- Return ---
    def return_book(self, transaction_id: int, user_role="student", fine_rate=None):
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE id=? AND status IN ('issued', 'overdue')",
            (transaction_id,),
        )
        trans = cursor.fetchone()
        if not trans:
            return False, "Active transaction not found (it may already have been returned).", None

        return_date = datetime.now().date()
        due_date = datetime.strptime(trans["due_date"], "%Y-%m-%d").date()
        overdue_days = max(0, (return_date - due_date).days)

        strategy = FacultyFineStrategy() if user_role.lower() == "faculty" else StudentFineStrategy(
            rate_per_day=10.0 if fine_rate is None else fine_rate
        )
        calculated_fine = FineContext(strategy).compute_fine(overdue_days)

        cursor.execute(
            "UPDATE transactions SET return_date=?, fine_amount=?, status='returned' WHERE id=?",
            (return_date.strftime("%Y-%m-%d"), calculated_fine, transaction_id)
        )

        cursor.execute("SELECT available_copies, total_copies FROM books WHERE id=?", (trans["book_id"],))
        book = cursor.fetchone()
        new_copies = min(book["available_copies"] + 1, book["total_copies"])
        cursor.execute(
            "UPDATE books SET available_copies=?, is_available=? WHERE id=?",
            (new_copies, 1 if new_copies > 0 else 0, trans["book_id"])
        )

        if calculated_fine > 0:
            cursor.execute(
                "INSERT INTO fines (student_id, transaction_id, amount, status) VALUES (?, ?, ?, 'unpaid')",
                (trans["student_id"], transaction_id, calculated_fine)
            )

        self.db.commit()
        title = cursor.execute("SELECT title FROM books WHERE id=?", (trans["book_id"],)).fetchone()
        book_title = title["title"] if title else "Your book"
        fine_note = f" Overdue fine: Rs. {calculated_fine}." if calculated_fine > 0 else ""
        self.notification_dao.notify(
            trans["student_id"],
            "Book returned",
            f"Return of '{book_title}' logged.{fine_note}",
            ntype="return",
            ref_id=transaction_id,
        )
        return True, "Book returned successfully.", calculated_fine

    # --- Queries ---
    def get_transaction_by_id(self, transaction_id):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT t.*, b.title AS book_title, b.author AS book_author, u.name AS student_name
               FROM transactions t
               JOIN books b ON t.book_id = b.id
               LEFT JOIN users u ON u.user_id = t.student_id
               WHERE t.id=?""",
            (transaction_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_transactions(self, student_id=None, status=None, search=None):
        cursor = self.db.cursor()
        clauses, params = [], []
        if student_id:
            clauses.append("t.student_id = ?")
            params.append(student_id)
        if status:
            if status == "active":
                clauses.append("t.status IN ('issued', 'overdue')")
            else:
                clauses.append("t.status = ?")
                params.append(status)
        if search:
            q = f"%{search}%"
            clauses.append("(b.title LIKE ? OR b.isbn LIKE ? OR u.name LIKE ? OR t.student_id LIKE ?)")
            params += [q, q, q, q]
        sql = """SELECT t.*, b.title AS book_title, b.author AS book_author, b.isbn AS book_isbn,
                        u.name AS student_name
                 FROM transactions t
                 JOIN books b ON t.book_id = b.id
                 LEFT JOIN users u ON u.user_id = t.student_id"""
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY t.id DESC"
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_student_borrowed_books(self, student_id: str, active_only=False):
        cursor = self.db.cursor()
        sql = """SELECT t.id as transaction_id, t.book_id, b.title, b.author, b.isbn,
                        t.issue_date, t.due_date, t.return_date, t.status, t.fine_amount
                 FROM transactions t
                 JOIN books b ON t.book_id = b.id
                 WHERE t.student_id = ?"""
        if active_only:
            sql += " AND t.status IN ('issued', 'overdue')"
        sql += " ORDER BY t.id DESC"
        cursor.execute(sql, (student_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_student_fines(self, student_id: str):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT f.*, b.title AS book_title, t.due_date, t.return_date
               FROM fines f
               JOIN transactions t ON f.transaction_id = t.id
               JOIN books b ON t.book_id = b.id
               WHERE f.student_id=? ORDER BY f.id DESC""",
            (student_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_fines(self, status=None, search=None):
        cursor = self.db.cursor()
        clauses, params = [], []
        if status:
            clauses.append("f.status=?")
            params.append(status)
        if search:
            query = f"%{search}%"
            clauses.append("(CAST(f.id AS TEXT) LIKE ? OR u.name LIKE ? OR f.student_id LIKE ? OR b.title LIKE ? OR b.isbn LIKE ?)")
            params.extend([query, query, query, query, query])
        sql = """SELECT f.*, u.name AS student_name, b.title AS book_title, b.isbn AS book_isbn,
                t.due_date, t.return_date,
                MAX(0, CAST(julianday(COALESCE(t.return_date, DATE('now'))) - julianday(t.due_date) AS INTEGER)) AS overdue_days
                 FROM fines f
                 JOIN transactions t ON t.id=f.transaction_id
                 JOIN books b ON b.id=t.book_id
                 JOIN users u ON u.user_id=f.student_id"""
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY f.id DESC"
        return [dict(row) for row in cursor.execute(sql, params).fetchall()]

    def mark_fine_paid(self, fine_id, collector_id):
        cursor = self.db.cursor()
        cursor.execute(
            """UPDATE fines SET status='paid', payment_date=DATE('now'), collected_by=?
               WHERE id=? AND status='unpaid'""",
            (collector_id, fine_id),
        )
        if cursor.rowcount == 0:
            exists = cursor.execute("SELECT 1 FROM fines WHERE id=?", (fine_id,)).fetchone()
            return None, "Fine has already been paid." if exists else "Fine not found."
        self.db.commit()
        fine = cursor.execute(
            """SELECT f.*, u.name AS student_name, b.title AS book_title
               FROM fines f
               JOIN transactions t ON t.id=f.transaction_id
               JOIN books b ON b.id=t.book_id
               JOIN users u ON u.user_id=f.student_id
               WHERE f.id=?""",
            (fine_id,),
        ).fetchone()
        return dict(fine), None

    def waive_fine(self, fine_id, waived_by, reason):
        cursor = self.db.cursor()
        cursor.execute(
            """UPDATE fines SET status='waived', waived_by=?, waive_reason=?, waived_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='unpaid'""",
            (waived_by, reason, fine_id),
        )
        if cursor.rowcount == 0:
            exists = cursor.execute("SELECT 1 FROM fines WHERE id=?", (fine_id,)).fetchone()
            return None, "Fine has already been settled." if exists else "Fine not found."
        self.db.commit()
        fine = cursor.execute(
            """SELECT f.*, u.name AS student_name, b.title AS book_title
               FROM fines f
               JOIN transactions t ON t.id=f.transaction_id
               JOIN books b ON b.id=t.book_id
               JOIN users u ON u.user_id=f.student_id
               WHERE f.id=?""",
            (fine_id,),
        ).fetchone()
        return dict(fine), None

    # --- Book fees (uploaded by the ADMIN only; publishing to the student portal is
    # automatic; only the admin marks a fee paid; borrowing is blocked while unpaid) ---
    FEE_SELECT = """SELECT f.*, u.name AS student_name, b.title AS book_title,
                           b.isbn AS book_isbn, b.author AS book_author
                    FROM book_fees f
                    JOIN users u ON u.user_id=f.student_id
                    LEFT JOIN books b ON b.id=f.book_id"""

    def create_fee(self, student_id: str, amount: float, book_id=None, transaction_id=None,
                   uploaded_by=None):
        """Upload a book fee for a member. Admin-only via the API layer."""
        cursor = self.db.cursor()
        cursor.execute(
            """INSERT INTO book_fees (student_id, book_id, transaction_id, amount, status, uploaded_by)
               VALUES (?, ?, ?, ?, 'unpaid', ?)""",
            (student_id, book_id, transaction_id, float(amount), uploaded_by),
        )
        fee_id = cursor.lastrowid
        self.db.commit()
        return self.get_fee_by_id(fee_id)

    def list_fees(self, student_id=None, status=None, search=None):
        cursor = self.db.cursor()
        clauses, params = [], []
        if student_id:
            clauses.append("f.student_id=?")
            params.append(student_id)
        if status:
            clauses.append("f.status=?")
            params.append(status)
        if search:
            query = f"%{search}%"
            clauses.append("(CAST(f.id AS TEXT) LIKE ? OR u.name LIKE ? OR f.student_id LIKE ? OR b.title LIKE ?)")
            params.extend([query, query, query, query])
        sql = self.FEE_SELECT
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY f.id DESC"
        return [dict(row) for row in cursor.execute(sql, params).fetchall()]

    def get_fee_by_id(self, fee_id):
        cursor = self.db.cursor()
        row = cursor.execute(self.FEE_SELECT + " WHERE f.id=?", (fee_id,)).fetchone()
        return dict(row) if row else None

    def mark_fee_paid(self, fee_id, collector_id):
        cursor = self.db.cursor()
        cursor.execute(
            """UPDATE book_fees SET status='paid', payment_date=DATE('now'), collected_by=?
               WHERE id=? AND status='unpaid'""",
            (collector_id, fee_id),
        )
        if cursor.rowcount == 0:
            exists = cursor.execute("SELECT 1 FROM book_fees WHERE id=?", (fee_id,)).fetchone()
            return None, "Fee has already been paid." if exists else "Fee not found."
        self.db.commit()
        return self.get_fee_by_id(fee_id), None

    def fee_summary(self):
        cursor = self.db.cursor()
        rows = cursor.execute(
            "SELECT status, COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM book_fees GROUP BY status"
        ).fetchall()
        by_status = {row["status"]: {"count": row["count"], "total": row["total"]} for row in rows}
        return {
            "outstanding": by_status.get("unpaid", {}).get("total", 0),
            "outstanding_count": by_status.get("unpaid", {}).get("count", 0),
            "collected": by_status.get("paid", {}).get("total", 0),
            "collected_count": by_status.get("paid", {}).get("count", 0),
        }

    def fine_summary(self):
        cursor = self.db.cursor()
        rows = cursor.execute(
            "SELECT status, COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM fines GROUP BY status"
        ).fetchall()
        by_status = {row["status"]: {"count": row["count"], "total": row["total"]} for row in rows}
        return {
            "outstanding": by_status.get("unpaid", {}).get("total", 0),
            "outstanding_count": by_status.get("unpaid", {}).get("count", 0),
            "collected": by_status.get("paid", {}).get("total", 0),
            "collected_count": by_status.get("paid", {}).get("count", 0),
            "waived": by_status.get("waived", {}).get("total", 0),
            "waived_count": by_status.get("waived", {}).get("count", 0),
        }

    def fine_collection_trend(self, days=14):
        cursor = self.db.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor.execute(
            """SELECT payment_date AS day, COALESCE(SUM(amount), 0) AS total
               FROM fines WHERE status='paid' AND payment_date >= ?
               GROUP BY payment_date ORDER BY payment_date ASC""",
            (since,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def sum_unpaid_fines(self, student_id=None):
        cursor = self.db.cursor()
        if student_id:
            row = cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM fines WHERE student_id=? AND status='unpaid'",
                (student_id,),
            ).fetchone()
        else:
            row = cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM fines WHERE status='unpaid'").fetchone()
        return row[0]

    # --- Overdue handling ---
    def detect_overdue(self):
        """Mark issued transactions whose due date has passed as overdue. Returns affected rows."""
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE transactions SET status='overdue' WHERE status='issued' AND due_date < ?",
            (datetime.now().strftime("%Y-%m-%d"),),
        )
        changed = cursor.rowcount
        self.db.commit()
        return changed

    def get_overdue_transactions(self):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT t.*, b.title AS book_title, u.name AS student_name,
                      CAST(julianday('now') - julianday(t.due_date) AS INTEGER) AS overdue_days
               FROM transactions t
               JOIN books b ON t.book_id = b.id
               LEFT JOIN users u ON u.user_id = t.student_id
               WHERE t.status IN ('issued', 'overdue') AND t.due_date < ?
               ORDER BY t.due_date ASC""",
            (datetime.now().strftime("%Y-%m-%d"),),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_due_soon_transactions(self, within_days=3):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT t.*, b.title AS book_title
               FROM transactions t
               JOIN books b ON t.book_id = b.id
               WHERE t.status = 'issued'
                 AND t.due_date >= ?
                 AND t.due_date <= ?
               ORDER BY t.due_date ASC""",
            (datetime.now().strftime("%Y-%m-%d"),
             (datetime.now() + timedelta(days=within_days)).strftime("%Y-%m-%d")),
        )
        return [dict(row) for row in cursor.fetchall()]

    # --- Counts for dashboards/reports ---
    def count_borrows(self, status=None):
        cursor = self.db.cursor()
        if status == "active":
            row = cursor.execute("SELECT COUNT(*) FROM transactions WHERE status IN ('issued', 'overdue')").fetchone()
        elif status == "returned":
            row = cursor.execute("SELECT COUNT(*) FROM transactions WHERE status='returned'").fetchone()
        elif status == "overdue":
            row = cursor.execute("SELECT COUNT(*) FROM transactions WHERE status='overdue'").fetchone()
        elif status == "all":
            row = cursor.execute("SELECT COUNT(*) FROM transactions").fetchone()
        else:
            row = cursor.execute("SELECT COUNT(*) FROM transactions WHERE status IN ('issued', 'overdue')").fetchone()
        return row[0]

    def most_borrowed_books(self, limit=8):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT b.id, b.title, b.author, b.category, COUNT(t.id) AS borrow_count
               FROM transactions t
               JOIN books b ON t.book_id = b.id
               GROUP BY t.book_id ORDER BY borrow_count DESC LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def borrowing_trend(self, days=14):
        cursor = self.db.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor.execute(
            """SELECT issue_date AS day, COUNT(*) AS total
               FROM transactions WHERE issue_date >= ?
               GROUP BY issue_date ORDER BY issue_date ASC""",
            (since,),
        )
        return [dict(row) for row in cursor.fetchall()]
