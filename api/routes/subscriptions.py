# api/routes/subscriptions.py
from fastapi import APIRouter, Depends, HTTPException
import stripe
from flask_jwt_extended import get_jwt_identity
from config import ConfigManager
from core.database import EnhancedDatabaseManager

router = APIRouter(prefix="/subscriptions")
db_manager = EnhancedDatabaseManager()
stripe.api_key = ConfigManager.get_config("services.stripe.secret_key")

class SubscriptionRequest(BaseModel):
    tier: str

@router.post("/create")
async def create_subscription(request: SubscriptionRequest, user_id: int = Depends(get_jwt_identity)):
    try:
        plan = ConfigManager.get_config(f"subscriptions.tiers.{request.tier}.price_id")
        subscription = stripe.Subscription.create(
            customer=f"cus_{user_id}",
            items=[{"price": plan}]
        )
        db_manager.execute(
            "UPDATE users SET subscription_tier = ? WHERE id = ?",
            (request.tier, user_id)
        )
        return {"subscription_id": subscription.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
