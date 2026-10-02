"""Library borrowing workflows."""

from datetime import date, timedelta

from dao.loan_dao import LoanDAO


class BorrowService:
	def __init__(self, loan_dao=None):
		self.loan_dao = loan_dao or LoanDAO()

	def issue_book(self, user_id: int, book_id: int, loan_days: int = 14):
		if loan_days < 1 or loan_days > 90:
			raise ValueError("Loan period must be between 1 and 90 days")
		due_at = (date.today() + timedelta(days=loan_days)).isoformat()
		return self.loan_dao.issue_book(user_id, book_id, due_at)

	def return_book(self, loan_id: int):
		return self.loan_dao.return_book(loan_id)
