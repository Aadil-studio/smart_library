from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

router = APIRouter()

# --- Pydantic Schemas (mirroring the Flask JSON body checks) ---
class RegisterRequest(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=20)
    full_name: str = Field(..., min_length=3)
    email: EmailStr
    password: str
    confirm_password: str
    department: Optional[str] = ""
    semester: Optional[str] = ""
    phone: Optional[str] = ""

class LoginRequest(BaseModel):
    credential: str
    password: str
    remember: bool = False

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

# --- Helper to get the controller (replace with your actual dependency) ---
def get_controller():
    # In a real app, this would return your LibraryController instance
    from controllers.app_controller import LibraryController
    return LibraryController()

# --- Routes ---
@router.post("/register")
async def register(data: RegisterRequest, request: Request):
    controller = get_controller()

    # Password match check (same as Flask route)
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # Password strength check (delegate to your existing helper)
    # if problem := password_problem(data.password):
    #     raise HTTPException(status_code=400, detail=problem)

    success, message = controller.register(
        student_id=data.student_id.strip(),
        full_name=data.full_name.strip(),
        email=data.email.lower(),
        password=data.password,
        role="student",
        department=data.department.strip(),
        semester=data.semester.strip(),
        phone=data.phone.strip(),
    )
    if not success:
        raise HTTPException(status_code=409, detail=message)

    # Log the user in (store in session)
    user = controller.login(data.email.lower(), data.password)
    request.session["user"] = user

    # Send welcome notification (same as Flask)
    controller.notification_dao.notify(
        user["user_id"],
        "Welcome to Smart Library",
        f"Hi {user['name']}, your account was created successfully.",
        ntype="account",
    )
    return {"data": {"user": user}, "message": "Registration successful."}

@router.post("/login")
async def login(data: LoginRequest, request: Request):
    controller = get_controller()
    user = controller.login(data.credential.strip(), data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or inactive account.",
        )
    request.session["user"] = user
    if data.remember:
        request.session["permanent"] = True  # SessionMiddleware handles max_age
    return {"data": {"user": user}, "message": f"Welcome back, {user['name']}!"}

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "You have been signed out."}

@router.get("/me")
async def me(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"data": {"user": user}}
