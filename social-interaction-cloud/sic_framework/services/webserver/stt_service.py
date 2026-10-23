import os
import logging
import threading

logger = logging.getLogger(__name__)

# Compatibility fix: PyAV removed 'metadata_errors' keyword argument in recent releases,
# but faster-whisper passes metadata_errors='ignore' to av.open().
try:
    import av
    _orig_av_open = av.open

    def _safe_av_open(*args, **kwargs):
        try:
            return _orig_av_open(*args, **kwargs)
        except TypeError as err:
            if "metadata_errors" in str(err):
                kwargs.pop("metadata_errors", None)
                return _orig_av_open(*args, **kwargs)
            raise

    av.open = _safe_av_open
except Exception:
    pass

stt_model = None
local_nlu = None
_model_warmup_lock = threading.Lock()
_models_warmed = threading.Event()

DOMAIN_PROMPT = (
    "CookingBroski conversational assistant: recipe, ingredients, pick one for me, "
    "recommend the best dish, under 30 minutes, vegetarian, Italian, Mexican, Asian, "
    "chicken, pasta, garlic, without onions, exclude dairy, instructions, what can I substitute, confirm."
)


def warmup_heavy_models():
    """
    Background daemon model warmup:
    Binds the HTTP port in <1.5s so Cloud Run's routing proxy marks the container
    healthy immediately, while heavier CTranslate2 and ONNX weights load into RAM in the background.
    """
    global stt_model, local_nlu
    with _model_warmup_lock:
        if _models_warmed.is_set():
            return
        logger.info("Background model warmup started (faster-whisper & FastBERTNLU)...")
        if stt_model is None:
            try:
                from faster_whisper import WhisperModel
                whisper_model_name = os.getenv("WHISPER_MODEL", "base.en").strip()
                cpu_threads = int(os.getenv("WHISPER_CPU_THREADS", "4"))
                logger.info(f"Loading faster-whisper {whisper_model_name} model (int8 on CPU, {cpu_threads} threads)...")
                # Create once per application process, not once per request.
                stt_model = WhisperModel(
                    whisper_model_name,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=cpu_threads,
                    num_workers=1,
                )
                logger.info(f"faster-whisper ({whisper_model_name}) loaded successfully in background!")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper: {e}")
                stt_model = None

        if local_nlu is None:
            try:
                from sic_framework.services.nlu.fast_bert_nlu import FastBERTNLU
                local_nlu = FastBERTNLU()
                if local_nlu.is_loaded():
                    logger.info(f"Loaded local BERT NLU engine (backend: {local_nlu.backend})")
                else:
                    logger.info("FastBERTNLU initialized in standby mode (using Claude LLM for NLU).")
            except Exception as e:
                logger.warning(f"FastBERTNLU background initialization: {e}")
                local_nlu = None

        _models_warmed.set()
        logger.info("Background model warmup completed! All models ready.")


def ensure_models_loaded(timeout=15.0):
    """Ensure models are ready before processing voice streams."""
    if not _models_warmed.is_set():
        logger.info("Waiting for background model warmup to finish before transcribing...")
        _models_warmed.wait(timeout=timeout)
        if not _models_warmed.is_set():
            warmup_heavy_models()


def models_ready() -> bool:
    """True once background warmup (faster-whisper + FastBERTNLU) has finished."""
    return _models_warmed.is_set()


def start_background_warmup():
    """Spawn background warmup thread immediately so HTTP port binds in <1.5s."""
    threading.Thread(target=warmup_heavy_models, daemon=True).start()


def get_stt_model():
    return stt_model


def get_local_nlu():
    return local_nlu


def stt_available() -> bool:
    """True if at least one STT engine (local faster-whisper or cloud API key) can serve a request."""
    return bool(
        stt_model is not None or os.getenv("ELEVENLABS_API_KEY") or os.getenv("OPENAI_API_KEY")
    )


ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
STT_HTTP_TIMEOUT_S = 10


def transcribe_with_elevenlabs(audio_path: str, language_code: str = "en") -> str:
    """Primary STT: ElevenLabs Scribe v2 over plain HTTP (no SDK / torch needed in the container)."""
    import requests

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")

    with open(audio_path, "rb") as audio_file:
        response = requests.post(
            ELEVENLABS_STT_URL,
            headers={"xi-api-key": api_key},
            files={"file": (os.path.basename(audio_path), audio_file, "audio/webm")},
            data={
                "model_id": "scribe_v2",
                "language_code": language_code,
                # Keep non-speech tags like "(laughter)" out of the BERT tokenizer.
                "tag_audio_events": "false",
                # Strip filler words / false starts before they reach the NLU.
                "no_verbatim": "true",
            },
            timeout=STT_HTTP_TIMEOUT_S,
        )
    response.raise_for_status()
    return response.json().get("text", "").strip()


def transcribe_with_openai_api(audio_path: str) -> str:
    """Secondary STT: OpenAI hosted whisper-1 (HTTP, no local torch dependency)."""
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured for STT fallback")
    with open(audio_path, "rb") as audio_file:
        response = requests.post(
            OPENAI_STT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (os.path.basename(audio_path), audio_file, "audio/webm")},
            data={"model": "whisper-1", "language": "en", "prompt": DOMAIN_PROMPT},
            timeout=STT_HTTP_TIMEOUT_S,
        )
    response.raise_for_status()
    return response.json().get("text", "").strip()


def transcribe_with_faster_whisper(audio_path: str) -> str:
    """Primary offline STT: bundled faster-whisper (CTranslate2 INT8 on CPU with 4 threads)."""
    if stt_model is None:
        raise RuntimeError("faster-whisper model is not loaded")
    segments, info = stt_model.transcribe(
        audio_path,
        beam_size=1,
        language="en",
        word_timestamps=False,
        initial_prompt=DOMAIN_PROMPT,
        vad_filter=True,
    )
    segments = list(segments)
    return " ".join(seg.text for seg in segments).strip()


def transcribe_audio_file(temp_audio_path: str) -> str:
    """
    Transcribe an audio file with a cascading engine strategy (Local Edge-First):
    local faster-whisper -> ElevenLabs Scribe v2 -> OpenAI whisper-1 API.
    Local model runs first for zero API cost and low latency; cloud APIs serve as fallback.
    """
    engines = []
    if stt_model is not None:
        engines.append(("faster_whisper", transcribe_with_faster_whisper))
    if os.getenv("ELEVENLABS_API_KEY"):
        engines.append(("elevenlabs_scribe_v2", transcribe_with_elevenlabs))
    if os.getenv("OPENAI_API_KEY"):
        engines.append(("openai_whisper_1", transcribe_with_openai_api))

    if not engines:
        raise RuntimeError("No STT engine available (load faster-whisper or set ELEVENLABS_API_KEY / OPENAI_API_KEY)")

    last_error = None
    for name, engine in engines:
        try:
            text = engine(temp_audio_path)
            logger.info(f"STT engine used: {name}")
            return text
        except Exception as e:
            last_error = e
            logger.warning(f"STT engine {name} failed ({e}); trying next engine...")
    raise RuntimeError(f"All STT engines failed; last error: {last_error}")

