from config.database import DatabaseConnection

class BookDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            is_available BOOLEAN DEFAULT 1
        );
        """
        self.db.execute(query)
        self.db.commit()

    def add_book(self, title: str, author: str, isbn: str):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, isbn) VALUES (?, ?, ?)",
            (title, author, isbn)
        )
        self.db.commit()
        return cursor.lastrowid

    def get_all_books(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM books")
        return [dict(row) for row in cursor.fetchall()]