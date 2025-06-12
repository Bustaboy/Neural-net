# api/routes/auth.py
from fastapi import APIRouter, Depends
from flask_jwt_extended import create_access_token, get_jwt_identity
router = APIRouter(prefix="/auth")

@router.post("/refresh")
async def refresh_token():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return {"access_token": access_token}
