import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

# Patching SICComponent to avoid Redis connection attempts during tests
with patch('sic_framework.core.component_python2.SICComponent.__init__', return_value=None):
    from sic_framework.services.webserver.webserver_pca import WebserverComponent

@pytest.fixture
def webserver_component():
    """Fixture to create a WebserverComponent instance with mocked dependencies."""
    # We mock out the threading and SocketIO to prevent them from starting a real server
    with patch('sic_framework.services.webserver.webserver_pca.SocketIO'), \
         patch('threading.Thread'):
        
        comp = WebserverComponent()
        # Since we mocked SICComponent.__init__, we must manually initialize what's needed
        comp.logger = MagicMock()
        comp.params = MagicMock()
        comp.params.host = "127.0.1.1"
        comp.params.port = 8080
        comp.app = Flask(__name__)
        comp.socketio = MagicMock()
        
        # Register the routes manually since start_web_app isn't called fully
        comp.render_template_string_routes()
        return comp

@pytest.fixture
def client(webserver_component):
    """Fixture to get the Flask test client."""
    with webserver_component.app.test_client() as client:
        yield client

def test_webserver_html_routing(client):
    """Test that the webserver properly routes and attempts to render HTML templates."""
    # We mock render_template so we don't actually need the HTML files to exist in the test folder
    with patch('sic_framework.services.webserver.webserver_pca.render_template', return_value="MOCKED_HTML"):
        response = client.get('/welcome.html')
        assert response.status_code == 200
        assert response.data == b"MOCKED_HTML"

def test_webserver_non_html_routing(client):
    """Test that requesting non-html files returns a default response."""
    response = client.get('/style.css')
    assert response.status_code == 200
    assert b"hello???" in response.data

def test_youtube_api_search_missing_key(client):
    """Test the YouTube API endpoint when no key is provided."""
    with patch.dict('os.environ', clear=True):  # Ensure YOUTUBE_API_KEY is not set
        response = client.get('/api/youtube/search?title=chicken')
        assert response.status_code == 500
        assert b"Missing YOUTUBE_API_KEY" in response.data

def test_youtube_api_search_missing_title(client):
    """Test the YouTube API endpoint when no title is provided."""
    with patch.dict('os.environ', {'YOUTUBE_API_KEY': 'fake_key'}):
        response = client.get('/api/youtube/search')
        assert response.status_code == 400
        assert b"Missing title" in response.data
