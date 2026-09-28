import os
import logging
import asyncio
from flask import Flask, render_template_string, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from sic_framework.services.prolog.prolog_brain import PrologBrain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: In a production app, you would load these keys from a .env file!
os.environ["YOUTUBE_API_KEY"] = "AIzaSyBMlr2WN0DZDkDZuEXOBuYyQIT8nbkHvbA"

# Initialize Flask and SocketIO
app = Flask(__name__, template_folder='templates', static_folder='static')
# cors_allowed_origins="*" is important for WebSockets in Cloud Run
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Initialize our new Prolog Brain
brain = PrologBrain()

# Load the Prolog database (this path assumes you copy the recipe_database.pl into the docker container)
# brain.load_knowledge_base("path/to/recipe_database.pl")

@app.route("/")
@app.route("/<string:page_name>", methods=['GET', 'POST'])
def html_page(page_name="welcome.html"):
    if not page_name.endswith(".html"):
        return render_template_string("<h1>404 Not Found</h1>"), 404
    try:
        return render_template(page_name)
    except Exception as e:
        logger.error(f"Error rendering {page_name}: {e}")
        return render_template_string("<h1>Template not found</h1>"), 404

@app.route("/api/youtube/search", methods=["GET"])
def youtube_search():
    import requests
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return jsonify({"error": "Missing YOUTUBE_API_KEY"}), 500

    title = (request.args.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Missing title"}), 400

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f"{title} recipe",
        "type": "video",
        "maxResults": 1,
        "safeSearch": "strict",
        "key": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        items = r.json().get("items", [])
        if not items:
            return jsonify({"videoId": None})
        return jsonify({"videoId": items[0].get("id", {}).get("videoId")})
    except Exception:
        return jsonify({"videoId": None}), 502

@socketio.on("connect")
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    # Tell the client it's their turn as soon as they connect
    emit("set_turn", "true")

@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on("buttonClick")
def handle_button_click(name):
    logger.info(f"Button clicked: {name}")
    # Here you can assert facts to prolog based on button clicks!
    brain.assert_fact(f"button_clicked('{name}')")
    
import whisper
import tempfile
import torch
from importlib.resources import files
from sic_framework.services.nlu.utils.predict import predict
from sic_framework.services.nlu.utils.model import BERTNLUModel
from sic_framework.services.nlu.utils.dataset import fit_encoders, intent_label_encoder, slot_label_encoder

# Load NLU Model and Encoders once at startup
try:
    logger.info("Loading BERT NLU Model...")
    ontology_path = str(files("sic_framework.services.nlu.utils.data").joinpath("ontology.json"))
    model_path = str(files("sic_framework.services.nlu.utils.checkpoints").joinpath("model_checkpoint.pt"))
    
    fit_encoders(ontology_path)
    num_intents = len(intent_label_encoder.classes_)
    num_slots = len(slot_label_encoder.classes_)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    nlu_model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots).to(device)
    nlu_model.load_state_dict(torch.load(model_path, weights_only=True, map_location=device))
    logger.info("BERT NLU Model loaded successfully!")
except Exception as e:
    logger.error(f"Failed to load NLU model: {e}")
    nlu_model = None

# Load Whisper STT model once at startup
try:
    logger.info("Loading Whisper base.en model...")
    stt_model = whisper.load_model("base.en", device=device)
    logger.info("Whisper loaded successfully!")
except Exception as e:
    logger.error(f"Failed to load Whisper: {e}")
    stt_model = None

@socketio.on("audio_stream")
def handle_audio_stream(audio_bytes):
    """
    Receives WebM/Wav audio bytes from the browser's microphone,
    transcribes it using Whisper, predicts the intent using BERT, 
    and asserts it to Prolog.
    """
    logger.info("Received audio stream from client. Processing...")
    
    if not stt_model:
        emit("transcript", "Error: STT model not loaded.")
        return

    # 1. Save audio temporarily to run through Whisper
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name
        
    try:
        # 2. Get the transcript
        result = stt_model.transcribe(temp_audio_path, language="en")
        transcript = result.get("text", "").strip()
        logger.info(f"Whisper heard: {transcript}")
        
        # Send the transcript back to the browser so the user sees what they said
        emit("transcript", transcript)
        
        if not transcript:
            return
            
        # 3. Predict Intent using BERT NLU
        if nlu_model:
            intent, intent_conf, slots, slot_confs = predict(nlu_model, transcript, max_length=16, device=device)
            logger.info(f"NLU Intent: {intent} ({intent_conf}), Slots: {slots}")
            
            # 4. Assert the intent into Prolog
            asyncio.run(brain.process_intent(intent, slots))
        else:
            logger.warning("NLU model missing, falling back to raw transcript assert.")
            brain.assert_fact(f"transcript('{transcript}')")
            
        # 5. Get the next action (handled inside process_intent or queried directly)
        # emit("pattern", "a50recipeSelect")
        
    except Exception as e:
        logger.error(f"Error processing audio stream: {e}")
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


if __name__ == "__main__":
    # In production/Docker, you'd use gunicorn. For dev, we run SocketIO directly.
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)