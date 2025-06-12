# api/routes/alerts.py
from fastapi import APIRouter
from utils.alert_manager import AlertManager
router = APIRouter(prefix="/alerts")

@router.post("/create")
async def create_alert(config: Dict, manager: AlertManager = Depends()):
    manager.create_alert_rule(user_id=1, alert_config=config)
    return {"status": "alert_created"}
