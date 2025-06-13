from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db
import hashlib

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Log in a user and return a token."""
    user = db.execute(
        "SELECT id, username, password_hash FROM users WHERE username = :username AND password_hash = :password",
        {"username": request.username, "password": hash_password(request.password)}
    ).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": f"token_{user.id}", "user_id": user.id}

@router.post("/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    existing_user = db.execute(
        "SELECT id FROM users WHERE username = :username",
        {"username": request.username}
    ).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    db.execute(
        "INSERT INTO users (username, password_hash) VALUES (:username, :password)",
        {"username": request.username, "password": hash_password(request.password)}
    )
    db.commit()
    user = db.execute(
        "SELECT id FROM users WHERE username = :username",
        {"username": request.username}
    ).fetchone()
    return {"access_token": f"token_{user.id}", "user_id": user.id}
