# api/routes/monitoring.py
from fastapi import APIRouter
from utils.health_check import HealthCheckSystem
router = APIRouter(prefix="/monitoring")

@router.get("/health")
async def health_check(checks: HealthCheckSystem = Depends()):
    return await checks.run_checks()
