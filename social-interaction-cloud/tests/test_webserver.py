import pytest
from unittest.mock import patch, MagicMock

# Import the module first so unittest.mock can find it
import sic_framework.services.nlu.utils.dataset

# Mock out heavy ML models (Whisper/BERT) and Prolog initialization
# before importing the Flask app so it doesn't crash during testing
with patch('torch.load'), \
     patch('whisper.load_model'), \
     patch('sic_framework.services.prolog.prolog_brain.PrologBrain.__init__', return_value=None), \
     patch('sic_framework.services.nlu.utils.dataset.fit_encoders'):
     
    from sic_framework.services.webserver.webserver_pca import app

@pytest.fixture
def client():
    """Fixture to get the Flask test client."""
    with app.test_client() as client:
        yield client

def test_webserver_html_routing(client):
    """Test that the webserver properly routes HTML templates."""
    with patch('sic_framework.services.webserver.webserver_pca.render_template', return_value="MOCKED_HTML"):
        response = client.get('/welcome.html')
        assert response.status_code == 200
        assert response.data == b"MOCKED_HTML"

def test_webserver_non_html_routing(client):
    """Test that requesting non-html files returns a 404."""
    response = client.get('/style.css')
    assert response.status_code == 404
    assert b"Not Found" in response.data

def test_youtube_api_search_missing_key(client):
    """Test the YouTube API endpoint when no key is provided."""
    with patch.dict('os.environ', clear=True):
        response = client.get('/api/youtube/search?title=chicken')
        assert response.status_code == 500
        assert b"Missing YOUTUBE_API_KEY" in response.data

def test_youtube_api_search_missing_title(client):
    """Test the YouTube API endpoint when no title is provided."""
    with patch.dict('os.environ', {'YOUTUBE_API_KEY': 'fake_key'}):
        response = client.get('/api/youtube/search')
        assert response.status_code == 400
        assert b"Missing title" in response.data
