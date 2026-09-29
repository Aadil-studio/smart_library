from datetime import datetime

class User:

    def __init__(self, user_id, name, email, password, role_id=1):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.role_id = role_id  # 1 for Member, 2 for Admin / Librarian


class Member(User):

    def __init__(
        self,
        user_id,
        name,
        email,
        password,
        membership_date=None,
        max_books_allowed=3,
    ):
        super().__init__(user_id, name, email, password, role_id=1)
        self.membership_date = membership_date or datetime.now().strftime(
            "%Y-%m-%d"
        )
        self.max_books_allowed = max_books_allowed


class Book:

    def __init__(
        self,
        book_id,
        title,
        author,
        category,
        available_copies,
        total_copies,
    ):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.category = category
        self.available_copies = available_copies
        self.total_copies = total_copies


class IssueRecord:

    def __init__(
        self,
        record_id,
        member_id,
        book_id,
        issue_date,
        due_date,
        return_date=None,
        status="ISSUED",
    ):
        self.record_id = record_id
        self.member_id = member_id
        self.book_id = book_id
        self.issue_date = issue_date
        self.due_date = due_date
        self.return_date = return_date
        self.status = status  # ISSUED, RETURNED, REQUESTED
