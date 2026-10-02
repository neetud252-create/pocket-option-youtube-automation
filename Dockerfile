FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        wget \
        fontconfig \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# app/video.py uses this exact font path for the bold Shorts overlay.
# Debian images can place DejaVu files differently, so resolve a real bold
# DejaVu font during the image build and create the expected path if needed.
RUN mkdir -p /usr/share/fonts/truetype/dejavu \
    && if [ ! -f /usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf ]; then \
         FONT_FILE="$(find /usr/share/fonts -type f \( -iname 'DejaVuSansCondensed-Bold.ttf' -o -iname 'DejaVuSans-Bold.ttf' -o -iname '*DejaVu*Bold*.ttf' \) | head -n 1)"; \
         test -n "$FONT_FILE"; \
         ln -sf "$FONT_FILE" /usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf; \
       fi \
    && test -f /usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf \
    && fc-cache -f

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
