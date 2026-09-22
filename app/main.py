import os
import time
import threading
import random

from datetime import datetime, timezone

from http.server import (
    ThreadingHTTPServer,
    BaseHTTPRequestHandler
)

from urllib.parse import (
    urlparse,
    parse_qs
)

from app.voice import generate_voice
from app.video import generate_video
from app.youtube import upload_short
from app.content import generate_content

from app.config import (
    YOUTUBE_DESCRIPTION,
    RELATED_VIDEO_URL
)


# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = "/app/output"

DATA_DIR = "/app/data"


# India timezone
IST_OFFSET_SECONDS = 5 * 3600 + 30 * 60


# ============================================================
# OAUTH CONFIG
# ============================================================

CLIENT_ID = os.getenv(
    "YOUTUBE_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "YOUTUBE_CLIENT_SECRET"
)

REDIRECT_URI = (
    "https://pocket-option-youtube-automation-production"
    ".up.railway.app/oauth2callback"
)


# ============================================================
# DIRECTORIES
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)


# ============================================================
# VIDEO SERVER
# ============================================================

class VideoHandler(
    BaseHTTPRequestHandler
):

    def log_message(
        self,
        format,
        *args
    ):

        print(
            f"[HTTP] {format % args}",
            flush=True
        )

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        if path == "/health":

            body = b'{"status":"ok"}'

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.end_headers()

            self.wfile.write(
                body
            )

            return

        if path == "/":

            body = b"""
            <html>
            <body>
            <h1>Pocket Option YouTube Automation</h1>
            <p>Automation service is running.</p>
            </body>
            </html>
            """

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/html"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.end_headers()

            self.wfile.write(
                body
            )

            return

        # Serve generated videos
        if path.startswith(
            "/output/"
        ):

            filename = path.replace(
                "/output/",
                "",
                1
            )

            file_path = os.path.join(
                OUTPUT_DIR,
                filename
            )

            if os.path.exists(
                file_path
            ):

                try:

                    with open(
                        file_path,
                        "rb"
                    ) as file:

                        data = file.read()

                    self.send_response(
                        200
                    )

                    self.send_header(
                        "Content-Type",
                        "video/mp4"
                    )

                    self.send_header(
                        "Content-Length",
                        str(len(data))
                    )

                    self.end_headers()

                    self.wfile.write(
                        data
                    )

                    return

                except Exception:

                    pass

        self.send_response(
            404
        )

        self.end_headers()


def start_video_server():

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            port
        ),
        VideoHandler
    )

    print(
        f"HTTP server running on port {port}",
        flush=True
    )

    server.serve_forever()


# ============================================================
# IST TIME
# ============================================================

def get_ist_now():

    now = datetime.now(
        timezone.utc
    )

    return now.astimezone(
        timezone(
            datetime.now().astimezone().utcoffset()
        )
    )


# ============================================================
# BETTER IST CALCULATION
# ============================================================

def current_ist():

    from datetime import timedelta

    return datetime.now(
        timezone.utc
    ) + timedelta(
        seconds=IST_OFFSET_SECONDS
    )


# ============================================================
# CHECK YOUTUBE TOKEN
# ============================================================

def youtube_connected():

    token_file = os.path.join(
        DATA_DIR,
        "youtube_token.json"
    )

    return os.path.exists(
        token_file
    )


# ============================================================
# GENERATE ONE SHORT
# ============================================================

def create_and_upload_short(
    slot_name
):

    print(
        "\n" + "=" * 70,
        flush=True
    )

    print(
        f"CREATING SHORT — {slot_name}",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    if not youtube_connected():

        raise RuntimeError(
            "YouTube is not connected."
        )

    # --------------------------------------------------------
    # CONTENT
    # --------------------------------------------------------

    content = generate_content()

    title = content["title"]

    script = content["script"]

    # --------------------------------------------------------
    # CTA
    # --------------------------------------------------------

    cta_text = (
        "Want to see the complete setup? "
        "Tap the Related Video below the title "
        "to watch the full tutorial."
    )

    full_script = (
        script
        + " "
        + cta_text
    )

    # --------------------------------------------------------
    # UNIQUE FILE NAMES
    # --------------------------------------------------------

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    voice_filename = (
        f"voice_{timestamp}.mp3"
    )

    video_filename = (
        f"short_{timestamp}.mp4"
    )

    # --------------------------------------------------------
    # ELEVENLABS
    # --------------------------------------------------------

    print(
        "\n[1/3] Generating ElevenLabs voice...",
        flush=True
    )

    voice_path = generate_voice(
        full_script,
        cta_text,
        voice_filename
    )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    print(
        "\n[2/3] Generating 4K Short...",
        flush=True
    )

    # Use a random test amount only if video.py
    # still expects the short_amount argument.
    short_amount = random.randint(
        1000,
        2000
    )

    video_path = generate_video(
        full_script,
        voice_path,
        video_filename,
        short_amount
    )

    # --------------------------------------------------------
    # YOUTUBE
    # --------------------------------------------------------

    print(
        "\n[3/3] Uploading to YouTube...",
        flush=True
    )

    result = upload_short(
        video_path,
        title,
        YOUTUBE_DESCRIPTION
    )

    print(
        "\n===== SHORT COMPLETE =====",
        flush=True
    )

    print(
        f"Title: {title}",
        flush=True
    )

    print(
        f"YouTube URL: {result['url']}",
        flush=True
    )

    print(
        f"Related Video to add: {RELATED_VIDEO_URL}",
        flush=True
    )

    print(
        "==========================",
        flush=True
    )

    return result


# ============================================================
# SCHEDULER
# ============================================================

last_morning_date = None

last_evening_date = None


def scheduler_loop():

    global last_morning_date
    global last_evening_date

    print(
        "\n===== DAILY SCHEDULER STARTED =====",
        flush=True
    )

    print(
        "10:00 AM IST → Short #1",
        flush=True
    )

    print(
        "6:00 PM IST → Short #2",
        flush=True
    )

    while True:

        try:

            now = current_ist()

            current_date = (
                now.strftime(
                    "%Y-%m-%d"
                )
            )

            current_time = (
                now.strftime(
                    "%H:%M"
                )
            )

            print(
                f"[SCHEDULER] IST: "
                f"{now.strftime('%Y-%m-%d %H:%M:%S')}",
                flush=True
            )

            # ------------------------------------------------
            # 10:00 AM
            # ------------------------------------------------

            if (
                current_time == "10:00"
                and
                last_morning_date != current_date
            ):

                last_morning_date = (
                    current_date
                )

                try:

                    create_and_upload_short(
                        "10:00 AM"
                    )

                except Exception as e:

                    print(
                        "\n10 AM SHORT FAILED:",
                        flush=True
                    )

                    print(
                        str(e),
                        flush=True
                    )

            # ------------------------------------------------
            # 6:00 PM
            # ------------------------------------------------

            if (
                current_time == "18:00"
                and
                last_evening_date != current_date
            ):

                last_evening_date = (
                    current_date
                )

                try:

                    create_and_upload_short(
                        "6:00 PM"
                    )

                except Exception as e:

                    print(
                        "\n6 PM SHORT FAILED:",
                        flush=True
                    )

                    print(
                        str(e),
                        flush=True
                    )

        except Exception as e:

            print(
                f"[SCHEDULER ERROR] {e}",
                flush=True
            )

        # Check every 20 seconds
        time.sleep(
            20
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70,
        flush=True
    )

    print(
        "POCKET OPTION YOUTUBE SHORTS AUTOMATION",
        flush=True
    )

    print(
        "2 SHORTS PER DAY",
        flush=True
    )

    print(
        "10:00 AM + 6:00 PM IST",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    if not os.getenv(
        "ELEVENLABS_API_KEY"
    ):

        print(
            "WARNING: ELEVENLABS_API_KEY missing.",
            flush=True
        )

    else:

        print(
            "ElevenLabs API key detected.",
            flush=True
        )

    if not youtube_connected():

        print(
            "\nWARNING: YouTube is NOT connected.",
            flush=True
        )

        print(
            "Open /authorize after adding the OAuth route.",
            flush=True
        )

    else:

        print(
            "\nYouTube authorization detected.",
            flush=True
        )

    # --------------------------------------------------------
    # SERVER
    # --------------------------------------------------------

    server_thread = threading.Thread(
        target=start_video_server,
        daemon=True
    )

    server_thread.start()

    # --------------------------------------------------------
    # SCHEDULER
    # --------------------------------------------------------

    scheduler_thread = threading.Thread(
        target=scheduler_loop,
        daemon=True
    )

    scheduler_thread.start()

    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------

    while True:

        print(
            f"[HEARTBEAT] "
            f"{current_ist().strftime('%Y-%m-%d %H:%M:%S')} IST",
            flush=True
        )

        time.sleep(
            300
        )


if __name__ == "__main__":

    main()
