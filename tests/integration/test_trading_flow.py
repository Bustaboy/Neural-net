# tests/integration/test_trading_flow.py
import pytest
from fastapi.testclient import TestClient
from api.app import create_app

def test_trading_flow():
    app = create_app()
    client = TestClient(app)
    # Register user, login, place trade
    response = client.post("/api/v1/trade", json={"symbol": "BTC/USDT", "side": "buy", "amount": 0.001})
    assert response.status_code == 200
