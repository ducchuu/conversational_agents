FROM python:3.12-slim

# NOTE: PYTHONOPTIMIZE is intentionally NOT set: it strips `assert`, which would make the
# in-image pytest run (cloudbuild.yaml) pass vacuously.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/hf-cache \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PORT=8080 \
    PATH="/home/appuser/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    swi-prolog \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Dependencies first (cached until requirements.txt changes)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 2) faster-whisper weights baked into the image (cached independently of source changes).
#    HF_HOME is shared so the non-root runtime user finds them while HF_HUB_OFFLINE=1.
RUN HF_HUB_OFFLINE=0 python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')"

# 3) Application source
COPY . /app/
RUN pip install --no-cache-dir --no-deps -e . && \
    python -m compileall -q /app/sic_framework /app/dialog_mngr

# 4) Drop privileges
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app /opt/hf-cache
USER appuser

EXPOSE 8080

# Single worker on purpose: pyswip/SWI-Prolog global state and the in-process DialogManager are not
# multi-process safe. Threads give concurrency for I/O (LLM/STT HTTP calls, Socket.IO long-polling/WebSocket).
CMD ["gunicorn", "--worker-class", "gthread", "-w", "1", "--threads", "8", "--timeout", "120", "-b", "0.0.0.0:8080", "sic_framework.services.webserver.webserver_pca:app"]
