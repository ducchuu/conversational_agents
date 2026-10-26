import pytest
from unittest.mock import patch, MagicMock

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


def test_warmup_splash_routing_when_not_ready(client):
    """When models are warming up (cold start), visiting / or /start.html serves warming_up.html."""
    with patch('sic_framework.services.webserver.webserver_pca.models_ready', return_value=False):
        with patch('sic_framework.services.webserver.webserver_pca.render_template', return_value="WARMUP_HTML") as mock_render:
            response = client.get('/')
            assert response.status_code == 200
            mock_render.assert_called_with("warming_up.html")

            response_start = client.get('/start.html')
            assert response_start.status_code == 200
            mock_render.assert_called_with("warming_up.html")


def test_start_page_routing_when_ready(client):
    """When models are warm, visiting / or /start.html serves start.html."""
    with patch('sic_framework.services.webserver.webserver_pca.models_ready', return_value=True):
        with patch('sic_framework.services.webserver.webserver_pca.render_template', return_value="START_HTML") as mock_render:
            response = client.get('/')
            assert response.status_code == 200
            mock_render.assert_called_with("start.html")

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


def test_health_and_readiness_probes(client):
    """Liveness always answers 200 and reports warmup state; readiness is 200 only once models are warm."""
    health = client.get('/api/health')
    assert health.status_code == 200
    assert "models_ready" in health.get_json()
    assert health.headers.get("Access-Control-Allow-Origin") == "*"

    # Preflight OPTIONS check
    opt = client.options('/api/ready')
    assert opt.status_code == 204
    assert opt.headers.get("Access-Control-Allow-Origin") == "*"

    with patch('sic_framework.services.webserver.webserver_pca.models_ready', return_value=False):
        resp = client.get('/api/ready')
        assert resp.status_code == 503
        assert resp.get_json()["status"] == "warming_up"
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    with patch('sic_framework.services.webserver.webserver_pca.models_ready', return_value=True):
        resp = client.get('/api/ready?wait=1')
        assert resp.status_code == 200
        assert resp.get_json()["models_ready"] is True
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_telemetry_counts_onnx_int8_as_local_hit():
    """Regression: bert_onnx_int8 must count as a Tier-1 local hit, not a fallback."""
    from sic_framework.services.webserver.telemetry import PipelineTelemetry

    t = PipelineTelemetry()
    t.log_turn("a", "addFilter", "bert_onnx_int8")
    t.log_turn("b", "addFilter", "bert_onnx_int8")
    t.log_turn("c", "cookingQuestion", "claude_claude-haiku-5-5")
    t.log_turn("d", "unknown", "rule_fallback")
    assert t.get_fallback_rate() == 50.0


def test_rejected_recipes_accumulate_and_are_excluded():
    """Regression: consecutive rejections must keep every rejected recipe excluded."""
    from sic_framework.services.webserver.webserver_pca import brain

    brain.state.reset()
    all_ids = brain.prolog.query_recipes({})
    assert len(all_ids) >= 3
    first, second = all_ids[0], all_ids[1]
    brain.state.reject_recipe(first)
    brain.state.reject_recipe(second)
    brain.state.reject_recipe(second)
    assert brain.state.memory["exclude_recipe"] == [first, second]
    remaining = brain.prolog.query_recipes(brain.state.memory)
    assert first not in remaining and second not in remaining
    assert len(remaining) == len(all_ids) - 2
    brain.state.reset()


def test_process_example_labels_multi_value_slots():
    """Regression: list-valued slots must be BIO-labelled, not silently dropped."""
    from sic_framework.services.nlu.utils import dataset

    dataset.fit_encoders(str(dataset_ontology_path()))
    tokens, _, labels = dataset.process_example({
        "text": "I want tomato and basil",
        "intent": "addFilter",
        "slots": {"ingredient": ["tomato", "basil"]},
    })
    tags = dataset.slot_label_encoder.inverse_transform(labels)
    assert tags[tokens.index("tomato")] == "B-ingredient"
    assert tags[tokens.index("basil")] == "B-ingredient"


def dataset_ontology_path():
    from pathlib import Path
    import sic_framework.services.nlu.utils as utils_pkg
    return Path(utils_pkg.__file__).resolve().parent / "data" / "ontology.json"


def test_youtube_blueprint_registered():
    """The /api/youtube/search route is served by the youtube_bp blueprint."""
    from sic_framework.services.webserver.webserver_pca import app
    assert "youtube" in app.blueprints


def test_stt_cascade_prefers_local_then_cloud():
    """STT cascade: faster-whisper (local) -> ElevenLabs -> OpenAI; no import of the torch-only `whisper` package."""
    from sic_framework.services.webserver import stt_service

    calls = []

    def _fail_local(path):
        calls.append("faster_whisper")
        raise RuntimeError("local failed")

    def _fail_elevenlabs(path):
        calls.append("elevenlabs")
        raise RuntimeError("cloud failed")

    def _ok_openai(path):
        calls.append("openai")
        return "hello from openai"

    with patch.object(stt_service, "stt_model", object()), \
         patch.dict('os.environ', {"ELEVENLABS_API_KEY": "k1", "OPENAI_API_KEY": "k2"}), \
         patch.object(stt_service, "transcribe_with_faster_whisper", _fail_local), \
         patch.object(stt_service, "transcribe_with_elevenlabs", _fail_elevenlabs), \
         patch.object(stt_service, "transcribe_with_openai_api", _ok_openai):
        assert stt_service.transcribe_audio_file("x.webm") == "hello from openai"
    assert calls == ["faster_whisper", "elevenlabs", "openai"]


def test_llm_speech_clause_streaming():
    """Verify generate_agent_speech_llm flushes clause/sentence chunks immediately via on_chunk."""
    from sic_framework.services.webserver.llm_nlu_service import generate_agent_speech_llm

    fake_deltas = [
        "You can substitute ",
        "butter with olive oil ",
        "in most savory recipes. ",
        "Would you like to ",
        "add any more filters?",
    ]

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__.return_value.text_stream = iter(fake_deltas)
    mock_stream_ctx.__exit__.return_value = False

    emitted_chunks = []

    def _on_chunk(text, is_first, is_final):
        emitted_chunks.append((text, is_first, is_final))

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}), \
         patch("sic_framework.services.webserver.llm_nlu_service.anthropic_client.messages.stream", return_value=mock_stream_ctx):
        full_text = generate_agent_speech_llm(
            "cookingQuestion",
            "Default fallback.",
            {"current_state": "recipe_overview", "userQuery": "Can I substitute butter?"},
            [],
            on_chunk=_on_chunk,
        )

    assert full_text == "You can substitute butter with olive oil in most savory recipes. Would you like to add any more filters?"
    assert len(emitted_chunks) == 2
    assert emitted_chunks[0] == (
        "You can substitute butter with olive oil in most savory recipes.",
        True,
        False,
    )
    assert emitted_chunks[1] == (
        "Would you like to add any more filters?",
        False,
        True,
    )


def test_kitchen_context_hydration_from_prolog():
    """Verify _build_kitchen_context and get_recipe_context_summary hydrate active recipe and filters."""
    from sic_framework.services.webserver.webserver_pca import brain
    from sic_framework.services.webserver.llm_nlu_service import _build_kitchen_context

    brain.state.reset()
    brain.state.state = "recipe_confirmation"
    brain.state.memory = {"cuisine": "asian"}
    brain.state.recipe_counter = 12
    brain.state.last_sent_recipe = "1"

    ctx = _build_kitchen_context(brain, {"current_state": "recipe_confirmation"})
    assert ctx["current_state"] == "recipe_confirmation"
    assert ctx["remaining_recipes_count"] == 12
    assert ctx["active_filters"] == {"cuisine": "asian"}
    assert ctx["active_recipe"].get("recipe_id") == "1"
    assert len(ctx["active_recipe"].get("ingredients", [])) > 0


