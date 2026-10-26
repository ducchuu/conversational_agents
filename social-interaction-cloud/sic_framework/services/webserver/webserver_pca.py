import os
import sys
import time
import logging
import asyncio
import tempfile
import threading
from pathlib import Path
from flask import Flask, render_template_string, render_template, request, jsonify
from flask_socketio import SocketIO, emit

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from dialog_mngr.agent_python.dialog_manager import DialogManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence Flask/Werkzeug static asset request spam
logging.getLogger("werkzeug").setLevel(logging.ERROR)


def _load_environment():
    """Load environment variables from .env file with zero-dependency fallback."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        for parent in Path(__file__).resolve().parents:
            env_file = parent / ".env"
            if env_file.is_file():
                load_dotenv(dotenv_path=env_file)
                break
    except ImportError:
        pass

    if not os.getenv("YOUTUBE_API_KEY"):
        for parent in Path(__file__).resolve().parents:
            env_file = parent / ".env"
            if env_file.is_file():
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip().strip("'\"")
                                if k and k not in os.environ:
                                    os.environ[k] = v
                    break
                except Exception:
                    pass


_load_environment()

from sic_framework.services.webserver.telemetry import telemetry
from sic_framework.services.webserver.youtube_service import youtube_bp
from sic_framework.services.webserver.stt_service import (
    models_ready,
    ensure_models_loaded,
    start_background_warmup,
    stt_available,
    get_local_nlu,
    transcribe_audio_file,
)
from sic_framework.services.webserver.llm_nlu_service import (
    CLAUDE_MODEL,
    DETERMINISTIC_INTENTS,  # noqa: F401  (re-exported for tests / external callers)
    INTENT_CANONICAL_MAP,  # noqa: F401
    NLUOutput,  # noqa: F401
    normalize_intent_name,
    get_few_shot_prompt,  # noqa: F401
    generate_agent_speech_llm,  # noqa: F401
    resolve_speech_text as _resolve_speech_text,
    extract_intent_llm,
    infer_fallback_intent,
)

# Initialize Flask, SocketIO, DialogManager, and background model warmup
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
app.register_blueprint(youtube_bp)
brain = DialogManager()
start_background_warmup()

connected_clients = set()
_disconnect_timer = None
active_session_sid = None
last_activity_time = 0.0


def resolve_speech_text(agent_intent, default_text, state_vars, on_chunk=None):
    return _resolve_speech_text(brain, agent_intent, default_text, state_vars, on_chunk=on_chunk)


def process_and_emit_actions(actions):
    """
    Two-pass execution:
    Pass 1: Resolve all speech payloads (streaming speech_chunk events immediately when Tier-2 LLM NLG runs)
    Pass 2: Emit single-shot speech (if not already streamed) before deferred navigation and state events
    """
    speech_to_emit = None
    streamed_chunks = False

    def _emit_speech_chunk(chunk_text, is_first, is_final):
        nonlocal streamed_chunks
        streamed_chunks = True
        emit(
            "speech_chunk",
            {
                "text": chunk_text,
                "is_first": is_first,
                "is_final": is_final,
            },
        )

    for action in actions:
        if action["type"] == "generate_speech":
            speech = resolve_speech_text(
                action["agent_intent"],
                action["default"],
                action.get("state_vars", {}),
                on_chunk=_emit_speech_chunk,
            )
            brain.state.pending_speech = speech
            speech_to_emit = speech

    if speech_to_emit and not streamed_chunks:
        emit("speech", speech_to_emit)

    for action in actions:
        if action["type"] == "emit":
            emit(action["event"], action["data"])


@app.route("/")
@app.route("/<string:page_name>", methods=["GET", "POST"])
def html_page(page_name="start.html"):
    if not page_name.endswith(".html"):
        return render_template_string("<h1>404 Not Found</h1>"), 404

    # If accessed while background AI models are still loading during cold start,
    # instantaneously serve the lightweight warm-up splash screen.
    if page_name in ["start.html", "index.html"] and not models_ready():
        return render_template("warming_up.html")

    if page_name in ["start.html", "index.html"]:
        brain.state.reset()
    try:
        return render_template(page_name)
    except Exception as e:
        logger.error(f"Error rendering {page_name}: {e}")
        return render_template_string("<h1>Template not found</h1>"), 404


@app.route("/api/health", methods=["GET"])
def health_check():
    """Liveness probe: answers immediately (port binds before models load) and reports warmup status."""
    resp = jsonify({
        "status": "ok",
        "service": "social-agent-cloud",
        "models_ready": models_ready(),
    })
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp, 200


@app.route("/api/ready", methods=["GET"])
def readiness_check():
    """Readiness probe: 200 only after faster-whisper and FastBERTNLU finished background warmup."""
    if not models_ready():
        resp = jsonify({"status": "warming_up", "models_ready": False})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 503
    resp = jsonify({"status": "ready", "models_ready": True})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp, 200


@app.route("/api/metrics", methods=["GET"])
def metrics_endpoint():
    """Telemetry and operational metrics for Cloud Monitoring."""
    return jsonify(telemetry.get_health_metrics()), 200


@socketio.on("connect")
def handle_connect():
    global _disconnect_timer, active_session_sid, last_activity_time
    if _disconnect_timer is not None:
        _disconnect_timer.cancel()
        _disconnect_timer = None
        logger.info("Client connected within grace period: preserved agent state.")

    connected_clients.add(request.sid)
    logger.info(f"Client connected: {request.sid} (Active clients: {len(connected_clients)})")

    # Single-session portfolio guard: notify if another visitor was actively interacting within 5 minutes
    is_in_use = (
        active_session_sid is not None
        and active_session_sid != request.sid
        and (time.time() - last_activity_time < 300)
        and brain.state.state not in ["start", "welcome"]
    )
    if is_in_use:
        emit("session_busy", {
            "in_use": True,
            "message": "CookingBroski is currently in a recipe session with another visitor. You can browse along, or click 'Start Over' to reset."
        })
    elif active_session_sid is None:
        active_session_sid = request.sid
        last_activity_time = time.time()

    emit("set_turn", "true")

    if brain.state.memory:
        emit("filters", brain.format_filters_string(brain.state.memory))
        emit("recipecounter", brain.state.recipe_counter)

    if brain.state.state in ["recipe_overview", "recipe_overview2"] and 0 < brain.state.recipe_counter <= 20:
        recipes = brain.prolog.query_recipes(brain.state.memory)
        emit("recipes", brain.prolog.get_recipes_json(recipes))

    if getattr(brain.state, "pending_speech", None):
        emit("speech", brain.state.pending_speech)
        brain.state.pending_speech = None
    logger.info(f"Current agent state: {brain.state.state}")


@socketio.on("disconnect")
def handle_disconnect():
    global _disconnect_timer, active_session_sid
    connected_clients.discard(request.sid)
    if request.sid == active_session_sid:
        active_session_sid = None
    logger.info(f"Client disconnected: {request.sid} (Remaining clients: {len(connected_clients)})")
    if len(connected_clients) == 0:
        if _disconnect_timer is not None:
            _disconnect_timer.cancel()

        def _delayed_reset():
            if len(connected_clients) == 0:
                brain.state.reset()
                logger.info("Grace period elapsed with no active clients: reset agent state to start.")

        _disconnect_timer = threading.Timer(15.0, _delayed_reset)
        _disconnect_timer.daemon = True
        _disconnect_timer.start()


@socketio.on("client_start")
def handle_client_start():
    global active_session_sid, last_activity_time
    active_session_sid = request.sid
    last_activity_time = time.time()
    logger.info("Client reached start page: resetting agent state.")
    brain.state.reset()


@socketio.on("event")
def handle_client_event(event_name):
    """Handle frontend lifecycle signals such as SpeechDone."""
    if event_name == "SpeechDone":
        logger.info("Speech playback completed on client.")
        brain.state.pending_speech = None


@socketio.on("buttonClick")
def handle_button_click(name):
    global active_session_sid, last_activity_time
    active_session_sid = request.sid
    last_activity_time = time.time()
    logger.info(f"Button clicked: {name}")
    brain.state.pending_speech = None
    if name == "start":
        brain.state.reset()
        actions = asyncio.run(brain.process_intent("start", {}))
    else:
        actions = asyncio.run(brain.process_intent("recipeRequest", {"recipe_name": name}))
    process_and_emit_actions(actions)


@socketio.on("audio_stream")
def handle_audio_stream(audio_bytes):
    """
    Receives WebM audio bytes from the browser's microphone,
    transcribes via faster-whisper / Whisper, predicts intent via FastBERTNLU or Claude LLM,
    and delegates to DialogManager using two-pass execution.
    """
    global active_session_sid, last_activity_time
    active_session_sid = request.sid
    last_activity_time = time.time()
    logger.info("Received audio stream from client. Processing...")

    ensure_models_loaded()
    if not stt_available():
        emit("transcript", "Error: no speech-to-text engine available.")
        return

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        t_turn_start = time.time()
        transcript = transcribe_audio_file(temp_audio_path)
        t_stt_end = time.time()
        stt_ms = (t_stt_end - t_turn_start) * 1000
        logger.info(f"STT heard: {transcript} ({stt_ms:.1f}ms)")
        emit("transcript", transcript)

        if not transcript:
            return

        # 3. Predict Intent (Prefer fast local BERT NLU if available, else Claude LLM)
        raw_intent = None
        slots = {}
        engine_used = "rule_fallback"
        confidence = 1.0

        local_nlu = get_local_nlu()
        if local_nlu and local_nlu.is_loaded():
            bert_intent, conf, bert_slots, _ = local_nlu.predict(transcript)
            if conf >= 0.6 and bert_intent and bert_intent != "unknown":
                raw_intent = bert_intent
                slots = bert_slots
                confidence = conf
                engine_used = f"bert_{local_nlu.backend}"
                logger.info(f"Fast BERT NLU classified: {raw_intent} (conf: {conf:.2f}), slots: {slots}")

        if not raw_intent:
            raw_intent, slots = extract_intent_llm(transcript)
            if raw_intent and raw_intent != "unknown":
                engine_used = f"claude_{CLAUDE_MODEL}"

        t_nlu_end = time.time()
        nlu_ms = (t_nlu_end - t_stt_end) * 1000

        # Check if user utterance directly names a recipe in overview states
        if brain.state.state in ["recipe_overview", "recipe_overview2"]:
            active_recipes = brain.prolog.query_recipes(brain.state.memory)
            matched_recipe_id = brain.prolog.find_recipe_by_title(transcript, candidate_ids=active_recipes)
            if matched_recipe_id:
                raw_intent = "recipeRequest"
                slots = {
                    "recipe_id": matched_recipe_id,
                    "recipe_name": brain.prolog.get_recipe_name(matched_recipe_id),
                }
                engine_used = "recipe_title_matcher"
                confidence = 1.0
                logger.info(f"Voice speech matched recipe {matched_recipe_id} ('{slots['recipe_name']}')")

        intent = normalize_intent_name(raw_intent) if raw_intent else "unknown"

        if intent.replace("_", "").lower() in [
            "cookingquestion",
            "helprequest",
            "outofscope",
            "unknown",
            "chitchat",
            "help",
            "checkcapability",
            "fallback",
        ]:
            if not slots.get("userQuery"):
                slots["userQuery"] = transcript

        t_dialog_start = time.time()
        if intent and intent != "unknown":
            logger.info(f"NLU Intent: {intent}, Slots: {slots}")
            print(f"{'=' * 80}", flush=True)
            brain.state.pending_speech = None
            actions = asyncio.run(brain.process_intent(intent, slots, utterance=transcript))
            process_and_emit_actions(actions)
        else:
            engine_used = "rule_fallback"
            logger.info("Evaluating conversational keyword fallback for unrecognized input...")
            intent, slots = infer_fallback_intent(transcript)
            actions = asyncio.run(brain.process_intent(intent, slots, utterance=transcript))
            process_and_emit_actions(actions)

        t_dialog_end = time.time()
        dialog_ms = (t_dialog_end - t_dialog_start) * 1000
        total_ms = (t_dialog_end - t_turn_start) * 1000

        telemetry.log_turn(
            transcript=transcript,
            intent=intent,
            engine=engine_used,
            stt_ms=stt_ms,
            nlu_ms=nlu_ms,
            dialog_ms=dialog_ms,
            total_ms=total_ms,
            slots=slots,
            confidence=confidence,
        )

    except Exception as e:
        logger.error(f"Error processing audio stream: {e}")
        emit("transcript", f"Error processing audio: {e}")
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False, allow_unsafe_werkzeug=True)
