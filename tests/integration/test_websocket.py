# tests/integration/test_websocket.py
import pytest
from socketio import Client
from api.app import create_app

def test_websocket_notification():
    app = create_app()
    client = Client()
    client.connect('http://localhost:5000')
    client.emit('model_retrained', {'event': 'test'})
    # Assert notification received
    client.disconnect()
