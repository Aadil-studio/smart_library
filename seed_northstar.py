"""Idempotently add the Northstar frontend catalog to the active SQLite database."""
import argparse
import os
import sqlite3

ADDITIONAL_BOOKS = (
    ("Clean Architecture", "Robert C. Martin", "9780134494166", "Software Engineering", 3),
    ("Designing Data-Intensive Applications", "Martin Kleppmann", "9781449373320", "Databases", 2),
    ("Refactoring", "Martin Fowler", "9780134757599", "Software Engineering", 2),
    ("Deep Learning", "Ian Goodfellow", "9780262035613", "Artificial Intelligence", 2),
    ("Hands-On Machine Learning", "Aurélien Géron", "9781098125974", "Artificial Intelligence", 3),
    ("You Don't Know JS Yet", "Kyle Simpson", "9781091210099", "Programming", 4),
    ("Eloquent JavaScript", "Marijn Haverbeke", "9781593279509", "Programming", 3),
    ("Fluent Python", "Luciano Ramalho", "9781492056355", "Programming", 2),
    ("System Design Interview", "Alex Xu", "9781736049112", "Software Engineering", 3),
    ("Computer Organization and Design", "David A. Patterson", "9780124077263", "Computer Science", 2),
    ("Modern Operating Systems", "Andrew S. Tanenbaum", "9780133591620", "Operating Systems", 2),
    ("Cryptography and Network Security", "William Stallings", "9780134444284", "Cybersecurity", 3),
    ("The Web Application Hacker's Handbook", "Dafydd Stuttard", "9781118026472", "Cybersecurity", 2),
    ("Head First Design Patterns", "Eric Freeman", "9781492078005", "Software Engineering", 3),
    ("Structure and Interpretation of Computer Programs", "Harold Abelson", "9780262510875", "Computer Science", 2),
    ("TCP/IP Illustrated, Vol. 1", "W. Richard Stevens", "9780321336316", "Networking", 2),
    ("Code: The Hidden Language", "Charles Petzold", "9780137909100", "Computer Science", 4),
    ("Grokking Algorithms", "Aditya Bhargava", "9781617292231", "Computer Science", 3),
    ("The Phoenix Project", "Gene Kim, Kevin Behr, George Spafford", "9780988262591", "Software Engineering", 2),
    ("Database Internals", "Alex Petrov", "9781492040347", "Databases", 2),
)

COVER_URL_OVERRIDES = {
    "9780988262591": "https://covers.openlibrary.org/b/isbn/9781942788294-L.jpg",
}

RAW = (
    "Atomic Habits|James Clear|Self-Help|2018;"
    "Deep Work|Cal Newport|Self-Help|2016;"
    "The Power of Habit|Charles Duhigg|Self-Help|2012;"
    "Mindset|Carol Dweck|Self-Help|2006;"
    "Grit|Angela Duckworth|Self-Help|2016;"
    "Man's Search for Meaning|Viktor Frankl|Philosophy|1946;"
    "Meditations|Marcus Aurelius|Philosophy|180;"
    "The Republic|Plato|Philosophy|375;"
    "Thus Spoke Zarathustra|F. Nietzsche|Philosophy|1883;"
    "The Art of War|Sun Tzu|Philosophy|500;"
    "Sapiens|Yuval N. Harari|History|2011;"
    "Guns, Germs, and Steel|Jared Diamond|History|1997;"
    "The Silk Roads|Peter Frankopan|History|2015;"
    "A People's History|Howard Zinn|History|1980;"
    "The Rise and Fall of the Third Reich|W. Shirer|History|1960;"
    "SPQR|Mary Beard|History|2015;"
    "A Brief History of Time|Stephen Hawking|Science|1988;"
    "Cosmos|Carl Sagan|Science|1980;"
    "The Selfish Gene|Richard Dawkins|Science|1976;"
    "Silent Spring|Rachel Carson|Science|1962;"
    "The Gene|S. Mukherjee|Science|2016;"
    "Astrophysics for People in a Hurry|N. deGrasse Tyson|Science|2017;"
    "Clean Code|Robert C. Martin|Technology|2008;"
    "The Pragmatic Programmer|Hunt & Thomas|Technology|1999;"
    "Introduction to Algorithms|Cormen et al.|Technology|1990;"
    "Designing Data-Intensive Applications|M. Kleppmann|Technology|2017;"
    "Python Crash Course|Eric Matthes|Technology|2015;"
    "Artificial Intelligence: A Modern Approach|Russell & Norvig|Technology|1995;"
    "Zero to One|Peter Thiel|Business|2014;"
    "The Lean Startup|Eric Ries|Business|2011;"
    "Good to Great|Jim Collins|Business|2001;"
    "Rich Dad Poor Dad|Robert Kiyosaki|Business|1997;"
    "Thinking, Fast and Slow|D. Kahneman|Business|2011;"
    "The Intelligent Investor|Benjamin Graham|Business|1949;"
    "1984|George Orwell|Fiction|1949;"
    "To Kill a Mockingbird|Harper Lee|Fiction|1960;"
    "Pride and Prejudice|Jane Austen|Fiction|1813;"
    "The Great Gatsby|F. Scott Fitzgerald|Fiction|1925;"
    "One Hundred Years of Solitude|G. G. Marquez|Fiction|1967;"
    "The Alchemist|Paulo Coelho|Fiction|1988;"
    "The Kite Runner|Khaled Hosseini|Fiction|2003;"
    "Crime and Punishment|F. Dostoevsky|Fiction|1866;"
    "Brave New World|Aldous Huxley|Fiction|1932;"
    "The Catcher in the Rye|J. D. Salinger|Fiction|1951;"
    "The Hobbit|J. R. R. Tolkien|Fantasy|1937;"
    "The Fellowship of the Ring|J. R. R. Tolkien|Fantasy|1954;"
    "Harry Potter and the Philosopher's Stone|J. K. Rowling|Fantasy|1997;"
    "A Game of Thrones|G. R. R. Martin|Fantasy|1996;"
    "The Name of the Wind|Patrick Rothfuss|Fantasy|2007;"
    "Dune|Frank Herbert|Fantasy|1965;"
    "The Lion, the Witch and the Wardrobe|C. S. Lewis|Fantasy|1950;"
    "Mistborn|Brandon Sanderson|Fantasy|2006;"
    "Neuromancer|William Gibson|Fantasy|1984;"
    "The Left Hand of Darkness|U. K. Le Guin|Fantasy|1969;"
    "Foundation|Isaac Asimov|Fantasy|1951;"
    "Principles of Economics|N. Gregory Mankiw|Business|1997;"
    "Psychology|David Myers|Science|1986;"
    "Calculus|James Stewart|Science|1987;"
    "Organic Chemistry|Paula Bruice|Science|1995;"
    "Discrete Mathematics|Kenneth Rosen|Technology|1988;"
    "Database System Concepts|Silberschatz|Technology|1986;"
    "Operating System Concepts|A. Silberschatz|Technology|1982;"
    "Computer Networking|Kurose & Ross|Technology|2000"
)


def normalized_isbn(value):
    return "".join(character for character in value.casefold() if character.isalnum())


def seed_additional_books():
    db_path = os.environ.get("LIBRARY_DB_PATH", "library.db")
    connection = sqlite3.connect(db_path, timeout=30)
    added = 0
    skipped = 0

    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute("SELECT title, isbn FROM books").fetchall()
        titles = {row[0].strip().casefold() for row in existing if row[0]}
        isbns = {normalized_isbn(row[1]) for row in existing if row[1]}

        for index, (title, author, isbn, category, copies) in enumerate(ADDITIONAL_BOOKS, start=1):
            title_key = title.strip().casefold()
            isbn_key = normalized_isbn(isbn)
            cover_url = COVER_URL_OVERRIDES.get(
                isbn,
                f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg",
            )
            if title_key in titles or isbn_key in isbns:
                if isbn in COVER_URL_OVERRIDES:
                    connection.execute(
                        """UPDATE books SET cover_url=?
                           WHERE title=? AND isbn=? AND COALESCE(cover_url, '')<>?""",
                        (cover_url, title, isbn, cover_url),
                    )
                skipped += 1
                continue

            cursor = connection.execute(
                """INSERT OR IGNORE INTO books (
                       isbn, title, author, category, publisher, edition, publication_year,
                       total_copies, available_copies, shelf_no, is_available, description,
                       status, created_at, fee, cover_url
                   ) VALUES (?, ?, ?, ?, '', '', NULL, ?, ?, ?, 1, '', 'active',
                             CURRENT_TIMESTAMP, 4000, ?)""",
                (
                    isbn,
                    title,
                    author,
                    category,
                    copies,
                    copies,
                    f"N-{(index - 1) // 10 + 3}",
                    cover_url,
                ),
            )
            if cursor.rowcount:
                titles.add(title_key)
                isbns.add(isbn_key)
                added += 1
            else:
                skipped += 1

        connection.commit()
        total = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        print(f"Additional catalog seed complete: added {added} books, skipped {skipped} duplicates; {total} books total.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="Seed the Northstar Library catalog.")
    parser.add_argument(
        "--additional-books",
        action="store_true",
        help="Insert only the 20 approved additional titles without altering the existing catalog.",
    )
    args = parser.parse_args()
    if args.additional_books:
        seed_additional_books()
        return

    from controllers.app_controller import LibraryController

    controller = LibraryController()
    existing = {
        (book["title"].casefold(), book["author"].casefold(), (book.get("category") or "").casefold())
        for book in controller.book_dao.get_all_books()
    }
    added = 0

    for index, item in enumerate(RAW.split(";"), start=1):
        title, author, category, year = item.split("|")
        key = (title.casefold(), author.casefold(), category.casefold())
        if key in existing:
            continue

        isbn = f"NS-CAT-{index:04d}"
        suffix = 1
        while controller.book_dao.get_book_by_isbn(isbn):
            isbn = f"NS-CAT-{index:04d}-{suffix}"
            suffix += 1
        copies = 2 + ((index - 1) * 7) % 4
        book_id = controller.register_book(
            title=title,
            author=author,
            isbn=isbn,
            category=category,
            publication_year=int(year),
            total_copies=copies,
            shelf_no=f"N-{(index - 1) // 10 + 1}",
        )
        if not book_id:
            raise RuntimeError(f"Unable to seed catalog entry: {title} ({isbn})")
        existing.add(key)
        added += 1

    total = len(controller.book_dao.get_all_books())
    print(f"Northstar catalog ready: added {added} books; {total} books total.")
    if total < 60:
        raise RuntimeError(f"The catalog has {total} books; at least 60 are required.")


if __name__ == "__main__":
    main()
