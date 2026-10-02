"""Optional development seed data — creates demo accounts and a sample catalog.

    python seed_demo.py

DEVELOPMENT ONLY: the demo passwords below are well-known defaults for local
demonstration. Change them (or delete the seeded accounts) before any real use.
Existing data is never overwritten; seeding skips what already exists.
"""
from controllers.app_controller import LibraryController

DEMO_BOOKS = [
    ("Clean Code", "Robert C. Martin", "978-0132350884", "Software Engineering", "Prentice Hall", 2008, 4, "A1"),
    ("The Pragmatic Programmer", "Andrew Hunt", "978-0135957059", "Software Engineering", "Addison-Wesley", 2019, 3, "A1"),
    ("Introduction to Algorithms", "Thomas H. Cormen", "978-0262046305", "Computer Science", "MIT Press", 2022, 3, "A2"),
    ("Database System Concepts", "Abraham Silberschatz", "978-0078022159", "Computer Science", "McGraw-Hill", 2019, 2, "A2"),
    ("Computer Networking: A Top-Down Approach", "James F. Kurose", "978-0136629226", "Networking", "Pearson", 2021, 2, "B1"),
    ("Artificial Intelligence: A Modern Approach", "Stuart Russell", "978-0134610993", "Artificial Intelligence", "Pearson", 2020, 2, "B2"),
    ("Operating System Concepts", "Abraham Silberschatz", "978-1119800361", "Operating Systems", "Wiley", 2018, 2, "B3"),
    ("The Pragmatic Bookshelf: Python Crash Course", "Eric Matthes", "978-1593279288", "Programming", "No Starch Press", 2019, 3, "C1"),
    ("Design Patterns", "Erich Gamma", "978-0201633610", "Software Engineering", "Addison-Wesley", 1994, 1, "C2"),
    ("Data Structures and Algorithms in Python", "Goodrich & Tamassia", "978-1118290279", "Computer Science", "Wiley", 2013, 2, "C3"),
]

DEMO_STUDENTS = [
    ("STU-1001", "Alex Morgan", "student@smartlibrary.local", "Student@123", "Computer Science", "6", "0300-1112223"),
    ("STU-1002", "Sara Khan", "sara.khan@smartlibrary.local", "Student@123", "Software Engineering", "4", "0300-4445556"),
]

DEMO_LIBRARIAN = ("LIB-2001", "Library Desk", "librarian@smartlibrary.local", "Librarian@123")


def main():
    controller = LibraryController()
    print("Seeding development demo data (existing records are skipped)...")

    # Admin is created automatically by the app if missing — but ensure one exists here too
    if not controller.user_dao.get_users_by_role("admin"):
        controller.register("ADMIN001", "System Administrator", "admin@smartlibrary.local",
                            "Admin@123", role="admin", department="IT")
        print("  admin    admin@smartlibrary.local  / Admin@123")

    for user_id, name, email, password, dept, semester, phone in DEMO_STUDENTS:
        ok, msg = controller.register(user_id, name, email, password, role="student",
                                      department=dept, semester=semester, phone=phone)
        if ok:
            print(f"  student  {email} / {password}")
        else:
            print(f"  student  {email}: {msg}")

    user_id, name, email, password = DEMO_LIBRARIAN
    ok, msg = controller.register(user_id, name, email, password, role="librarian", department="Library")
    print(f"  librarian {email} / {password}" if ok else f"  librarian {email}: {msg}")

    added = 0
    for title, author, isbn, category, publisher, year, copies, shelf in DEMO_BOOKS:
        if controller.register_book(title, author, isbn, category=category, publisher=publisher,
                                    publication_year=year, total_copies=copies, shelf_no=shelf,
                                    description=f"{title} — part of the seeded development catalog."):
            added += 1
    print(f"  books    {added} new (of {len(DEMO_BOOKS)})")

    print("\nAll demo passwords are DEVELOPMENT ONLY. Change them for anything real.")


if __name__ == "__main__":
    main()
