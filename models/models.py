from datetime import datetime, timedelta


class User:
    """Base User class representing shared authentication and identity attributes."""

    def __init__(self, user_id, name, email, password, role_id=1):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.role_id = role_id  # 1: Member, 2: Librarian/Admin


class Member(User):
    """Member entity representing Role 1 in the Smart Library System."""

    def __init__(
        self,
        user_id,
        name,
        email,
        password,
        membership_date=None,
        max_books_allowed=3,
        fine_balance=0.0,
    ):
        super().__init__(user_id, name, email, password, role_id=1)
        self.membership_date = membership_date or datetime.now().strftime(
            "%Y-%m-%d"
        )
        self.max_books_allowed = max_books_allowed
        self.fine_balance = fine_balance

    def to_dict(self):
        """Converts member object to dictionary format."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role_id": self.role_id,
            "membership_date": self.membership_date,
            "max_books_allowed": self.max_books_allowed,
            "fine_balance": self.fine_balance,
        }


class Book:
    """Book entity representing catalog items."""

    def __init__(
        self,
        book_id,
        title,
        author,
        isbn,
        category,
        available_copies,
        total_copies,
    ):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.isbn = isbn
        self.category = category
        self.available_copies = available_copies
        self.total_copies = total_copies


class IssueRecord:
    """Represents book borrowings and issue history for a Member."""

    def __init__(
        self,
        record_id,
        member_id,
        book_id,
        issue_date,
        due_date,
        return_date=None,
        status="ISSUED",
        fine_amount=0.0,
    ):
        self.record_id = record_id
        self.member_id = member_id
        self.book_id = book_id
        self.issue_date = issue_date
        self.due_date = due_date
        self.return_date = return_date
        self.status = status  # 'ISSUED', 'RETURNED', 'OVERDUE'
        self.fine_amount = fine_amount
