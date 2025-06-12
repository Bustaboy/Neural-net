# api/routes/market.py
from fastapi import APIRouter, Depends
from flask_jwt_extended import get_jwt_identity
from market.data_fetcher import MarketDataFetcher

router = APIRouter(prefix="/market")
fetcher = MarketDataFetcher()

@router.get("/data/{symbol}")
async def get_market_data(symbol: str, user_id: int = Depends(get_jwt_identity)):
    try:
        data = await fetcher.fetch_ticker(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
