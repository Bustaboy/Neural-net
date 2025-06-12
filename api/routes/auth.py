# api/routes/auth.py
from fastapi import APIRouter, HTTPException, FastAPI
from pydantic import BaseModel
from flask_jwt_extended import get_jwt_identity
from api.auth import AuthManager
from core.database import EnhancedDatabaseManager

router = APIRouter(prefix="/auth")
app = FastAPI()  # Temporary for Flask compatibility; replace with your app
auth_manager = AuthManager(app, EnhancedDatabaseManager())

class LoginRequest(BaseModel):
    email: str
    password: str

class Verify2FARequest(BaseModel):
    user_id: int
    code: str

@router.post("/login")
async def login(request: LoginRequest):
    user = auth_manager.db_manager.fetch_one(
        "SELECT id, password, subscription_tier, two_factor_secret FROM users WHERE email = ?",
        (request.email,)
    )
    if not user or not auth_manager.verify_password(request.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user['two_factor_secret']:
        return {"status": "2fa_required", "user_id": user['id']}
    tokens = auth_manager.generate_tokens(user['id'], subscription_tier=user['subscription_tier'])
    return tokens

@router.post("/refresh")
async def refresh_token():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return {"access_token": access_token}

@router.post("/verify-2fa")
async def verify_2fa(request: Verify2FARequest):
    if not auth_manager.verify_2fa(request.user_id, request.code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    user = auth_manager.db_manager.fetch_one(
        "SELECT id, subscription_tier FROM users WHERE id = ?", (request.user_id,)
    )
    tokens = auth_manager.generate_tokens(user['id'], subscription_tier=user['subscription_tier'])
    return tokens
