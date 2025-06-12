# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
