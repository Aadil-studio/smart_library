from config.database import DatabaseConnection


class ReservationDAO:
    def __init__(self):
        self.db = DatabaseConnection().get_connection()

    def create(self, student_id, book_id):
        cursor = self.db.cursor()
        duplicate = cursor.execute(
            "SELECT 1 FROM reservations WHERE student_id=? AND book_id=? AND status IN ('pending', 'approved')",
            (student_id, book_id),
        ).fetchone()
        if duplicate:
            return False, "You already have an active reservation for this book."
        cursor.execute(
            "INSERT INTO reservations (student_id, book_id, status) VALUES (?, ?, 'pending')",
            (student_id, book_id),
        )
        self.db.commit()
        return True, "Reservation request submitted. The library staff will review it."

    def get_by_id(self, reservation_id):
        cursor = self.db.cursor()
        row = cursor.execute(
            """SELECT r.*, b.title AS book_title, b.author AS book_author,
                      u.name AS student_name, u.user_id AS student_ref
               FROM reservations r
               JOIN books b ON r.book_id = b.id
               LEFT JOIN users u ON u.user_id = r.student_id
               WHERE r.id=?""",
            (reservation_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_reservations(self, student_id=None, status=None, search=None):
        cursor = self.db.cursor()
        clauses, params = [], []
        if student_id:
            clauses.append("r.student_id = ?")
            params.append(student_id)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        if search:
            q = f"%{search}%"
            clauses.append("(b.title LIKE ? OR b.author LIKE ? OR u.name LIKE ? OR r.student_id LIKE ?)")
            params += [q, q, q, q]
        sql = """SELECT r.*, b.title AS book_title, b.author AS book_author, b.isbn AS book_isbn,
                        u.name AS student_name
                 FROM reservations r
                 JOIN books b ON r.book_id = b.id
                 LEFT JOIN users u ON u.user_id = r.student_id"""
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY r.id DESC"
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_status(self, reservation_id, status):
        cursor = self.db.cursor()
        cursor.execute("UPDATE reservations SET status=? WHERE id=?", (status, reservation_id))
        self.db.commit()
        return cursor.rowcount > 0

    def count_reservations(self, status=None):
        cursor = self.db.cursor()
        if status:
            row = cursor.execute("SELECT COUNT(*) FROM reservations WHERE status=?", (status,)).fetchone()
        else:
            row = cursor.execute("SELECT COUNT(*) FROM reservations").fetchone()
        return row[0]

    def get_student_reservations(self, student_id: str):
        return self.list_reservations(student_id=student_id)
