"""Idempotently add the Northstar frontend catalog to the active SQLite database."""
from controllers.app_controller import LibraryController

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


def main():
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
