FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        wget \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Local TTS fallback. ElevenLabs stays primary, but Piper keeps
# the daily automation alive if ElevenLabs has a key/quota/outage issue.
RUN mkdir -p /app/voices \
    && wget -q --tries=3 --timeout=30 \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
    -O /app/voices/en_US-lessac-medium.onnx \
    && wget -q --tries=3 --timeout=30 \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
    -O /app/voices/en_US-lessac-medium.onnx.json

COPY . .

# Exactly one Gunicorn worker is intentional: app.main starts one scheduler
# thread, and multiple workers would create duplicate scheduler instances.
CMD ["sh", "-c", "gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-8080} app.main:app"]
