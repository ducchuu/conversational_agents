import pytest
from unittest.mock import patch, MagicMock

# Patching SICComponent and redis to avoid actual Redis connection attempts
with patch('sic_framework.core.component_python2.SICComponent.__init__', return_value=None), \
     patch('redis.Redis'):
    from sic_framework.services.openai_whisper_speech_to_text.whisper_speech_to_text import SICWhisper, WhisperComponent, WhisperConf
    from sic_framework.services.openai_gpt.gpt import GPTComponent, GPTConf

@pytest.fixture
def whisper_component():
    # We mock whisper.load_model so it doesn't download massive gigabytes of AI models during CI testing!
    with patch('whisper.load_model') as mock_model, \
         patch('sic_framework.core.sic_redis.SICRedis') as mock_redis_cls, \
         patch('sic_framework.core.connector.SICConnector.__init__', return_value=None):
        mock_redis_cls.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        comp = SICWhisper.__new__(SICWhisper)
        comp.params = WhisperConf()
        comp.logger = MagicMock()
        return comp

def test_whisper_initialization(whisper_component):
    """Test that the Whisper STT component initializes with the default configuration."""
    assert whisper_component.params.model == "base.en"

@pytest.fixture
def gpt_component():
    with patch('openai.OpenAI') as mock_openai, \
         patch('sic_framework.core.sic_redis.SICRedis') as mock_redis_cls, \
         patch('sic_framework.core.component_python2.SICComponent.__init__', return_value=None):
        mock_redis_cls.return_value = MagicMock()
        conf = GPTConf(openai_key="fake_sk_key")
        comp = GPTComponent(conf=conf)
        comp.params = conf
        comp.client = mock_openai.return_value
        comp.logger = MagicMock()
        return comp

def test_gpt_initialization(gpt_component):
    """Test that the OpenAI GPT component initializes correctly."""
    assert gpt_component.client is not None
    assert gpt_component.params.model == "gpt-3.5-turbo"
