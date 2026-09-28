import pytest
from unittest.mock import patch, MagicMock

# Patching SICComponent and SICRedis to avoid Redis connection attempts
with patch('sic_framework.core.component_python2.SICComponent.__init__', return_value=None), \
     patch('sic_framework.core.sic_redis.SICRedis.__init__', return_value=None):
    from sic_framework.services.google_stt.google_stt import GoogleSpeechToText, GoogleSpeechToTextConf
    from sic_framework.services.text2speech.text2speech_service import Text2Speech, Text2SpeechConf

@pytest.fixture
def stt_component():
    with patch('google.cloud.speech.SpeechClient'):
        conf = GoogleSpeechToTextConf(keyfile_json={"fake": "key", "project_id": "test_project"}, sample_rate_hertz=44100, language="en-US")
        comp = GoogleSpeechToText(conf=conf)
        comp.logger = MagicMock()
        return comp

def test_google_stt_initialization(stt_component):
    """Test that the Google STT component initializes correctly."""
    assert stt_component.params.language == "en-US"
    assert stt_component.params.sample_rate_hertz == 44100

@pytest.fixture
def tts_component():
    with patch('google.cloud.texttospeech.TextToSpeechClient'):
        conf = Text2SpeechConf(keyfile={"fake": "key"})
        comp = Text2Speech(conf=conf)
        comp.logger = MagicMock()
        return comp

def test_google_tts_initialization(tts_component):
    """Test that the Google TTS component initializes correctly."""
    assert tts_component.params.language == "en-US"
    # Verify the google cloud client was mocked and set
    assert tts_component.client is not None
