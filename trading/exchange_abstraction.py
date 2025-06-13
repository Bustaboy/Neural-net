from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import ccxt  # For Binance integration
import time
import logging
import web3  # For Web3 (install later)

logger = logging.getLogger(__name__)

def execute_trade(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Execute a trade on Binance or Web3 DEX with API limit respect."""
    global api_request_count, last_request_time
    api_request_count = getattr(execute_trade, 'api_request_count', 0)
    last_request_time = getattr(execute_trade, 'last_request_time', datetime.utcnow())

    try:
        current_time = datetime.utcnow()
        time_diff = (current_time - last_request_time).total_seconds()
        if time_diff > 1:
            api_request_count = 0
            last_request_time = current_time
        if api_request_count >= 10:
            logger.warning("API request limit reached, waiting...")
            time.sleep(1)
            api_request_count = 0
        api_request_count += 1
        setattr(execute_trade, 'api_request_count', api_request_count)
        setattr(execute_trade, 'last_request_time', last_request_time)

        user = db.execute(
            "SELECT exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
        if not user or not user.exchange_api_key or not user.exchange_secret:
            raise HTTPException(status_code=400, detail="No exchange API keys configured")

        exchange_api_key = user.exchange_api_key
        exchange_secret = user.exchange_secret

        testnet = False  # Placeholder; fetch from users table later

        # Binance execution (placeholder)
        exchange = ccxt.binance({
            'apiKey': exchange_api_key,
            'secret': exchange_secret,
            'enableRateLimit': True,
            'test': testnet
        })
        side = 'buy' if trade_type.lower() == 'buy' else 'sell'
        try:
            order = exchange.create_order(symbol, side.upper(), 'market', amount)
            return {"trade_id": order['id'], "status": "success"}
        except ccxt.ExchangeError as e:
            # Web3 fallback (placeholder)
            # w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_PROJECT_ID'))
            # contract = w3.eth.contract(address='YOUR_DEX_CONTRACT_ADDRESS', abi='YOUR_ABI')
            # tx_hash = contract.functions.swap(symbol, amount, side).transact({'from': w3.eth.accounts[0]})
            # return {"trade_id": tx_hash.hex(), "status": "success"}
            raise HTTPException(status_code=500, detail=f"Trade failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {e}")
