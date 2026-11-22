from config.database import DatabaseConnection


class StudentPortalDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    def list_wishlist(self, user_id):
        rows = self.db.execute(
            """SELECT book_id, created_at FROM wishlist
               WHERE user_id=? ORDER BY created_at DESC, id DESC""",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def toggle_wishlist(self, user_id, book_id):
        cursor = self.db.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            book = cursor.execute("SELECT 1 FROM books WHERE id=?", (book_id,)).fetchone()
            if not book:
                return None

            existing = cursor.execute(
                "SELECT id FROM wishlist WHERE user_id=? AND book_id=?",
                (user_id, book_id),
            ).fetchone()
            if existing:
                cursor.execute("DELETE FROM wishlist WHERE id=?", (existing["id"],))
                saved = False
            else:
                cursor.execute(
                    "INSERT INTO wishlist (user_id, book_id) VALUES (?, ?)",
                    (user_id, book_id),
                )
                saved = True
            self.db.commit()
            return saved
        finally:
            if self.db.in_transaction:
                self.db.rollback()

    def renewed_loan_ids(self, student_id):
        rows = self.db.execute(
            "SELECT loan_id FROM student_loan_renewals WHERE student_id=?",
            (student_id,),
        ).fetchall()
        return [row["loan_id"] for row in rows]

    def renew_loan(self, student_id, loan_id):
        cursor = self.db.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            loan = cursor.execute(
                "SELECT student_id, due_date, status FROM transactions WHERE id=?",
                (loan_id,),
            ).fetchone()
            if not loan or loan["student_id"] != student_id:
                return None, "Loan not found.", 404
            if loan["status"] != "issued":
                return None, "Only active loans can be renewed.", 409
            if not cursor.execute(
                "SELECT DATE(?) >= DATE('now')",
                (loan["due_date"],),
            ).fetchone()[0]:
                return None, "Overdue loans cannot be renewed.", 409
            if cursor.execute(
                "SELECT 1 FROM student_loan_renewals WHERE loan_id=?",
                (loan_id,),
            ).fetchone():
                return None, "This loan has already been renewed.", 409

            renewed_due_date = cursor.execute(
                "SELECT DATE(?, '+7 days')",
                (loan["due_date"],),
            ).fetchone()[0]
            if not renewed_due_date:
                return None, "The loan due date is invalid.", 409

            cursor.execute(
                """INSERT INTO student_loan_renewals
                   (loan_id, student_id, original_due_date, renewed_due_date)
                   VALUES (?, ?, ?, ?)""",
                (loan_id, student_id, loan["due_date"], renewed_due_date),
            )
            cursor.execute(
                """UPDATE transactions SET due_date=?
                   WHERE id=? AND student_id=? AND status='issued' AND due_date=?
                     AND DATE(due_date)>=DATE('now')""",
                (renewed_due_date, loan_id, student_id, loan["due_date"]),
            )
            if cursor.rowcount != 1:
                return None, "The loan changed before it could be renewed. Please refresh and try again.", 409

            self.db.commit()
            return renewed_due_date, None, 200
        finally:
            if self.db.in_transaction:
                self.db.rollback()
