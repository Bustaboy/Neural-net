# api/routes/users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.auth import AuthManager
from core.database import EnhancedDatabaseManager

router = APIRouter(prefix="/users")
db_manager = EnhancedDatabaseManager()
auth_manager = AuthManager(app, db_manager)

class RegisterRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register_user(request: RegisterRequest):
    if db_manager.fetch_one("SELECT id FROM users WHERE email = ?", (request.email,)):
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed = auth_manager.hash_password(request.password)
    user_id = db_manager.execute(
        "INSERT INTO users (email, password) VALUES (?, ?) RETURNING id",
        (request.email, hashed)
    ).fetchone()[0]
    auth_manager.send_verification_email(user_id, request.email)
    return {"user_id": user_id}

@router.get("/verify")
async def verify_email(token: str):
    identity = get_jwt_identity(token)
    if not identity.get('verify_email'):
        raise HTTPException(status_code=400, detail="Invalid verification token")
    db_manager.execute(
        "UPDATE users SET verified = TRUE WHERE id = ?",
        (identity['user_id'],)
    )
    return {"status": "email_verified"}
