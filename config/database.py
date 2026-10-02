import sqlite3
import os

class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            # LIBRARY_DB_PATH env override keeps tests/isolated runs off the real database
            db_path = os.environ.get("LIBRARY_DB_PATH", "library.db")
            # Timeout set to 30 seconds to prevent locks
            cls._instance.connection = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            cls._instance.connection.row_factory = sqlite3.Row
            
            # Enable WAL Mode (Write-Ahead Logging) to fix OperationalError: database is locked
            cursor = cls._instance.connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            
            cls._instance.init_tables()
            print("[INFO] Database Connection Established with WAL Mode (Singleton Instance)")
        return cls._instance

    def get_connection(self):
        return self.connection

    def init_tables(self):
        cursor = self.connection.cursor()
        
        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'librarian', 'student')) NOT NULL,
            department TEXT,
            semester TEXT,
            phone TEXT,
            otp TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Categories Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        """)

        # Authors Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        """)

        # Books Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT,
            publisher TEXT,
            edition TEXT,
            publication_year INTEGER,
            total_copies INTEGER DEFAULT 1,
            available_copies INTEGER DEFAULT 1,
            shelf_no TEXT,
            is_available BOOLEAN DEFAULT 1
        );
        """)

        # Transactions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date DATE DEFAULT CURRENT_DATE,
            due_date DATE NOT NULL,
            return_date DATE,
            fine_amount REAL DEFAULT 0.0,
            status TEXT CHECK(status IN ('issued', 'returned', 'overdue')) DEFAULT 'issued',
            FOREIGN KEY (student_id) REFERENCES users(user_id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
        """)

        # Reservations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'fulfilled')) DEFAULT 'pending',
            FOREIGN KEY (student_id) REFERENCES users(user_id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
        """)

        # Fines Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            transaction_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT CHECK(status IN ('unpaid', 'paid')) DEFAULT 'unpaid',
            payment_date DATE,
            FOREIGN KEY (student_id) REFERENCES users(user_id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        );
        """)

        # Notifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Activity Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_name TEXT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Password Reset OTPs — hashed codes with expiry (never store raw OTP)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)

        self._migrate_columns(cursor)
        self._create_indexes(cursor)

        self.connection.commit()

    def _add_column_if_missing(self, cursor, table, column, definition):
        """Additive migration helper — existing data and columns are never touched."""
        existing = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _migrate_columns(self, cursor):
        # Extend existing tables without destroying data (SQLite ALTER ADD COLUMN is additive)
        self._add_column_if_missing(cursor, "users", "preferences", "TEXT")
        self._add_column_if_missing(cursor, "books", "description", "TEXT DEFAULT ''")
        self._add_column_if_missing(cursor, "books", "status", "TEXT DEFAULT 'active'")
        self._add_column_if_missing(cursor, "books", "created_at", "TIMESTAMP")
        self._add_column_if_missing(cursor, "notifications", "title", "TEXT DEFAULT ''")
        self._add_column_if_missing(cursor, "notifications", "type", "TEXT")
        self._add_column_if_missing(cursor, "notifications", "ref_id", "INTEGER")
        # Backfill created_at for pre-existing book rows
        cursor.execute("UPDATE books SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    def _create_indexes(self, cursor):
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)",
            "CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)",
            "CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_student ON transactions(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_book ON transactions(book_id)",
            "CREATE INDEX IF NOT EXISTS idx_reservations_student ON reservations(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)",
            "CREATE INDEX IF NOT EXISTS idx_fines_student ON fines(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_otps_user ON password_reset_otps(user_id)",
        ]
        for statement in indexes:
            cursor.execute(statement)

    @staticmethod
    def reset_instance():
        """Used by tests to swap the singleton for an in-memory database."""
        DatabaseConnection._instance = None