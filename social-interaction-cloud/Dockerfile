FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    swi-prolog \
    build-essential \
    espeak \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*


COPY . /app/

RUN pip install --no-cache-dir -e . 
RUN pip install --no-cache-dir pyswip pytest pytest-asyncio flask flask-socketio \
    google-cloud-speech google-cloud-texttospeech openai openai-whisper SpeechRecognition transformers torch scikit-learn

# Start the Flask webserver by default
CMD ["python", "sic_framework/services/webserver/webserver_pca.py"]
