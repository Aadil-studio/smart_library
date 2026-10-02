from datetime import datetime, timedelta
import sqlite3

from config.database import DatabaseConnection
from models.models import Book, IssueRecord, Member


class BookDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    def add_book(self, title: str, author: str, isbn: str, category="General", publisher="", edition="",
                 publication_year=2026, total_copies=1, shelf_no="A1", description=""):
        cursor = self.db.cursor()
        try:
            cursor.execute(
                """INSERT INTO books (title, author, isbn, category, publisher, edition, publication_year,
                                      total_copies, available_copies, shelf_no, is_available, description,
                                      status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 'active', CURRENT_TIMESTAMP)""",
                (title, author, isbn, category, publisher, edition, publication_year, total_copies,
                 total_copies, shelf_no, description)
            )
            self.db.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_all_books(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM books ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_book_by_id(self, book_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM books WHERE id=?", (book_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_book_by_isbn(self, isbn):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM books WHERE isbn=?", (isbn,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_books(self, query):
        cursor = self.db.cursor()
        term = f"%{query}%"
        cursor.execute(
            """SELECT * FROM books
               WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? OR category LIKE ? OR publisher LIKE ?
               ORDER BY id DESC""",
            (term, term, term, term, term),
        )
        return [dict(row) for row in cursor.fetchall()]

    def filter_books(self, search=None, category=None, author=None, availability=None):
        """Combined search and filters used by the catalog API."""
        cursor = self.db.cursor()
        clauses, params = [], []
        if search:
            term = f"%{search}%"
            clauses.append("(title LIKE ? OR author LIKE ? OR isbn LIKE ? OR category LIKE ? OR publisher LIKE ?)")
            params.extend([term, term, term, term, term])
        if category:
            clauses.append("category = ?")
            params.append(category)
        if author:
            clauses.append("author LIKE ?")
            params.append(f"%{author}%")
        if availability == "available":
            clauses.append("available_copies > 0")
        elif availability == "unavailable":
            clauses.append("available_copies <= 0")
        query = "SELECT * FROM books"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_categories(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category != '' ORDER BY category")
        return [row["category"] for row in cursor.fetchall()]

    def get_authors(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT DISTINCT author FROM books ORDER BY author")
        return [row["author"] for row in cursor.fetchall()]

    def update_book(self, book_id, **fields):
        """Update safe book fields and keep available copies within the total."""
        book = self.get_book_by_id(book_id)
        if not book:
            return False, "Book not found."

        allowed = ("title", "author", "isbn", "category", "publisher", "edition",
                   "publication_year", "shelf_no", "description", "status")
        updates, params = [], []
        for column in allowed:
            if fields.get(column) is not None:
                updates.append(f"{column}=?")
                params.append(fields[column])

        if fields.get("total_copies") is not None:
            total = int(fields["total_copies"])
            borrowed = book["total_copies"] - book["available_copies"]
            if total < borrowed:
                return False, f"Total copies cannot be less than the {borrowed} currently borrowed."
            updates.extend(("total_copies=?", "available_copies=?", "is_available=?"))
            params.extend((total, total - borrowed, 1 if total - borrowed > 0 else 0))

        if not updates:
            return True, "Nothing to update."
        params.append(book_id)
        cursor = self.db.cursor()
        try:
            cursor.execute(f"UPDATE books SET {', '.join(updates)} WHERE id=?", params)
            self.db.commit()
        except sqlite3.IntegrityError:
            return False, "Another book already uses that ISBN."
        return True, "Book updated successfully."

    def delete_book(self, book_id):
        cursor = self.db.cursor()
        book = self.get_book_by_id(book_id)
        if not book:
            return False, "Book not found."
        row = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE book_id=? AND status IN ('issued', 'overdue')",
            (book_id,),
        ).fetchone()
        if row[0] > 0:
            return False, "This book has copies currently borrowed by students and cannot be deleted."
        cursor.execute("DELETE FROM reservations WHERE book_id=?", (book_id,))
        cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
        self.db.commit()
        return True, "Book deleted successfully."

    def count_books(self, available_only=False):
        cursor = self.db.cursor()
        if available_only:
            row = cursor.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books").fetchone()
        else:
            row = cursor.execute("SELECT COUNT(*) FROM books").fetchone()
        return row[0]

    def category_distribution(self):
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT COALESCE(NULLIF(category, ''), 'Uncategorized') AS category, COUNT(*) AS total
               FROM books GROUP BY category ORDER BY total DESC"""
        )
        return [dict(row) for row in cursor.fetchall()]


class MemberDAO:
    """Member-facing data operations, compatible with legacy and current schemas."""

    def __init__(self, db_connection):
        self.conn = db_connection

    def _table_exists(self, table_name):
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).fetchone()
        return row is not None

    def _columns(self, table_name):
        return {row[1] for row in self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()}

    def get_member_profile(self, member_id):
        columns = self._columns("users")
        cursor = self.conn.cursor()
        if "role_id" in columns:
            cursor.execute(
                """SELECT user_id, name, email, password, membership_date, max_books_allowed, fine_balance
                   FROM users WHERE user_id=? AND role_id=1""",
                (member_id,),
            )
            row = cursor.fetchone()
            return Member(*row) if row else None

        if "role" not in columns:
            return None
        cursor.execute(
            "SELECT user_id, name, email, password, created_at FROM users WHERE user_id=? AND role='student'",
            (member_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        fine_balance = 0.0
        if self._table_exists("fines"):
            fine_balance = cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM fines WHERE student_id=? AND status='unpaid'",
                (member_id,),
            ).fetchone()[0]
        return Member(row["user_id"], row["name"], row["email"], row["password"],
                      row["created_at"], 3, fine_balance)

    def search_books(self, search_term=""):
        columns = self._columns("books")
        id_column = "book_id" if "book_id" in columns else "id"
        category = "category" if "category" in columns else "''"
        available = "available_copies" if "available_copies" in columns else "CASE WHEN is_available THEN 1 ELSE 0 END"
        total = "total_copies" if "total_copies" in columns else "1"
        term = f"%{search_term}%"
        cursor = self.conn.cursor()
        cursor.execute(
            f"""SELECT {id_column}, title, author, isbn, {category}, {available}, {total}
                FROM books WHERE title LIKE ? OR author LIKE ? OR {category} LIKE ? OR isbn LIKE ?
                ORDER BY title""",
            (term, term, term, term),
        )
        return [Book(*row) for row in cursor.fetchall()]

    def request_book_issue(self, member_id, book_id):
        if self._table_exists("transactions"):
            return self._request_current_issue(member_id, book_id)
        return self._request_legacy_issue(member_id, book_id)

    def _request_legacy_issue(self, member_id, book_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM issue_records WHERE member_id=? AND status='ISSUED'", (member_id,)
        )
        active_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT max_books_allowed FROM users WHERE user_id=? AND role_id=1", (member_id,)
        )
        member = cursor.fetchone()
        if not member:
            return False, "Invalid Member ID."
        max_allowed = member[0]
        if active_count >= max_allowed:
            return False, f"Limit reached. You cannot borrow more than {max_allowed} books at once."

        cursor.execute("SELECT available_copies FROM books WHERE book_id=?", (book_id,))
        book = cursor.fetchone()
        if not book or book[0] <= 0:
            return False, "Requested book is currently out of stock."
        issue_date = datetime.now().strftime("%Y-%m-%d")
        due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        try:
            cursor.execute(
                """INSERT INTO issue_records (member_id, book_id, issue_date, due_date, status, fine_amount)
                   VALUES (?, ?, ?, ?, 'ISSUED', 0.0)""",
                (member_id, book_id, issue_date, due_date),
            )
            cursor.execute("UPDATE books SET available_copies=available_copies-1 WHERE book_id=?", (book_id,))
            self.conn.commit()
            return True, f"Book issued successfully! Due date: {due_date}"
        except sqlite3.Error as error:
            self.conn.rollback()
            return False, f"Database error: {error}"

    def _request_current_issue(self, member_id, book_id):
        cursor = self.conn.cursor()
        user_columns = self._columns("users")
        book_columns = self._columns("books")
        role_filter = "role='student'" if "role" in user_columns else "role_id=1"
        member = cursor.execute(
            f"SELECT * FROM users WHERE user_id=? AND {role_filter}", (member_id,)
        ).fetchone()
        if not member:
            return False, "Invalid Member ID."
        if "status" in user_columns and member["status"] != "active":
            return False, "That student account is deactivated."
        max_allowed = member["max_books_allowed"] if "max_books_allowed" in user_columns else 3
        active_count = cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE student_id=? AND status IN ('issued', 'overdue')",
            (member_id,),
        ).fetchone()[0]
        if active_count >= max_allowed:
            return False, f"Limit reached. You cannot borrow more than {max_allowed} books at once."

        book_id_column = "book_id" if "book_id" in book_columns else "id"
        book = cursor.execute(
            f"SELECT available_copies FROM books WHERE {book_id_column}=?", (book_id,)
        ).fetchone()
        if not book or book[0] <= 0:
            return False, "Requested book is currently out of stock."
        issue_date = datetime.now().strftime("%Y-%m-%d")
        due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        try:
            cursor.execute(
                """INSERT INTO transactions (student_id, book_id, issue_date, due_date, status, fine_amount)
                   VALUES (?, ?, ?, ?, 'issued', 0.0)""",
                (member_id, book_id, issue_date, due_date),
            )
            cursor.execute(
                f"UPDATE books SET available_copies=available_copies-1 WHERE {book_id_column}=?", (book_id,)
            )
            if "is_available" in book_columns:
                cursor.execute(
                    f"UPDATE books SET is_available=CASE WHEN available_copies > 1 THEN 1 ELSE 0 END WHERE {book_id_column}=?",
                    (book_id,),
                )
            self.conn.commit()
            return True, f"Book issued successfully! Due date: {due_date}"
        except sqlite3.Error as error:
            self.conn.rollback()
            return False, f"Database error: {error}"

    def get_borrowing_history(self, member_id):
        cursor = self.conn.cursor()
        if self._table_exists("transactions"):
            cursor.execute(
                """SELECT id, student_id, book_id, issue_date, due_date, return_date, status, fine_amount
                   FROM transactions WHERE student_id=? ORDER BY issue_date DESC, id DESC""",
                (member_id,),
            )
        else:
            cursor.execute(
                """SELECT record_id, member_id, book_id, issue_date, due_date, return_date, status, fine_amount
                   FROM issue_records WHERE member_id=? ORDER BY issue_date DESC""",
                (member_id,),
            )
        return [IssueRecord(*row) for row in cursor.fetchall()]