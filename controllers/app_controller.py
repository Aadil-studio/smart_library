from dao.book_dao import BookDAO
from dao.borrow_dao import BorrowDAO
from dao.notification_dao import NotificationDAO
from dao.reservation_dao import ReservationDAO
from dao.user_dao import UserDAO
from config.database import DatabaseConnection


class LibraryController:
    def __init__(self):
        # Guarantee database tables exist before any operation
        DatabaseConnection().init_tables()
        self.book_dao = BookDAO()
        self.user_dao = UserDAO()
        self.borrow_dao = BorrowDAO()
        self.reservation_dao = ReservationDAO()
        self.notification_dao = NotificationDAO()

    # --- User Auth & Management ---
    def register(self, user_id, name, email, password, role="student", department="", semester="", phone=""):
        return self.user_dao.register_user(user_id, name, email, password, role, department, semester, phone)

    # Alias for PyTest backward compatibility
    def register_user(self, name, user_id, password, role="student", email=""):
        if not email:
            email = f"{user_id}@library.com"
        self.user_dao.register_user(user_id, name, email, password, role)
        return user_id

    def login(self, credential, password):
        return self.user_dao.authenticate(credential, password)

    # Alias for PyTest backward compatibility
    def authenticate_user(self, credential, password):
        return self.user_dao.authenticate(credential, password)

    def generate_otp(self, email):
        """Returns (True, otp) or (False, message). Delivery (email/dev mode) is handled by the auth route."""
        otp, error = self.user_dao.generate_otp(email)
        if error:
            return False, error
        return True, otp

    def reset_password(self, email, otp, new_password):
        return self.user_dao.reset_password_with_otp(email, otp, new_password)

    def get_activity_logs(self):
        return self.user_dao.get_all_activity_logs()

    def get_users_by_role(self, role):
        return self.user_dao.get_users_by_role(role)

    def get_user(self, user_id):
        return self.user_dao.get_user_by_id(user_id)

    def update_profile(self, user_id, **fields):
        return self.user_dao.update_profile(user_id, **fields)

    def change_password(self, user_id, current_password, new_password):
        return self.user_dao.change_password(user_id, current_password, new_password)

    def set_user_status(self, user_id, status):
        self.user_dao.set_user_status(user_id, status)
        user = self.user_dao.get_user_by_id(user_id)
        self.user_dao.log_activity(user_id, user["name"] if user else user_id,
                                   "ACCOUNT_STATUS", f"Account set to {status}")
        return True, f"Account {status}."

    def get_preferences(self, user_id):
        return self.user_dao.get_preferences(user_id)

    def set_preferences(self, user_id, preferences):
        self.user_dao.set_preferences(user_id, preferences)
        return True, "Preferences saved."

    # --- Book Operations ---
    def register_book(self, title, author, isbn, category="General", publisher="", edition="",
                      publication_year=2026, total_copies=1, shelf_no="A1", description=""):
        return self.book_dao.add_book(title, author, isbn, category, publisher, edition,
                                      publication_year, total_copies, shelf_no, description)

    def list_books(self):
        return self.book_dao.get_all_books()

    def list_available_books(self):
        all_books = self.book_dao.get_all_books()
        return [book for book in all_books if book.get("is_available") == 1 and book.get("available_copies", 0) > 0]

    def search_books(self, query):
        return self.book_dao.search_books(query)

    def filter_books(self, search=None, category=None, author=None, availability=None):
        return self.book_dao.filter_books(search=search, category=category, author=author, availability=availability)

    def get_book(self, book_id):
        return self.book_dao.get_book_by_id(book_id)

    def update_book(self, book_id, **fields):
        return self.book_dao.update_book(book_id, **fields)

    def delete_book(self, book_id):
        return self.book_dao.delete_book(book_id)

    def get_categories(self):
        return self.book_dao.get_categories()

    def get_authors(self):
        return self.book_dao.get_authors()

    # --- Borrow / Return ---
    def issue_book(self, student_id, book_id, days=14):
        success, message, _transaction_id = self.borrow_dao.issue_book(student_id, book_id, days)
        if success:
            self.user_dao.log_activity(student_id, "", "BOOK_ISSUED", message)
        return book_id if success else None

    def return_book(self, transaction_id, user_role="student"):
        return self.borrow_dao.return_book(transaction_id, user_role)

    def list_transactions(self, student_id=None, status=None, search=None):
        return self.borrow_dao.list_transactions(student_id=student_id, status=status, search=search)

    def get_student_borrowed_books(self, student_id):
        return self.borrow_dao.get_student_borrowed_books(student_id)

    def get_student_active_loans(self, student_id):
        return self.borrow_dao.get_student_borrowed_books(student_id, active_only=True)

    def get_student_fines(self, student_id):
        return self.borrow_dao.get_student_fines(student_id)

    # --- Reservations ---
    def reserve_book(self, student_id, book_id):
        ok, message = self.reservation_dao.create(student_id, book_id)
        if ok:
            book = self.book_dao.get_book_by_id(book_id)
            self.user_dao.log_activity(student_id, "", "RESERVATION",
                                       f"Reserved '{book['title'] if book else book_id}'")
            self.notification_dao.notify(student_id, "Reservation submitted",
                                         f"Your reservation request for '{book['title'] if book else 'the book'}' "
                                         f"is pending approval.")
        return ok, message

    def list_reservations(self, student_id=None, status=None, search=None):
        return self.reservation_dao.list_reservations(student_id=student_id, status=status, search=search)

    def get_reservation(self, reservation_id):
        return self.reservation_dao.get_by_id(reservation_id)

    def update_reservation_status(self, reservation_id, action, acting_user_id):
        """action: approve | reject | fulfil | cancel"""
        reservation = self.reservation_dao.get_by_id(reservation_id)
        if not reservation:
            return False, "Reservation not found."
        status_map = {"approve": "approved", "reject": "rejected",
                      "fulfil": "fulfilled", "cancel": "rejected"}
        status = status_map.get(action)
        if not status:
            return False, "Invalid action."

        # Students may only cancel their own pending reservations
        if action == "cancel":
            if reservation["student_id"] != acting_user_id:
                return False, "You can only cancel your own reservations."
            if reservation["status"] != "pending":
                return False, "Only pending reservations can be cancelled."

        if action in ("approve", "reject") and reservation["status"] not in ("pending",):
            return False, f"Only pending reservations can be {action}d."
        if action == "fulfil" and reservation["status"] != "approved":
            return False, "Only approved reservations can be fulfilled."

        self.reservation_dao.update_status(reservation_id, status)
        titles = {"approve": "Reservation approved", "reject": "Reservation declined",
                  "fulfil": "Reservation fulfilled", "cancel": "Reservation cancelled"}
        self.notification_dao.notify(
            reservation["student_id"], titles[action],
            f"Your reservation for '{reservation['book_title']}' is now {status}.",
            ntype="reservation", ref_id=reservation_id,
        )
        return True, f"Reservation {status}."

    # --- Notifications ---
    def get_student_notifications(self, student_id):
        return self.notification_dao.get_user_notifications(student_id)

    def list_notifications(self, user_id, unread_only=False):
        return self.notification_dao.get_user_notifications(user_id, unread_only=unread_only)

    def unread_count(self, user_id):
        return self.notification_dao.unread_count(user_id)

    def mark_notification_read(self, notification_id, user_id):
        return self.notification_dao.mark_read(notification_id, user_id)

    def mark_all_notifications_read(self, user_id):
        self.notification_dao.mark_all_read(user_id)
        return True, "All notifications marked as read."

    # --- Overdue sweep (due-soon + overdue detection with de-duplicated notifications) ---
    def run_overdue_sweep(self):
        from datetime import datetime
        overdue = self.borrow_dao.get_overdue_transactions()
        marked = 0
        for trans in overdue:
            if trans["status"] == "issued":
                self.borrow_dao.detect_overdue()
                marked += 1
            days = trans.get("overdue_days") or 0
            self.notification_dao.notify(
                trans["student_id"], "Book overdue",
                f"'{trans['book_title']}' was due on {trans['due_date']} and is now {days} day(s) overdue. "
                f"Fine so far: Rs. {days * 10.0}. Please return it as soon as possible.",
                ntype="overdue", ref_id=trans["id"],
            )
        for trans in self.borrow_dao.get_due_soon_transactions(within_days=3):
            prefs = self.user_dao.get_preferences(trans["student_id"])
            if prefs.get("due_reminders", True) is False:
                continue
            self.notification_dao.notify(
                trans["student_id"], "Book due soon",
                f"'{trans['book_title']}' is due on {trans['due_date']}. Return or visit the library on time "
                f"to avoid a fine.",
                ntype="due_soon", ref_id=trans["id"],
            )
        return {"overdue_tracked": len(overdue), "newly_marked_overdue": marked,
                "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    # --- Dashboards & reports ---
    def get_student_dashboard(self, user):
        from datetime import datetime, timedelta
        student_id = user["user_id"]
        loans = self.borrow_dao.get_student_borrowed_books(student_id, active_only=True)
        history = self.borrow_dao.get_student_borrowed_books(student_id)
        now = datetime.now()
        due_soon = sum(1 for l in loans if l["status"] == "issued" and
                       datetime.strptime(l["due_date"], "%Y-%m-%d") <= now + timedelta(days=3))
        overdue = sum(1 for l in loans if l["status"] == "overdue" or
                      (l["status"] == "issued" and datetime.strptime(l["due_date"], "%Y-%m-%d") < now))
        return {
            "user": user,
            "stats": {
                "total_borrowed": len(history),
                "active_loans": len(loans),
                "due_soon": due_soon,
                "overdue": overdue,
                "unpaid_fines": self.borrow_dao.sum_unpaid_fines(student_id),
                "pending_reservations": len(self.reservation_dao.list_reservations(
                    student_id=student_id, status="pending")),
            },
            "active_loans": loans[:6],
            "history": history[:6],
            "notifications": self.notification_dao.get_user_notifications(student_id)[:6],
            "unread_notifications": self.notification_dao.unread_count(student_id),
        }

    def get_admin_dashboard(self):
        report = self.report_summary()
        return {
            "stats": report,
            "recent_borrows": self.borrow_dao.list_transactions()[:8],
            "recent_registrations": self.user_dao.get_users_by_role("student")[:6],
            "overdue": self.borrow_dao.get_overdue_transactions()[:10],
            "top_books": self.borrow_dao.most_borrowed_books(limit=6),
            "category_distribution": self.book_dao.category_distribution(),
            "recent_activity": self.user_dao.get_all_activity_logs(limit=10),
        }

    def report_summary(self):
        from services.report_service import ReportService
        return ReportService().summary()

    def borrowing_report(self, days=30):
        from services.report_service import ReportService
        return ReportService().borrowing_report(days=days)

    def calculate_member_fine(self, role: str, days_overdue: int) -> float:
        from services.fine_strategy import FineContext, StudentFineStrategy, FacultyFineStrategy
        context = FineContext()
        if role.lower() == "faculty":
            context.set_strategy(FacultyFineStrategy())
        else:
            context.set_strategy(StudentFineStrategy())
        return context.compute_fine(days_overdue)
