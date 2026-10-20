from fastapi import FastAPI, Request, Depends, HTTPException
#pip install websockets
# run fast api websocket uvicorn main:app --reload --ws none
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from routes import auth_routes, book_routes
import os

app = FastAPI(title="Smart Library API (FastAPI adaptation)")

# Session middleware (similar to Flask's session)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-only-insecure-key-change-in-env"),
    session_cookie="smart_library_session",
    max_age=30 * 24 * 60 * 60,  # 30 days (matches REMEMBER_ME_DAYS)
)

# Mount the static frontend (identical to the original repo)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Include API routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(book_routes.router, prefix="/api/books", tags=["Books"])

# Optional: catch-all for SPA-style routing (or just serve index.html)
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("frontend/index.html") as f:
        return f.read()

