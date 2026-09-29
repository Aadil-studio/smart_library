from dao.book_dao import BookDAO
from services.fine_strategy import FineContext, StudentFineStrategy, FacultyFineStrategy

class LibraryController:
    def __init__(self):
        self.book_dao = BookDAO()

    def register_book(self, title: str, author: str, isbn: str):
        return self.book_dao.add_book(title, author, isbn)

    def list_books(self):
        return self.book_dao.get_all_books()

    def calculate_member_fine(self, role: str, days: int) -> float:
        if role.lower() == 'student':
            context = FineContext(StudentFineStrategy())
        else:
            context = FineContext(FacultyFineStrategy())
        return context.compute_fine(days)