import io
import logging
import re
import sqlite3
import uuid
import warnings
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from routes import (admin_required, fail, get_controller, json_body, librarian_required,
                    login_required, ok, password_problem, require_fields, valid_email)

router = APIRouter(prefix="/api/profile")
librarian_router = APIRouter(prefix="/api/librarian")
admin_profile_router = APIRouter(prefix="/api/admin")
AVATAR_DIRECTORY = Path(__file__).resolve().parents[1] / "frontend" / "uploads" / "avatars"
AVATAR_URL_PREFIX = "/uploads/avatars/"
MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_AVATAR_PIXELS = 25_000_000
AVATAR_FORMATS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}
logger = logging.getLogger(__name__)


def _process_avatar(data: bytes, filename: str) -> tuple[bytes, str]:
    extension = Path(filename or "").suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("Choose a JPG, JPEG, PNG, or WEBP image.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image_format = image.format
                if image_format not in AVATAR_FORMATS or extension not in AVATAR_FORMATS[image_format]:
                    raise ValueError("The file extension does not match a supported image format.")
                if image.width * image.height > MAX_AVATAR_PIXELS:
                    raise ValueError("Image dimensions are too large.")
                image.verify()

            with Image.open(io.BytesIO(data)) as image:
                image = ImageOps.exif_transpose(image)
                image.load()
                if image_format == "JPEG":
                    if "A" in image.getbands():
                        rgba = image.convert("RGBA")
                        background = Image.new("RGB", rgba.size, (255, 255, 255))
                        background.paste(rgba, mask=rgba.getchannel("A"))
                        image = background
                    else:
                        image = image.convert("RGB")
                elif image_format == "PNG":
                    if image.mode not in ("RGB", "RGBA"):
                        image = image.convert("RGBA")
                else:
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

                output = io.BytesIO()
                save_options = {"format": image_format}
                if image_format == "JPEG":
                    save_options.update({"quality": 88, "optimize": True, "progressive": True})
                elif image_format == "PNG":
                    save_options["optimize"] = True
                else:
                    save_options.update({"quality": 88, "method": 4})
                image.save(output, **save_options)
    except ValueError:
        raise
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise ValueError("The uploaded file is not a valid supported image.") from error

    processed = output.getvalue()
    extension = ".jpg" if image_format == "JPEG" else f".{image_format.lower()}"
    return processed, extension


def _store_avatar_file(user_id: str, data: bytes, extension: str) -> tuple[Path, str]:
    AVATAR_DIRECTORY.mkdir(parents=True, exist_ok=True)
    safe_user_id = re.sub(r"[^A-Za-z0-9_-]", "_", user_id)[:64] or "user"
    filename = f"user_{safe_user_id}_{uuid.uuid4().hex}{extension}"
    path = AVATAR_DIRECTORY / filename
    try:
        with path.open("xb") as avatar_file:
            avatar_file.write(data)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path, f"{AVATAR_URL_PREFIX}{filename}"


def _delete_avatar_file(avatar_url: str | None) -> bool:
    if not isinstance(avatar_url, str) or not avatar_url.startswith(AVATAR_URL_PREFIX):
        return True
    filename = Path(avatar_url).name
    if not filename or filename in {".", ".."}:
        return True
    avatar_path = AVATAR_DIRECTORY / filename
    if avatar_path.resolve().parent != AVATAR_DIRECTORY.resolve():
        return True
    try:
        avatar_path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove replaced profile avatar: %s", avatar_path)
        return False
    return True


@admin_profile_router.get("/profile")
async def get_admin_profile(request: Request, user: dict = Depends(admin_required)):
    profile = get_controller(request).get_user(user["user_id"])
    if not profile:
        return fail("Administrator account not found.", 404)
    return ok(data={"profile": {
        "user_id": profile["user_id"],
        "name": profile["name"],
        "email": profile["email"],
        "role": profile["role"],
        "avatar_url": profile.get("avatar_url"),
    }})


@admin_profile_router.put("/profile")
async def update_admin_profile(request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "name", "email")
    if error:
        return fail(error)
    if not isinstance(data["name"], str) or not isinstance(data["email"], str):
        return fail("'name' and 'email' must be strings.")

    name = data["name"].strip()
    email = data["email"].strip().lower()
    if not name:
        return fail("'name' cannot be empty.")
    if not valid_email(email):
        return fail("Please enter a valid email address.")

    current = controller.get_user(user["user_id"])
    if not current:
        return fail("Administrator account not found.", 404)
    if email != current["email"].lower() and controller.user_dao.email_exists(email):
        return fail("That email address is already in use by another account.", 409)

    success, message = controller.update_profile(user["user_id"], name=name, email=email)
    if not success:
        return fail(message, 409)
    refreshed = controller.get_user(user["user_id"])
    request.session["user"] = refreshed
    return ok(data={"profile": {
        "user_id": refreshed["user_id"],
        "name": refreshed["name"],
        "email": refreshed["email"],
        "role": refreshed["role"],
        "avatar_url": refreshed.get("avatar_url"),
    }}, message=message)


@admin_profile_router.post("/profile/avatar")
async def upload_admin_profile_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(admin_required),
):
    contents = await file.read(MAX_AVATAR_BYTES + 1)
    if not contents:
        return fail("Choose an image to upload.")
    if len(contents) > MAX_AVATAR_BYTES:
        return fail("Profile photos must be 2 MB or smaller.", 413)
    try:
        processed, extension = _process_avatar(contents, file.filename or "")
    except ValueError as error:
        return fail(str(error))

    controller = get_controller(request)
    current = controller.get_user(user["user_id"])
    if not current:
        return fail("Administrator account not found.", 404)
    _, avatar_url = _store_avatar_file(user["user_id"], processed, extension)
    try:
        updated = controller.user_dao.update_avatar_url(user["user_id"], avatar_url)
    except sqlite3.Error:
        _delete_avatar_file(avatar_url)
        raise
    if not updated:
        _delete_avatar_file(avatar_url)
        return fail("Administrator account not found.", 404)

    request.session["user"] = updated
    previous_removed = _delete_avatar_file(current.get("avatar_url"))
    message = "Administrator photo updated."
    if not previous_removed:
        message += " The previous photo could not be removed from storage."
    return ok(data={"profile": updated}, message=message)


@admin_profile_router.delete("/profile/avatar")
async def remove_admin_profile_avatar(request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    current = controller.get_user(user["user_id"])
    if not current:
        return fail("Administrator account not found.", 404)
    updated = controller.user_dao.update_avatar_url(user["user_id"], None)
    if not updated:
        return fail("Administrator account not found.", 404)

    request.session["user"] = updated
    previous_removed = _delete_avatar_file(current.get("avatar_url"))
    message = "Administrator photo removed."
    if not previous_removed:
        message += " The previous photo could not be removed from storage."
    return ok(data={"profile": updated}, message=message)


@admin_profile_router.post("/change-password")
async def change_admin_password(request: Request, user: dict = Depends(admin_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "current_password", "new_password", "confirm_password")
    if error:
        return fail(error)
    if not all(isinstance(data[field], str) for field in ("current_password", "new_password", "confirm_password")):
        return fail("Password fields must be strings.")
    if data["new_password"] != data["confirm_password"]:
        return fail("New passwords do not match.")
    if data["current_password"] == data["new_password"]:
        return fail("The new password must be different from the current one.")
    if problem := password_problem(data["new_password"]):
        return fail(problem)

    success, message = controller.change_password(
        user["user_id"], data["current_password"], data["new_password"]
    )
    if not success:
        return fail(message, 403)
    return ok(message=message)


@librarian_router.get("/profile")
async def get_librarian_profile(request: Request, user: dict = Depends(librarian_required)):
    profile = get_controller(request).get_user(user["user_id"])
    if not profile:
        return fail("Librarian account not found.", 404)
    return ok(data={"profile": {
        "user_id": profile["user_id"],
        "name": profile["name"],
        "email": profile["email"],
        "role": profile["role"],
    }})


@librarian_router.put("/profile")
async def update_librarian_profile(request: Request, user: dict = Depends(librarian_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "name", "email")
    if error:
        return fail(error)
    if not isinstance(data["name"], str) or not isinstance(data["email"], str):
        return fail("'name' and 'email' must be strings.")

    name = data["name"].strip()
    email = data["email"].strip().lower()
    if not name:
        return fail("'name' cannot be empty.")
    if not valid_email(email):
        return fail("Please enter a valid email address.")

    current = controller.get_user(user["user_id"])
    if not current:
        return fail("Librarian account not found.", 404)
    if email != current["email"].lower() and controller.user_dao.email_exists(email):
        return fail("That email address is already in use by another account.", 409)

    success, message = controller.update_profile(user["user_id"], name=name, email=email)
    if not success:
        return fail(message, 409)
    refreshed = controller.get_user(user["user_id"])
    request.session["user"] = refreshed
    return ok(data={"profile": {
        "user_id": refreshed["user_id"],
        "name": refreshed["name"],
        "email": refreshed["email"],
        "role": refreshed["role"],
    }}, message=message)


@librarian_router.post("/change-password")
async def change_librarian_password(request: Request, user: dict = Depends(librarian_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "current_password", "new_password", "confirm_password")
    if error:
        return fail(error)
    if not all(isinstance(data[field], str) for field in ("current_password", "new_password", "confirm_password")):
        return fail("Password fields must be strings.")
    if data["new_password"] != data["confirm_password"]:
        return fail("New passwords do not match.")
    if len(data["new_password"]) < 6:
        return fail("New password must be at least 6 characters long.")
    if data["current_password"] == data["new_password"]:
        return fail("The new password must be different from the current one.")

    success, message = controller.change_password(
        user["user_id"], data["current_password"], data["new_password"]
    )
    if not success:
        return fail(message, 403)
    return ok(message=message)


@router.get("")
async def get_profile(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    return ok(data={
        "profile": controller.get_user(user["user_id"]),
        "preferences": controller.get_preferences(user["user_id"]),
        "stats": {
            "borrowed_total": len(controller.borrow_dao.get_student_borrowed_books(user["user_id"])),
            "active_loans": len(controller.borrow_dao.get_student_borrowed_books(user["user_id"], active_only=True)),
        },
    })


@router.put("")
async def update_profile(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
    if not str(data.get("name", "")).strip():
        return fail("'name' cannot be empty.")
    success, message = controller.update_profile(
        user["user_id"],
        name=str(data.get("name")).strip(),
        phone=str(data.get("phone", "") or "").strip(),
        department=str(data.get("department", "") or "").strip(),
        semester=str(data.get("semester", "") or "").strip(),
    )
    if not success:
        return fail(message, 409)
    refreshed = controller.get_user(user["user_id"])
    request.session["user"] = refreshed
    return ok(data={"profile": refreshed}, message=message)


@router.post("/avatar")
async def upload_profile_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(login_required),
):
    if user.get("role") not in {"student", "librarian"}:
        return fail("Only students and librarians can update a profile photo.", 403)
    contents = await file.read(MAX_AVATAR_BYTES + 1)
    if not contents:
        return fail("Choose an image to upload.")
    if len(contents) > MAX_AVATAR_BYTES:
        return fail("Profile photos must be 2 MB or smaller.", 413)
    try:
        processed, extension = _process_avatar(contents, file.filename or "")
    except ValueError as error:
        return fail(str(error))

    controller = get_controller(request)
    current = controller.get_user(user["user_id"])
    if not current:
        return fail("Account not found.", 404)
    avatar_path, avatar_url = _store_avatar_file(user["user_id"], processed, extension)
    try:
        updated = controller.user_dao.update_avatar_url(user["user_id"], avatar_url)
    except sqlite3.Error:
        _delete_avatar_file(avatar_url)
        raise
    if not updated:
        _delete_avatar_file(avatar_url)
        return fail("Account not found.", 404)

    request.session["user"] = updated
    previous_removed = _delete_avatar_file(current.get("avatar_url"))
    message = "Profile photo updated."
    if not previous_removed:
        message += " The previous photo could not be removed from storage."
    return ok(data={"profile": updated}, message=message)


@router.delete("/avatar")
async def remove_profile_avatar(request: Request, user: dict = Depends(login_required)):
    if user.get("role") not in {"student", "librarian"}:
        return fail("Only students and librarians can update a profile photo.", 403)
    controller = get_controller(request)
    current = controller.get_user(user["user_id"])
    if not current:
        return fail("Account not found.", 404)
    updated = controller.user_dao.update_avatar_url(user["user_id"], None)
    if not updated:
        return fail("Account not found.", 404)

    request.session["user"] = updated
    previous_removed = _delete_avatar_file(current.get("avatar_url"))
    message = "Profile photo removed."
    if not previous_removed:
        message += " The previous photo could not be removed from storage."
    return ok(data={"profile": updated}, message=message)


@router.post("/password")
@router.put("/password")
async def change_password(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
    error = require_fields(data, "current_password", "new_password", "confirm_password")
    if error:
        return fail(error)
    if data["new_password"] != data["confirm_password"]:
        return fail("New passwords do not match.")
    if data["current_password"] == data["new_password"]:
        return fail("The new password must be different from the current one.")
    if problem := password_problem(data["new_password"]):
        return fail(problem)
    success, message = controller.change_password(user["user_id"], data["current_password"], data["new_password"])
    if not success:
        return fail(message, 403)
    return ok(message=message)


@router.put("/preferences")
async def update_preferences(request: Request, user: dict = Depends(login_required)):
    controller = get_controller(request)
    data = await json_body(request)
    current = controller.get_preferences(user["user_id"])
    if "due_reminders" in data:
        current["due_reminders"] = bool(data["due_reminders"])
    success, message = controller.set_preferences(user["user_id"], current)
    return ok(data={"preferences": controller.get_preferences(user["user_id"])}, message=message)
