import asyncio
import base64
import binascii
import logging
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Query, Request

from routes import (admin_required, fail, get_controller, json_body, login_required,
                    ok, parse_float, parse_int, require_fields, staff_required)

router = APIRouter(prefix="/api/books")
MAX_COVER_BYTES = 2 * 1024 * 1024
BOOK_COVER_DIR = Path(__file__).resolve().parents[1] / "frontend" / "uploads" / "book-covers"
COVER_TYPES = {
    "image/jpeg": (".jpg", lambda content: content.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda content: content.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda content: content.startswith(b"RIFF") and content[8:12] == b"WEBP"),
}
COVER_LOOKUP_CACHE = {}
COVER_LOOKUP_CACHE_TTL = 60 * 60 * 24
NEGATIVE_COVER_CACHE_TTL = 60 * 15
GOOGLE_BOOKS_COOLDOWN_UNTIL = 0
OPEN_LIBRARY_COOLDOWN_UNTIL = 0
OPEN_LIBRARY_REQUEST_LOCK = asyncio.Lock()
OPEN_LIBRARY_LAST_REQUEST = 0
BOOK_TITLE_ALIASES = {
    "computer networking": "computer networking a top down approach",
    "a people s history": "a people s history of the united states",
    "discrete mathematics": "discrete mathematics and its applications",
}
logger = logging.getLogger(__name__)
cover_lookup_semaphore = asyncio.Semaphore(3)


def _normalized_cover_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()


def _normalized_book_title(value):
    title = _normalized_cover_text(value)
    publisher_prefix = "the pragmatic bookshelf "
    title = title.removeprefix(publisher_prefix).strip()
    return BOOK_TITLE_ALIASES.get(title, title)


def _normalized_isbn(value):
    return re.sub(r"[^0-9x]", "", str(value or "").lower())


def _valid_isbn(value):
    isbn = _normalized_isbn(value)
    if len(isbn) == 10:
        if not isbn[:9].isdigit() or not (isbn[9].isdigit() or isbn[9] == "x"):
            return False
        return sum((10 - index) * (10 if digit == "x" else int(digit))
                   for index, digit in enumerate(isbn)) % 11 == 0
    if len(isbn) == 13 and isbn.isdigit():
        return sum(int(digit) * (1 if index % 2 == 0 else 3)
                   for index, digit in enumerate(isbn)) % 10 == 0
    return False


def _open_library_query(params):
    if "isbn" in params:
        return f"isbn:{params['isbn']}"
    terms = []
    for field in ("title", "author"):
        if params.get(field):
            raw_value = str(params[field])
            if field == "title":
                raw_value = re.sub(
                    r"^The Pragmatic Bookshelf:\s*", "", raw_value, flags=re.IGNORECASE
                )
            value = raw_value.replace("\\", "\\\\").replace('"', '\\"')
            terms.append(f'{field}:"{value}"')
    return " AND ".join(terms)


async def _search_open_library(params):
    global OPEN_LIBRARY_COOLDOWN_UNTIL, OPEN_LIBRARY_LAST_REQUEST
    async with OPEN_LIBRARY_REQUEST_LOCK:
        now = time.monotonic()
        if OPEN_LIBRARY_COOLDOWN_UNTIL > now:
            raise httpx.ConnectError(
                "Open Library is in a temporary cooldown.",
                request=httpx.Request("GET", "https://openlibrary.org/search.json"),
            )
        async with httpx.AsyncClient(
            timeout=8.0,
            headers={"User-Agent": "NorthstarLibrary/1.0"},
            follow_redirects=True,
        ) as client:
            async def get_json(url, request_params=None):
                global OPEN_LIBRARY_COOLDOWN_UNTIL, OPEN_LIBRARY_LAST_REQUEST
                wait = 1.0 - (time.monotonic() - OPEN_LIBRARY_LAST_REQUEST)
                if wait > 0:
                    await asyncio.sleep(wait)
                response = await client.get(url, params=request_params)
                OPEN_LIBRARY_LAST_REQUEST = time.monotonic()
                if response.status_code == 429:
                    OPEN_LIBRARY_COOLDOWN_UNTIL = time.monotonic() + 60
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                result = response.json()
                return result if isinstance(result, dict) else None

            if params.get("isbn"):
                edition = await get_json(
                    f"https://openlibrary.org/isbn/{_normalized_isbn(params['isbn'])}.json"
                )
                if edition:
                    author_names = []
                    for author in edition.get("authors", []):
                        key = author.get("key") if isinstance(author, dict) else None
                        if not isinstance(key, str) or not key.startswith("/authors/"):
                            continue
                        author_doc = await get_json(f"https://openlibrary.org{key}.json")
                        if author_doc and author_doc.get("name"):
                            author_names.append(author_doc["name"])
                    isbn_13 = edition.get("isbn_13", [])
                    isbn_10 = edition.get("isbn_10", [])
                    identifiers = (
                        isbn_13 + isbn_10
                        if isinstance(isbn_13, list) and isinstance(isbn_10, list)
                        else []
                    )
                    covers = edition.get("covers", [])
                    if not isinstance(covers, list):
                        covers = []
                    return [{
                        "title": edition.get("full_title") or edition.get("title"),
                        "author_name": author_names,
                        "isbn": identifiers,
                        "cover_i": next(
                            (cover for cover in covers if isinstance(cover, int) and cover > 0),
                            None,
                        ),
                    }]

            response = await client.get(
                "https://openlibrary.org/search.json",
                params={
                    "q": _open_library_query(params),
                    "fields": "title,author_name,isbn,cover_i",
                    "limit": 100,
                },
            )
            OPEN_LIBRARY_LAST_REQUEST = time.monotonic()
            if response.status_code == 429:
                OPEN_LIBRARY_COOLDOWN_UNTIL = time.monotonic() + 60
            response.raise_for_status()
            result = response.json()
            documents = result.get("docs", []) if isinstance(result, dict) else []
            return documents if isinstance(documents, list) else []


async def _search_google_books(params):
    global GOOGLE_BOOKS_COOLDOWN_UNTIL
    if GOOGLE_BOOKS_COOLDOWN_UNTIL > time.monotonic():
        return []
    if "isbn" in params:
        query = f"isbn:{params['isbn']}"
    elif "author" in params:
        query = f'intitle:"{params["title"]}" inauthor:"{params["author"]}"'
    else:
        query = f'intitle:"{params["title"]}"'
    async with httpx.AsyncClient(
        timeout=5.0,
        headers={"User-Agent": "NorthstarLibrary/1.0"},
    ) as client:
        response = await client.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": query, "maxResults": 10, "printType": "books"},
        )
        if response.status_code == 429:
            GOOGLE_BOOKS_COOLDOWN_UNTIL = time.monotonic() + 60 * 60
            return []
        response.raise_for_status()
        result = response.json()
        items = result.get("items", []) if isinstance(result, dict) else []
        return items if isinstance(items, list) else []


def _google_cover_url(document):
    info = document.get("volumeInfo", {})
    images = info.get("imageLinks", {}) if isinstance(info, dict) else {}
    for key in ("extraLarge", "large", "medium", "thumbnail", "smallThumbnail"):
        raw_url = images.get(key) if isinstance(images, dict) else None
        if not raw_url:
            continue
        parsed = urlparse(raw_url)
        if parsed.hostname not in ("books.google.com", "books.googleusercontent.com"):
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        return urlunparse(("https", parsed.netloc, parsed.path, parsed.params, parsed.query, ""))
    return ""


def _open_library_cover_url(document):
    cover_id = document.get("cover_i")
    if isinstance(cover_id, int) and cover_id > 0:
        return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg?default=false"
    identifiers = document.get("isbn", [])
    for isbn in identifiers if isinstance(identifiers, list) else []:
        if _valid_isbn(isbn):
            return f"https://covers.openlibrary.org/b/isbn/{_normalized_isbn(isbn)}-L.jpg?default=false"
    return ""


def _book_title_matches(expected, actual, isbn_match=False):
    expected_title = _normalized_book_title(expected)
    actual_title = _normalized_book_title(actual)
    return bool(expected_title) and (
        expected_title == actual_title
        or (isbn_match and actual_title.startswith(f"{expected_title} "))
    )


def _same_author(expected, candidates):
    expected_text = re.sub(r"\s+et\s+al\.?$", "", str(expected or ""), flags=re.IGNORECASE)
    expected_names = re.split(r"\s+(?:and|&)\s+|,\s*(?=[A-Z])", expected_text, flags=re.IGNORECASE)
    if not isinstance(candidates, list):
        return False
    candidate_names = [str(candidate) for candidate in candidates]

    def author_matches(expected_name, candidate_name):
        expected_tokens = _normalized_cover_text(expected_name).split()
        candidate_tokens = _normalized_cover_text(candidate_name).split()
        if not expected_tokens or not candidate_tokens:
            return False
        if expected_tokens == candidate_tokens:
            return True
        if expected_tokens[-1] != candidate_tokens[-1]:
            return False
        if len(expected_tokens) == 1:
            return True
        return expected_tokens[0][0] == candidate_tokens[0][0]

    return bool(expected_names) and all(
        any(author_matches(name, candidate) for candidate in candidate_names)
        for name in expected_names if name.strip()
    )


def _book_match(document, title, author, isbn="", provider="openlibrary"):
    if provider == "google":
        info = document.get("volumeInfo", {})
        if not isinstance(info, dict):
            return False
        identifiers = info.get("industryIdentifiers", [])
        isbn_match = isinstance(identifiers, list) and any(
            isinstance(identifier, dict)
            and _normalized_isbn(identifier.get("identifier")) == _normalized_isbn(isbn)
            for identifier in identifiers
        ) if isbn else False
        return (
            _book_title_matches(title, info.get("title"), isbn_match=isbn_match)
            and _same_author(author, info.get("authors", []))
            and (not isbn or isbn_match)
        )
    if not isinstance(document, dict):
        return False
    identifiers = document.get("isbn", [])
    isbn_match = isinstance(identifiers, list) and any(
        _normalized_isbn(candidate) == _normalized_isbn(isbn) for candidate in identifiers
    ) if isbn else False
    return (
        _book_title_matches(title, document.get("title"), isbn_match=isbn_match)
        and _same_author(author, document.get("author_name", []))
        and (not isbn or isbn_match)
    )


async def _verify_cover_image(url):
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            current_url = url
            for _ in range(4):
                parsed = urlparse(current_url)
                host = (parsed.hostname or "").lower()
                if parsed.scheme != "https" or not (
                    host in ("books.google.com", "books.googleusercontent.com", "covers.openlibrary.org")
                    or host.endswith(".archive.org")
                    or host == "archive.org"
                ):
                    return False
                async with client.stream(
                    "GET",
                    current_url,
                    headers={"User-Agent": "NorthstarLibrary/1.0"},
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            return False
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code != 200 or not response.headers.get("content-type", "").lower().startswith("image/"):
                        return False
                    first_chunk = await anext(response.aiter_bytes(chunk_size=16))
                    return (
                        first_chunk.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF", b"GIF87a", b"GIF89a"))
                        and (not first_chunk.startswith(b"RIFF") or first_chunk[8:12] == b"WEBP")
                    )
            return False
    except (httpx.HTTPError, StopAsyncIteration):
        return False


async def _provider_documents(provider, params):
    try:
        if provider == "google":
            return await _search_google_books(params)
        return await _search_open_library(params)
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("%s book-cover lookup failed: %s", provider, type(error).__name__)
        return None


async def _find_verified_covers(isbn, title, author):
    sources = (
        ("google", _google_cover_url, "google"),
        ("openlibrary", _open_library_cover_url, "openlibrary"),
    )
    covers = []
    errors = False

    async def search_provider(provider, make_url, provider_name, query, match_isbn=""):
        nonlocal errors
        initial_count = len(covers)
        documents = await _provider_documents(provider, query)
        if documents is None:
            errors = True
            return False
        for document in documents:
            if not _book_match(document, title, author, match_isbn, provider_name):
                continue
            url = make_url(document)
            if not url or url in covers:
                continue
            if await _verify_cover_image(url):
                covers.append(url)
                if len(covers) >= 8:
                    break
        return len(covers) > initial_count

    if _valid_isbn(isbn):
        for provider, make_url, provider_name in sources:
            await search_provider(
                provider, make_url, provider_name, {"isbn": _normalized_isbn(isbn)}, isbn,
            )
            if len(covers) >= 8:
                return covers, errors

    for provider, make_url, provider_name in sources:
        if len(covers) >= 8:
            break
        existing_count = len(covers)
        await search_provider(
            provider,
            make_url,
            provider_name,
            {"title": title, "author": author},
        )
        if len(covers) == existing_count and len(covers) < 8:
            await search_provider(
                provider,
                make_url,
                provider_name,
                {"title": title},
            )

    return covers, errors


def valid_cover_url(value):
    if value in ("", None):
        return True
    if not isinstance(value, str) or len(value) > 2048:
        return False
    if value.startswith("/uploads/book-covers/"):
        filename = value.rsplit("/", 1)[-1]
        return bool(filename) and Path(filename).name == filename and Path(filename).suffix.lower() in {
            ".jpg", ".png", ".webp"
        }
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password


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


@router.get("/cover-lookup")
async def lookup_book_cover(
    request: Request,
    isbn: str = "",
    title: str = "",
    author: str = "",
    book_id: int = 0,
    exclude: list[str] = Query(default=[]),
    user: dict = Depends(login_required),
):
    controller = get_controller(request)
    if book_id:
        book = controller.get_book(book_id)
        if not book:
            return fail("Book not found.", 404)
        isbn = str(book.get("isbn") or "")
        title = str(book.get("title") or "")
        author = str(book.get("author") or "")
    else:
        book = None
    isbn = isbn.strip()
    title = title.strip()
    author = author.strip()
    if len(isbn) > 32 or len(title) > 300 or len(author) > 300:
        return fail("Book cover search details are too long.")
    if not title or not author:
        return fail("Book title and author are required for cover lookup.")
    if len(exclude) > 8 or any(len(url) > 2048 for url in exclude):
        return fail("Too many excluded cover URLs.")

    cache_key = f"{_normalized_isbn(isbn)}|{_normalized_cover_text(title)}|{_normalized_cover_text(author)}"
    cached = COVER_LOOKUP_CACHE.get(cache_key)
    if cached and cached[0] > time.monotonic():
        candidates = cached[1]
    else:
        async with cover_lookup_semaphore:
            candidates, lookup_failed = await _find_verified_covers(isbn, title, author)
        if not candidates and lookup_failed:
            return fail("Book cover lookup is temporarily unavailable.", 502)
        ttl = COVER_LOOKUP_CACHE_TTL if candidates else NEGATIVE_COVER_CACHE_TTL
        COVER_LOOKUP_CACHE[cache_key] = (time.monotonic() + ttl, candidates)
    if len(COVER_LOOKUP_CACHE) > 512:
        COVER_LOOKUP_CACHE.pop(next(iter(COVER_LOOKUP_CACHE)))

    excluded = set(exclude)
    candidates = [candidate for candidate in candidates if candidate not in excluded]
    if book and candidates:
        if not book.get("cover_url"):
            controller.book_dao.set_cover_if_missing(book["id"], candidates[0])
        elif book["cover_url"] in excluded:
            controller.book_dao.replace_cover_if_failed(book["id"], candidates[0], excluded)
    return ok(data={"cover_url": candidates[0] if candidates else "",
                    "cover_urls": candidates})


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
    if "cover_url" in data and not valid_cover_url(data["cover_url"]):
        return fail("Cover URL must be a secure HTTPS URL or a library-uploaded image.")

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
        cover_url=data.get("cover_url") or None,
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
    if "cover_url" in data and not valid_cover_url(data["cover_url"]):
        return fail("Cover URL must be a secure HTTPS URL or a library-uploaded image.")
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


@router.put("/{book_id}/cover")
async def upload_book_cover(book_id: int, request: Request, user: dict = Depends(staff_required)):
    controller = get_controller(request)
    book = controller.get_book(book_id)
    if not book:
        return fail("Book not found.", 404)
    data = await json_body(request)
    encoded = data.get("image")
    content_type = str(data.get("content_type", "")).lower()
    if not isinstance(encoded, str) or content_type not in COVER_TYPES:
        return fail("Upload a JPEG, PNG or WebP cover image.")
    if len(encoded) > ((MAX_COVER_BYTES + 2) // 3) * 4:
        return fail("Cover images must be 2 MB or smaller.", 413)
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return fail("The uploaded image data is invalid.")
    if not content or len(content) > MAX_COVER_BYTES:
        return fail("Cover images must be between 1 byte and 2 MB.", 413)
    extension, signature_check = COVER_TYPES[content_type]
    if not signature_check(content):
        return fail("The image content does not match its declared file type.")

    filename = f"{uuid4().hex}{extension}"
    cover_dir = BOOK_COVER_DIR
    cover_dir.mkdir(parents=True, exist_ok=True)
    image_path = cover_dir / filename
    image_path.write_bytes(content)
    cover_url = f"/uploads/book-covers/{filename}"
    success, message = controller.update_book(book_id, cover_url=cover_url)
    if not success:
        image_path.unlink()
        return fail(message, 409)

    previous_url = book.get("cover_url", "")
    if isinstance(previous_url, str) and previous_url.startswith("/uploads/book-covers/"):
        previous_path = (cover_dir / Path(previous_url).name).resolve()
        if previous_path.parent == cover_dir.resolve() and previous_path != image_path.resolve() and previous_path.exists():
            previous_path.unlink()
    return ok(data={"book": controller.get_book(book_id)}, message="Book cover updated.")


@router.delete("/{book_id}")
async def delete_book(book_id: int, request: Request, user: dict = Depends(admin_required)):
    success, message = get_controller(request).delete_book(book_id)
    if not success:
        return fail(message, 409)
    return ok(message=message)
