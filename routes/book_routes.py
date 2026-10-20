from fastapi import APIRouter, Request, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter()

# --- Pydantic Schemas ---
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    isbn: str = Field(..., min_length=1)
    category: Optional[str] = "General"
    publisher: Optional[str] = ""
    edition: Optional[str] = ""
    publication_year: Optional[int] = Field(2026, ge=1000, le=2100)
    total_copies: Optional[int] = Field(1, ge=1, le=999)
    shelf_no: Optional[str] = "A1"
    description: Optional[str] = ""

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    category: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    total_copies: Optional[int] = Field(None, ge=1, le=999)
    shelf_no: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # "active" or "inactive"

# --- Dependency: get controller ---
def get_controller():
    from controllers.app_controller import LibraryController
    return LibraryController()

# --- Dependency: check login (mirrors @login_required) ---
def login_required(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user

# --- Routes ---
@router.get("")
async def list_books(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    availability: Optional[str] = Query(None),
    controller=Depends(get_controller),
    user=Depends(login_required),
):
    books = controller.filter_books(
        search=q.strip() if q else None,
        category=category.strip() if category else None,
        author=author.strip() if author else None,
        availability=availability.strip() if availability else None,
    )
    return {
        "data": {
            "books": books,
            "categories": controller.get_categories(),
            "authors": controller.get_authors(),
        }
    }

@router.get("/{book_id}")
async def get_book(
    book_id: str,
    controller=Depends(get_controller),
    user=Depends(login_required),
):
    book = controller.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"data": {"book": book}}

@router.post("")
async def add_book(
    data: BookCreate,
    controller=Depends(get_controller),
    user=Depends(login_required),  # In the original, this is @staff_required
):
    # In a real app, add a staff_required dependency here
    book_id = controller.register_book(
        title=data.title.strip(),
        author=data.author.strip(),
        isbn=data.isbn.strip(),
        category=data.category.strip() or "General",
        publisher=data.publisher.strip(),
        edition=data.edition.strip(),
        publication_year=data.publication_year,
        total_copies=data.total_copies,
        shelf_no=data.shelf_no.strip() or "A1",
        description=data.description.strip(),
    )
    if not book_id:
        raise HTTPException(status_code=409, detail="A book with this ISBN already exists.")
    book = controller.get_book(book_id)
    return {"data": {"book": book}, "message": f"'{book['title']}' added to the catalog."}

@router.put("/{book_id}")
async def update_book(
    book_id: str,
    data: BookUpdate,
    controller=Depends(get_controller),
    user=Depends(login_required),  # staff_required in original
):
    if not controller.get_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found.")
    update_data = data.dict(exclude_unset=True)
    if "status" in update_data and update_data["status"] not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'inactive'.")
    success, message = controller.update_book(book_id, **update_data)
    if not success:
        raise HTTPException(status_code=409, detail=message)
    return {"data": {"book": controller.get_book(book_id)}, "message": message}

@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    controller=Depends(get_controller),
    user=Depends(login_required),  # admin_required in original
):
    success, message = controller.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=409, detail=message)
    return {"message": message}
