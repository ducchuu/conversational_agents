import os
import time

import pytest
import requests
import socketio

# The live URL will be passed in via environment variable
CLOUD_RUN_URL = os.getenv("CLOUD_RUN_URL")
READY_TIMEOUT_S = int(os.getenv("READY_TIMEOUT_S", "120"))


@pytest.fixture(scope="module")
def ready_service():
    """Block until /api/ready reports that faster-whisper and FastBERTNLU finished warmup."""
    deadline = time.time() + READY_TIMEOUT_S
    last = None
    while time.time() < deadline:
        try:
            last = requests.get(f"{CLOUD_RUN_URL}/api/ready", timeout=10)
            if last.status_code == 200:
                return CLOUD_RUN_URL
        except requests.RequestException as exc:
            last = exc
        time.sleep(3)
    pytest.fail(f"Service not ready after {READY_TIMEOUT_S}s (last: {last})")


@pytest.mark.skipif(not CLOUD_RUN_URL, reason="CLOUD_RUN_URL environment variable is not set")
def test_e2e_liveness_and_readiness(ready_service):
    """Liveness answers immediately and reports models_ready once warmup is done."""
    health = requests.get(f"{CLOUD_RUN_URL}/api/health", timeout=10)
    assert health.status_code == 200
    assert health.json()["models_ready"] is True


@pytest.mark.skipif(not CLOUD_RUN_URL, reason="CLOUD_RUN_URL environment variable is not set")
def test_e2e_http_endpoint(ready_service):
    """Test that the Cloud Run container is serving the basic HTTP files."""
    response = requests.get(f"{CLOUD_RUN_URL}/welcome.html")
    assert response.status_code == 200
    assert "html" in response.text.lower()

@pytest.mark.skipif(not CLOUD_RUN_URL, reason="CLOUD_RUN_URL environment variable is not set")
def test_e2e_websocket_connection(ready_service):
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
