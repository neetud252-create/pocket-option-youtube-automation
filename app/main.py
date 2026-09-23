import os
import random
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app.config import (
    YOUTUBE_DESCRIPTION,
    RELATED_VIDEO_URL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)

from app.content import generate_content
from app.voice import generate_voice
from app.video import generate_video
from app.youtube import upload_short


# ============================================================
# SETTINGS
# ============================================================

IST = ZoneInfo("Asia/Kolkata")

PORT = int(
    os.getenv(
        "PORT",
        "8080"
    )
)

DATA_DIR = "/app/data"

TOKEN_FILE = os.path.join(
    DATA_DIR,
    "youtube_token.json"
)

CLIENT_SECRET_FILE = os.path.join(
    DATA_DIR,
    "client_secret.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

REDIRECT_URI = (
    "https://pocket-option-youtube-automation-production.up.railway.app"
    "/oauth2callback"
)


# ============================================================
# RUNTIME STATE
# ============================================================

last_10am_date = None
last_6pm_date = None

oauth_flow = None


# ============================================================
# RANDOM DEMO VOLUME
# ============================================================

def generate_demo_volume():

    amount = random.randint(
        1000,
        2000
    )

    print(
        f"Random demo volume generated: ${amount}",
        flush=True
    )

    return amount


# ============================================================
# YOUTUBE OAUTH
# ============================================================

def create_oauth_flow():

    client_id = os.getenv(
        "GOOGLE_CLIENT_ID"
    )

    client_secret = os.getenv(
        "GOOGLE_CLIENT_SECRET"
    )

    if not client_id or not client_secret:

        raise RuntimeError(
            "GOOGLE_CLIENT_ID or "
            "GOOGLE_CLIENT_SECRET is missing."
        )

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri":
                "https://accounts.google.com/o/oauth2/auth",
            "token_uri":
                "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                REDIRECT_URI
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    return flow


# ============================================================
# LOAD YOUTUBE TOKEN
# ============================================================

def youtube_token_exists():

    return os.path.exists(
        TOKEN_FILE
    )


# ============================================================
# CREATE SHORT
# ============================================================

def create_and_upload_short(
    trigger="SCHEDULED"
):

    print(
        "\n"
        "==================================================",
        flush=True
    )

    print(
        f"STARTING SHORT CREATION: {trigger}",
        flush=True
    )

    print(
        "==================================================",
        flush=True
    )

    try:

        # ====================================================
        # 1. GENERATE CONTENT
        # ====================================================

        content = generate_content()

        script = content["script"]
        title = content["title"]

        print(
            "\n===== GENERATED CONTENT =====",
            flush=True
        )

        print(
            f"Title: {title}",
            flush=True
        )

        print(
            f"Script: {script}",
            flush=True
        )

        print(
            "==============================",
            flush=True
        )

        # ====================================================
        # 2. CTA SCRIPT
        # ====================================================

        cta_text = (
            "Want to activate the Pocket Option AI Bot? "
            "Go to my channel, open the channel description, "
            "and click the Bot Activation button."
        )

        print(
            "\nCTA:",
            flush=True
        )

        print(
            cta_text,
            flush=True
        )

        # ====================================================
        # 3. FULL VOICE SCRIPT
        # ====================================================

        full_script = (
            script.strip()
            + " "
            + cta_text
        )

        # ====================================================
        # 4. RANDOM DEMO VOLUME
        # ====================================================

        short_amount = generate_demo_volume()

        print(
            f"\nDemo volume for this Short: "
            f"${short_amount}",
            flush=True
        )

        # ====================================================
        # 5. UNIQUE FILENAMES
        # ====================================================

        timestamp = datetime.now(
            IST
        ).strftime(
            "%Y%m%d_%H%M%S"
        )

        voice_filename = (
            f"voice_{timestamp}.mp3"
        )

        video_filename = (
            f"short_{timestamp}.mp4"
        )

        voice_path = os.path.join(
            "/app/output",
            voice_filename
        )

        video_path = os.path.join(
            "/app/output",
            video_filename
        )

        os.makedirs(
            "/app/output",
            exist_ok=True
        )

        # ====================================================
        # 6. ELEVENLABS VOICE
        # ====================================================

        print(
            "\n===== GENERATING VOICE =====",
            flush=True
        )

        generate_voice(
            full_script,
            cta_text,
            voice_path
        )

        print(
            "Voice generation complete.",
            flush=True
        )

        # ====================================================
        # 7. GENERATE VIDEO
        # ====================================================

        print(
            "\n===== GENERATING VIDEO =====",
            flush=True
        )

        generate_video(
            script,
            voice_path,
            video_filename,
            short_amount
        )

        print(
            "Video generation complete.",
            flush=True
        )

        # ====================================================
        # 8. YOUTUBE DESCRIPTION
        # ====================================================

        description = YOUTUBE_DESCRIPTION

        # ====================================================
        # 9. UPLOAD SHORT
        # ====================================================

        print(
            "\n===== UPLOADING TO YOUTUBE =====",
            flush=True
        )

        upload_result = upload_short(
            video_path,
            title,
            description
        )

        print(
            "\n===== YOUTUBE UPLOAD COMPLETE =====",
            flush=True
        )

        print(
            f"Video ID: "
            f"{upload_result['video_id']}",
            flush=True
        )

        print(
            f"Video URL: "
            f"{upload_result['url']}",
            flush=True
        )

        print(
            "Privacy: UNLISTED",
            flush=True
        )

        print(
            "====================================",
            flush=True
        )

        print(
            "\nRelated Video is NOT being used.",
            flush=True
        )

        print(
            "CTA directs viewers to the channel description.",
            flush=True
        )

        print(
            "Bot Activation button should be in the channel description.",
            flush=True
        )

        return upload_result

    except Exception as e:

        print(
            "\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
            flush=True
        )

        print(
            "SHORT CREATION FAILED",
            flush=True
        )

        print(
            f"ERROR: {e}",
            flush=True
        )

        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
            flush=True
        )

        raise


# ============================================================
# MANUAL TEST
# ============================================================

def start_manual_test():

    print(
        "\nStarting manual Short test...",
        flush=True
    )

    thread = threading.Thread(
        target=create_and_upload_short,
        args=("MANUAL TEST",),
        daemon=True
    )

    thread.start()


# ============================================================
# HTTP SERVER
# ============================================================

class Handler(
    BaseHTTPRequestHandler
):

    def log_message(
        self,
        format,
        *args
    ):

        return

    def do_GET(self):

        global oauth_flow

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        # ====================================================
        # HOME
        # ====================================================

        if path == "/":

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.end_headers()

            status = (
                "Connected"
                if youtube_token_exists()
                else "Not Connected"
            )

            html = f"""
            <html>
            <head>
                <title>Pocket Option YouTube Automation</title>
            </head>
            <body>
                <h1>Pocket Option YouTube Shorts Automation</h1>

                <p>
                    <b>Schedule:</b>
                    10:00 AM + 6:00 PM IST
                </p>

                <p>
                    <b>YouTube:</b>
                    {status}
                </p>

                <p>
                    <b>Testing privacy:</b>
                    UNLISTED
                </p>

                <p>
                    <a href="/authorize">
                        Connect YouTube
                    </a>
                </p>

                <p>
                    <a href="/run-test">
                        Run Test Short
                    </a>
                </p>
            </body>
            </html>
            """

            self.wfile.write(
                html.encode(
                    "utf-8"
                )
            )

            return

        # ====================================================
        # HEALTH
        # ====================================================

        if path == "/health":

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain"
            )

            self.end_headers()

            self.wfile.write(
                b"OK"
            )

            return

        # ====================================================
        # RUN TEST
        # ====================================================

        if path == "/run-test":

            start_manual_test()

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.end_headers()

            html = """
            <html>
            <body>
                <h1>Test Started</h1>

                <p>
                    The Short is being generated
                    in the background.
                </p>

                <p>
                    Check Railway logs for progress.
                </p>

                <p>
                    The YouTube upload will be
                    <b>UNLISTED</b>.
                </p>
            </body>
            </html>
            """

            self.wfile.write(
                html.encode(
                    "utf-8"
                )
            )

            return

        # ====================================================
        # AUTHORIZE
        # ====================================================

        if path == "/authorize":

            try:

                oauth_flow = create_oauth_flow()

                authorization_url, state = (
                    oauth_flow.authorization_url(
                        access_type="offline",
                        include_granted_scopes="true",
                        prompt="consent"
                    )
                )

                self.send_response(
                    302
                )

                self.send_header(
                    "Location",
                    authorization_url
                )

                self.end_headers()

                return

            except Exception as e:

                self.send_response(
                    500
                )

                self.send_header(
                    "Content-Type",
                    "text/plain"
                )

                self.end_headers()

                self.wfile.write(
                    str(e).encode(
                        "utf-8"
                    )
                )

                return

        # ====================================================
        # OAUTH CALLBACK
        # ====================================================

        if path == "/oauth2callback":

            try:

                if oauth_flow is None:

                    oauth_flow = (
                        create_oauth_flow()
                    )

                authorization_response = (
                    "https://pocket-option-youtube-automation-production.up.railway.app"
                    + self.path
                )

                oauth_flow.fetch_token(
                    authorization_response=authorization_response
                )

                credentials = (
                    oauth_flow.credentials
                )

                os.makedirs(
                    DATA_DIR,
                    exist_ok=True
                )

                with open(
                    TOKEN_FILE,
                    "w",
                    encoding="utf-8"
                ) as token_file:

                    token_file.write(
                        credentials.to_json()
                    )

                self.send_response(
                    200
                )

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )

                self.end_headers()

                html = """
                <html>
                <body>
                    <h1>YouTube Connected Successfully</h1>

                    <p>
                        Your YouTube authorization was successful.
                    </p>

                    <p>
                        The authorization token has been
                        saved to persistent Railway storage.
                    </p>

                    <p>
                        You can close this page.
                    </p>
                </body>
                </html>
                """

                self.wfile.write(
                    html.encode(
                        "utf-8"
                    )
                )

                return

            except Exception as e:

                self.send_response(
                    500
                )

                self.send_header(
                    "Content-Type",
                    "text/plain"
                )

                self.end_headers()

                self.wfile.write(
                    str(e).encode(
                        "utf-8"
                    )
                )

                return

        # ====================================================
        # 404
        # ====================================================

        self.send_response(
            404
        )

        self.send_header(
            "Content-Type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Not Found"
        )


# ============================================================
# SCHEDULER
# ============================================================

def scheduler_loop():

    global last_10am_date
    global last_6pm_date

    print(
        "\n"
        "==========================================",
        flush=True
    )

    print(
        "DAILY SCHEDULER",
        flush=True
    )

    print(
        "10:00 AM IST -> Short #1",
        flush=True
    )

    print(
        "6:00 PM IST -> Short #2",
        flush=True
    )

    print(
        "TEST UPLOAD PRIVACY -> UNLISTED",
        flush=True
    )

    print(
        "==========================================",
        flush=True
    )

    while True:

        try:

            now = datetime.now(
                IST
            )

            current_date = now.date()

            current_time = (
                now.hour,
                now.minute
            )

            # =================================================
            # 10 AM
            # =================================================

            if (
                current_time == (10, 0)
                and last_10am_date != current_date
            ):

                print(
                    "\n10:00 AM IST reached.",
                    flush=True
                )

                last_10am_date = current_date

                thread = threading.Thread(
                    target=create_and_upload_short,
                    args=("10:00 AM SCHEDULE",),
                    daemon=True
                )

                thread.start()

            # =================================================
            # 6 PM
            # =================================================

            if (
                current_time == (18, 0)
                and last_6pm_date != current_date
            ):

                print(
                    "\n6:00 PM IST reached.",
                    flush=True
                )

                last_6pm_date = current_date

                thread = threading.Thread(
                    target=create_and_upload_short,
                    args=("6:00 PM SCHEDULE",),
                    daemon=True
                )

                thread.start()

        except Exception as e:

            print(
                f"Scheduler error: {e}",
                flush=True
            )

        time.sleep(
            20
        )


# ============================================================
# HEARTBEAT
# ============================================================

def heartbeat_loop():

    while True:

        try:

            now = datetime.now(
                IST
            )

            print(
                f"[HEARTBEAT] "
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} IST",
                flush=True
            )

            print(
                "10:00 AM IST -> Short #1",
                flush=True
            )

            print(
                "6:00 PM IST -> Short #2",
                flush=True
            )

            print(
                "YouTube privacy -> UNLISTED",
                flush=True
            )

        except Exception as e:

            print(
                f"Heartbeat error: {e}",
                flush=True
            )

        time.sleep(
            300
        )


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    os.makedirs(
        "/app/output",
        exist_ok=True
    )

    print(
        "\n"
        "==============================================",
        flush=True
    )

    print(
        "POCKET OPTION YOUTUBE SHORTS AUTOMATION",
        flush=True
    )

    print(
        "4 RANDOM CLIPS + 1 CTA CLIP",
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
        "TEST PRIVACY: UNLISTED",
        flush=True
    )

    print(
        "==============================================",
        flush=True
    )

    # ========================================================
    # ELEVENLABS
    # ========================================================

    if os.getenv(
        "ELEVENLABS_API_KEY"
    ):

        print(
            "ElevenLabs API key detected.",
            flush=True
        )

    else:

        print(
            "WARNING: ElevenLabs API key not detected.",
            flush=True
        )

    # ========================================================
    # GEMINI
    # ========================================================

    if GEMINI_API_KEY:

        print(
            f"Gemini API key detected. "
            f"Model: {GEMINI_MODEL}",
            flush=True
        )

    else:

        print(
            "WARNING: Gemini API key not detected.",
            flush=True
        )

    # ========================================================
    # YOUTUBE
    # ========================================================

    if youtube_token_exists():

        print(
            "YouTube OAuth token detected.",
            flush=True
        )

    else:

        print(
            "WARNING: YouTube OAuth token not detected.",
            flush=True
        )

    # ========================================================
    # CTA
    # ========================================================

    print(
        "CTA: Channel description -> Bot Activation button",
        flush=True
    )

    print(
        f"Legacy Related Video URL stored: "
        f"{RELATED_VIDEO_URL}",
        flush=True
    )

    # ========================================================
    # HTTP SERVER
    # ========================================================

    server = HTTPServer(
        ("0.0.0.0", PORT),
        Handler
    )

    print(
        f"HTTP server running on port {PORT}",
        flush=True
    )

    print(
        f"OAuth callback: {REDIRECT_URI}",
        flush=True
    )

    # ========================================================
    # START SCHEDULER
    # ========================================================

    scheduler_thread = threading.Thread(
        target=scheduler_loop,
        daemon=True
    )

    scheduler_thread.start()

    # ========================================================
    # START HEARTBEAT
    # ========================================================

    heartbeat_thread = threading.Thread(
        target=heartbeat_loop,
        daemon=True
    )

    heartbeat_thread.start()

    # ========================================================
    # START SERVER
    # ========================================================

    server.serve_forever()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
