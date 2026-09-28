import pytest
from unittest.mock import patch, MagicMock

# Patching SICComponent to avoid Redis connection attempts
with patch('sic_framework.core.component_python2.SICComponent.__init__', return_value=None):
    from sic_framework.services.openai_whisper_speech_to_text.whisper_speech_to_text import SICWhisper
    from sic_framework.services.openai_gpt.gpt import OpenAIGPT, OpenAIGPTConf

@pytest.fixture
def whisper_component():
    # We mock whisper.load_model so it doesn't download massive gigabytes of AI models during CI testing!
    with patch('whisper.load_model') as mock_model:
        mock_model.return_value = MagicMock()
        comp = SICWhisper()
        comp.logger = MagicMock()
        return comp

def test_whisper_initialization(whisper_component):
    """Test that the Whisper STT component initializes and requests the base model."""
    import whisper
    # Verify load_model was called (we default to 'base.en' normally)
    assert whisper.load_model.called

@pytest.fixture
def gpt_component():
    with patch('openai.OpenAI'):
        conf = OpenAIGPTConf(api_key="fake_sk_key")
        comp = OpenAIGPT(conf=conf)
        comp.logger = MagicMock()
        return comp

def test_gpt_initialization(gpt_component):
    """Test that the OpenAI GPT component initializes correctly."""
    assert gpt_component.client is not None
    assert gpt_component.params.model == "gpt-3.5-turbo"
