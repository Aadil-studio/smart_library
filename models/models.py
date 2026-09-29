class Book:
    def __init__(self, book_id: int, title: str, author: str, isbn: str, is_available: bool = True):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.isbn = isbn
        self.is_available = is_available

class User:
    def __init__(self, user_id: int, name: str, role: str):
        self.user_id = user_id
        self.name = name
        self.role = role  # Student, Faculty, Librarian