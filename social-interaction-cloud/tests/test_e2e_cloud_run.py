import os
import pytest
import requests
import socketio

# The live URL will be passed in via environment variable
CLOUD_RUN_URL = os.getenv("CLOUD_RUN_URL")

@pytest.mark.skipif(not CLOUD_RUN_URL, reason="CLOUD_RUN_URL environment variable is not set")
def test_e2e_http_endpoint():
    """Test that the Cloud Run container is serving the basic HTTP files."""
    response = requests.get(f"{CLOUD_RUN_URL}/welcome.html")
    assert response.status_code == 200
    assert "html" in response.text.lower()

@pytest.mark.skipif(not CLOUD_RUN_URL, reason="CLOUD_RUN_URL environment variable is not set")
def test_e2e_websocket_connection():
    """Test that WebSocket connections can be established with the deployed container."""
    sio = socketio.Client()
    connected = False

    @sio.event
    def connect():
        nonlocal connected
        connected = True

    # Connect to the cloud run URL
    sio.connect(CLOUD_RUN_URL)
    
    # Wait briefly for connection
    sio.sleep(1)
    
    assert connected is True
    sio.disconnect()
