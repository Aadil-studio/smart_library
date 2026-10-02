import sqlite3

import pytest

from config.database import DatabaseConnection
from controllers.app_controller import LibraryController


@pytest.fixture
def controller(monkeypatch):
    instance = object.__new__(DatabaseConnection)
    instance.connection = sqlite3.connect(":memory:", check_same_thread=False)
    instance.connection.row_factory = sqlite3.Row
    instance.connection.execute("PRAGMA foreign_keys = ON")
    monkeypatch.setattr(DatabaseConnection, "_instance", instance)
    yield LibraryController()
    instance.connection.close()


def test_issue_and_return_book_updates_availability(controller):
    member_id = controller.register_user("Test Member", "test-member", "password123")
    book_id = controller.register_book("Test Title", "Test Author", "test-isbn")

    loan_id = controller.issue_book(member_id, book_id)

    assert loan_id is not None
    assert controller.list_available_books() == []
    assert controller.issue_book(member_id, book_id) is None
    assert controller.return_book(loan_id)
    assert len(controller.list_available_books()) == 1


def test_user_password_is_verified(controller):
    controller.register_user("Test Member", "test-member", "password123", "student")

    assert controller.authenticate_user("test-member", "password123")["role"] == "student"
    assert controller.authenticate_user("test-member", "wrong-password") is None