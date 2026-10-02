from flask import Blueprint, request

from routes import (admin_required, fail, get_controller, json_body, login_required,
                    ok, parse_int, require_fields, staff_required)

book_bp = Blueprint("books", __name__, url_prefix="/api/books")


@book_bp.get("")
@login_required
def list_books():
    controller = get_controller()
    books = controller.filter_books(
        search=request.args.get("q", "").strip() or None,
        category=request.args.get("category", "").strip() or None,
        author=request.args.get("author", "").strip() or None,
        availability=request.args.get("availability", "").strip() or None,
    )
    return ok(data={"books": books, "categories": controller.get_categories(),
                    "authors": controller.get_authors()})


@book_bp.get("/<int:book_id>")
@login_required
def get_book(book_id):
    book = get_controller().get_book(book_id)
    if not book:
        return fail("Book not found.", 404)
    return ok(data={"book": book})


@book_bp.post("")
@staff_required
def add_book():
    controller = get_controller()
    data = json_body()
    error = require_fields(data, "title", "author", "isbn")
    if error:
        return fail(error)

    copies, error = parse_int(data.get("total_copies", 1), "total_copies", minimum=1, maximum=999)
    if error:
        return fail(error)
    year, error = parse_int(data.get("publication_year", 2026), "publication_year", minimum=1000, maximum=2100)
    if error:
        return fail(error)

    book_id = controller.register_book(
        title=str(data["title"]).strip(),
        author=str(data["author"]).strip(),
        isbn=str(data["isbn"]).strip(),
        category=str(data.get("category", "") or "General").strip() or "General",
        publisher=str(data.get("publisher", "") or "").strip(),
        edition=str(data.get("edition", "") or "").strip(),
        publication_year=year,
        total_copies=copies,
        shelf_no=str(data.get("shelf_no", "") or "A1").strip() or "A1",
        description=str(data.get("description", "") or "").strip(),
    )
    if not book_id:
        return fail("A book with this ISBN already exists.", 409)
    book = controller.get_book(book_id)
    return ok(data={"book": book}, message=f"'{book['title']}' added to the catalog.")


@book_bp.put("/<int:book_id>")
@staff_required
def update_book(book_id):
    controller = get_controller()
    if not controller.get_book(book_id):
        return fail("Book not found.", 404)
    data = json_body()
    if "total_copies" in data:
        copies, error = parse_int(data.get("total_copies"), "total_copies", minimum=1, maximum=999)
        if error:
            return fail(error)
        data["total_copies"] = copies
    if "publication_year" in data and data["publication_year"] not in ("", None):
        year, error = parse_int(data.get("publication_year"), "publication_year", minimum=1000, maximum=2100)
        if error:
            return fail(error)
        data["publication_year"] = year
    if "status" in data and data["status"] not in ("active", "inactive"):
        return fail("Status must be 'active' or 'inactive'.")
    success, message = controller.update_book(book_id, **data)
    if not success:
        return fail(message, 409)
    return ok(data={"book": controller.get_book(book_id)}, message=message)


@book_bp.delete("/<int:book_id>")
@admin_required
def delete_book(book_id):
    success, message = get_controller().delete_book(book_id)
    if not success:
        return fail(message, 409)
    return ok(message=message)
