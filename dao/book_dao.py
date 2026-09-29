from datetime import datetime, timedelta
import sqlite3
from models import Book, IssueRecord, Member


class MemberDAO:
    """Data Access Object handling Member operations (Role 1)."""

    def __init__(self, db_connection):
        self.conn = db_connection

    def get_member_profile(self, member_id):
        """Fetches profile details for a specific member."""
        cursor = self.conn.cursor()
        query = """
            SELECT user_id, name, email, password, membership_date, max_books_allowed, fine_balance 
            FROM users 
            WHERE user_id = ? AND role_id = 1
        """
        cursor.execute(query, (member_id,))
        row = cursor.fetchone()
        if row:
            return Member(*row)
        return None

    def search_books(self, search_term=""):
        """Searches available books by Title, Author, Category, or ISBN using parameterized query."""
        cursor = self.conn.cursor()
        query = """
            SELECT book_id, title, author, isbn, category, available_copies, total_copies 
            FROM books 
            WHERE title LIKE ? OR author LIKE ? OR category LIKE ? OR isbn LIKE ?
        """
        term = f"%{search_term}%"
        cursor.execute(query, (term, term, term, term))
        rows = cursor.fetchall()
        return [Book(*row) for row in rows]

    def request_book_issue(self, member_id, book_id):
        """Processes a book borrowing request for Member Role 1."""
        cursor = self.conn.cursor()

        # Check maximum allowed books limit
        cursor.execute(
            "SELECT COUNT(*) FROM issue_records WHERE member_id = ? AND status = 'ISSUED'",
            (member_id,),
        )
        active_borrowed_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT max_books_allowed FROM users WHERE user_id = ? AND role_id = 1",
            (member_id,),
        )
        member_row = cursor.fetchone()

        if not member_row:
            return False, "Invalid Member ID."

        max_allowed = member_row[0]
        if active_borrowed_count >= max_allowed:
            return (
                False,
                f"Limit reached. You cannot borrow more than {max_allowed} books at once.",
            )

        # Check book stock availability
        cursor.execute(
            "SELECT available_copies FROM books WHERE book_id = ?", (book_id,)
        )
        book_row = cursor.fetchone()

        if not book_row or book_row[0] <= 0:
            return False, "Requested book is currently out of stock."

        # Compute issue and due dates (14 days standard duration)
        today = datetime.now()
        issue_date = today.strftime("%Y-%m-%d")
        due_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")

        # Execute issue transaction safely
        try:
            cursor.execute(
                """
                INSERT INTO issue_records (member_id, book_id, issue_date, due_date, status, fine_amount) 
                VALUES (?, ?, ?, ?, 'ISSUED', 0.0)
            """,
                (member_id, book_id, issue_date, due_date),
            )

            cursor.execute(
                "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
                (book_id,),
            )

            self.conn.commit()
            return True, f"Book issued successfully! Due date: {due_date}"
        except sqlite3.Error as e:
            self.conn.rollback()
            return False, f"Database error: {str(e)}"

    def get_borrowing_history(self, member_id):
        """Retrieves all past and active book borrowing records for a member."""
        cursor = self.conn.cursor()
        query = """
            SELECT record_id, member_id, book_id, issue_date, due_date, return_date, status, fine_amount 
            FROM issue_records 
            WHERE member_id = ? 
            ORDER BY issue_date DESC
        """
        cursor.execute(query, (member_id,))
        rows = cursor.fetchall()
        return [IssueRecord(*row) for row in rows]
