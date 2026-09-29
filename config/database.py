# config/database.py
import sqlite3

class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            # Database file local create ho jayegi
            cls._instance.connection = sqlite3.connect('library.db', check_same_thread=False)
            cls._instance.connection.row_factory = sqlite3.Row  # Dict format response ke liye
            print("[INFO] Database Connection Established (Singleton Instance)")
        return cls._instance

    def get_connection(self):
        return self.connection