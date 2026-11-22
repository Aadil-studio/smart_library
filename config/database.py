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
            cursor.execute("PRAGMA foreign_keys=ON;")
            
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
            status TEXT CHECK(status IN ('unpaid', 'paid', 'waived')) DEFAULT 'unpaid',
            payment_date DATE,
            collected_by TEXT,
            waived_by TEXT,
            waive_reason TEXT,
            waived_at TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(user_id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        );
        """)

        # Book Fees — uploaded by the ADMIN only (Rs. 4000 default). Publishing to the
        # student portal is automatic; only the admin can mark a fee paid, and borrowing
        # is blocked while a fee is unpaid.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            transaction_id INTEGER,
            book_id INTEGER,
            amount REAL NOT NULL,
            status TEXT CHECK(status IN ('unpaid', 'paid')) DEFAULT 'unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_date DATE,
            collected_by TEXT,
            uploaded_by TEXT,
            FOREIGN KEY (student_id) REFERENCES users(user_id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, book_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_loan_renewals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL UNIQUE,
            student_id TEXT NOT NULL,
            original_due_date DATE NOT NULL,
            renewed_due_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES transactions(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # Migrate a pre-existing book_fees table that required a book/transaction and
        # had no uploaded_by column (SQLite CHECK/NOT NULL constraints cannot be
        # altered in place, so the table is rebuilt and the data preserved).
        existing_book_fees = [row[1] for row in cursor.execute("PRAGMA table_info(book_fees)").fetchall()]
        if existing_book_fees and "uploaded_by" not in existing_book_fees:
            cursor.execute("""
            CREATE TABLE book_fees_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                transaction_id INTEGER,
                book_id INTEGER,
                amount REAL NOT NULL,
                status TEXT CHECK(status IN ('unpaid', 'paid')) DEFAULT 'unpaid',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_date DATE,
                collected_by TEXT,
                uploaded_by TEXT,
                FOREIGN KEY (student_id) REFERENCES users(user_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            );
            """)
            cursor.execute("""
                INSERT INTO book_fees_new (id, student_id, transaction_id, book_id, amount,
                                           status, created_at, payment_date, collected_by)
                SELECT id, student_id, transaction_id, book_id, amount,
                       status, created_at, payment_date, collected_by FROM book_fees
            """)
            cursor.execute("DROP TABLE book_fees")
            cursor.execute("ALTER TABLE book_fees_new RENAME TO book_fees")

        # Migrate a pre-existing fines table that lacks the payment/waiver columns
        # and the 'waived' status (SQLite CHECK constraints cannot be altered in place).
        existing_fines = [row[1] for row in cursor.execute("PRAGMA table_info(fines)").fetchall()]
        if "collected_by" not in existing_fines:
            cursor.execute("""
            CREATE TABLE fines_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                transaction_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT CHECK(status IN ('unpaid', 'paid', 'waived')) DEFAULT 'unpaid',
                payment_date DATE,
                collected_by TEXT,
                waived_by TEXT,
                waive_reason TEXT,
                waived_at TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users(user_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            );
            """)
            cursor.execute("""
                INSERT INTO fines_new (id, student_id, transaction_id, amount, status, payment_date)
                SELECT id, student_id, transaction_id, amount, status, payment_date FROM fines
            """)
            cursor.execute("DROP TABLE fines")
            cursor.execute("ALTER TABLE fines_new RENAME TO fines")

        # Library Settings (key/value, edited by the administrator)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        for key, value in (
            ("library_name", "Smart Library"),
            ("loan_period_days", "14"),
            ("fine_per_day", "10"),
            ("due_soon_days", "3"),
            ("book_fee", os.environ.get("BOOK_FEE", "4000")),
        ):
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

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
            verified INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_request_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_key TEXT NOT NULL,
            ip_key TEXT NOT NULL,
            requested_at REAL NOT NULL
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
        self._add_column_if_missing(cursor, "users", "avatar_url", "TEXT")
        self._add_column_if_missing(cursor, "books", "description", "TEXT DEFAULT ''")
        self._add_column_if_missing(cursor, "books", "status", "TEXT DEFAULT 'active'")
        self._add_column_if_missing(cursor, "books", "created_at", "TIMESTAMP")
        self._add_column_if_missing(cursor, "books", "fee", "REAL")
        self._add_column_if_missing(cursor, "books", "cover_url", "TEXT")
        self._add_column_if_missing(cursor, "notifications", "title", "TEXT DEFAULT ''")
        self._add_column_if_missing(cursor, "notifications", "type", "TEXT")
        self._add_column_if_missing(cursor, "notifications", "ref_id", "INTEGER")
        self._add_column_if_missing(cursor, "fines", "collected_by", "TEXT")
        self._add_column_if_missing(cursor, "password_reset_otps", "verified", "INTEGER DEFAULT 0")
        self._add_column_if_missing(cursor, "password_reset_otps", "attempts", "INTEGER DEFAULT 0")
        # Every book carries the library book fee (Rs. 4000 unless overridden per title)
        cursor.execute("UPDATE books SET fee = ? WHERE fee IS NULL",
                       (os.environ.get("BOOK_FEE", "4000"),))
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
            "CREATE INDEX IF NOT EXISTS idx_book_fees_student ON book_fees(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_book_fees_txn ON book_fees(transaction_id)",
            "CREATE INDEX IF NOT EXISTS idx_otps_user ON password_reset_otps(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_otp_request_email ON otp_request_limits(email_key, requested_at)",
            "CREATE INDEX IF NOT EXISTS idx_otp_request_ip ON otp_request_limits(ip_key, requested_at)",
        ]
        for statement in indexes:
            cursor.execute(statement)

    @staticmethod
    def reset_instance():
        """Used by tests to swap the singleton for an in-memory database."""
        DatabaseConnection._instance = None
