# api/routes/portfolio.py
from fastapi import APIRouter, Depends
from trading.position_manager import PositionManager
from flask_jwt_extended import get_jwt_identity
from core.database import EnhancedDatabaseManager

router = APIRouter(prefix="/portfolio")
db_manager = EnhancedDatabaseManager()
position_manager = PositionManager(db_manager)

@router.get("/")
async def get_portfolio(user_id: int = Depends(get_jwt_identity)):
    positions = position_manager.get_open_positions(user_id)
    return {"positions": positions}
