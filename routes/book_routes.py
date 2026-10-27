from fastapi import APIRouter, Depends, Request

from routes import (admin_required, fail, get_controller, json_body, login_required,
                    ok, parse_float, parse_int, require_fields, staff_required)

router = APIRouter(prefix="/api/books")


@router.get("")
async def list_books(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    sort = request.query_params.get("sort", "").strip() or None
    if sort and sort not in ("newest", "oldest", "title", "title-desc", "author", "year", "availability"):
        return fail("Invalid sort option.")
    books = controller.filter_books(
        search=request.query_params.get("q", "").strip() or None,
        category=request.query_params.get("category", "").strip() or None,
        author=request.query_params.get("author", "").strip() or None,
        availability=request.query_params.get("availability", "").strip() or None,
        sort=sort,
    )
    return ok(data={"books": books, "categories": controller.get_categories(),
                    "authors": controller.get_authors()})


@router.get("/{book_id}")
async def get_book(book_id: int, request: Request, user: dict = Depends(login_required)):
    book = get_controller(request).get_book(book_id)
    if not book:
        return fail("Book not found.", 404)
    return ok(data={"book": book})


@router.post("")
async def add_book(request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "title", "author", "isbn")
    if error:
        return fail(error)

    copies, error = parse_int(data.get("total_copies", 1), "total_copies", minimum=1, maximum=999)
    if error:
        return fail(error)
    year, error = parse_int(data.get("publication_year", 2026), "publication_year", minimum=1000, maximum=2100)
    if error:
        return fail(error)
    fee, error = parse_float(data, "fee", minimum=0, maximum=100000)
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
        fee=fee,
    )
    if not book_id:
        return fail("A book with this ISBN already exists.", 409)
    book = controller.get_book(book_id)
    return ok(data={"book": book}, message=f"'{book['title']}' added to the catalog.")


@router.put("/{book_id}")
async def update_book(book_id: int, request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    if not controller.get_book(book_id):
        return fail("Book not found.", 404)
    data = await json_body(request)
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
    if "fee" in data:
        fee, error = parse_float(data, "fee", minimum=0, maximum=100000)
        if error:
            return fail(error)
        data["fee"] = fee
    if "status" in data and data["status"] not in ("active", "inactive"):
        return fail("Status must be 'active' or 'inactive'.")
    success, message = controller.update_book(book_id, **data)
    if not success:
        return fail(message, 409)
    return ok(data={"book": controller.get_book(book_id)}, message=message)


@router.delete("/{book_id}")
async def delete_book(book_id: int, request: Request, user: dict = Depends(admin_required)):
    success, message = get_controller(request).delete_book(book_id)
    if not success:
        return fail(message, 409)
    return ok(message=message)
