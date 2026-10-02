from config.database import DatabaseConnection


class LoanDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()
        self.create_table()

    def create_table(self):
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                due_at TEXT NOT NULL,
                returned_at TEXT
            )
            """
        )
        self.db.commit()

    def issue_book(self, user_id: int, book_id: int, due_at: str):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            book = self.db.execute(
                "SELECT id FROM books WHERE id = ? AND is_available = 1", (book_id,)
            ).fetchone()
            member = self.db.execute(
                "SELECT id FROM users WHERE id = ? AND role IN ('student', 'faculty')", (user_id,)
            ).fetchone()
            if book is None or member is None:
                self.db.rollback()
                return None

            cursor = self.db.execute(
                "INSERT INTO loans (book_id, user_id, due_at) VALUES (?, ?, ?)",
                (book_id, user_id, due_at),
            )
            updated = self.db.execute(
                "UPDATE books SET is_available = 0 WHERE id = ? AND is_available = 1", (book_id,)
            )
            if updated.rowcount != 1:
                self.db.rollback()
                return None
            self.db.commit()
            return cursor.lastrowid
        except Exception:
            self.db.rollback()
            raise

    def return_book(self, loan_id: int):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            loan = self.db.execute(
                "SELECT book_id FROM loans WHERE id = ? AND returned_at IS NULL", (loan_id,)
            ).fetchone()
            if loan is None:
                self.db.rollback()
                return False
            self.db.execute(
                "UPDATE loans SET returned_at = CURRENT_TIMESTAMP WHERE id = ?", (loan_id,)
            )
            self.db.execute("UPDATE books SET is_available = 1 WHERE id = ?", (loan["book_id"],))
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def get_user_loans(self, user_id: int):
        rows = self.db.execute(
            """
            SELECT loans.*, books.title, books.author
            FROM loans JOIN books ON books.id = loans.book_id
            WHERE loans.user_id = ? ORDER BY loans.issued_at DESC, loans.id DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_all_loans(self):
        rows = self.db.execute(
            """
            SELECT loans.*, books.title, books.author, users.name AS member_name,
                   users.username, users.role
            FROM loans
            JOIN books ON books.id = loans.book_id
            JOIN users ON users.id = loans.user_id
            ORDER BY loans.issued_at DESC, loans.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def get_active_loans(self):
        return [loan for loan in self.get_all_loans() if loan["returned_at"] is None]

    def get_active_loan_count(self):
        return self.db.execute(
            "SELECT COUNT(*) FROM loans WHERE returned_at IS NULL"
        ).fetchone()[0]