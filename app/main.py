import os
import time
import json
import threading

from datetime import datetime
from zoneinfo import ZoneInfo

from http.server import (
    ThreadingHTTPServer,
    BaseHTTPRequestHandler
)

from urllib.parse import (
    urlparse,
    parse_qs
)

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

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

TIMEZONE = ZoneInfo(
    "Asia/Kolkata"
)

TOKEN_FILE = os.path.join(
    DATA_DIR,
    "youtube_token.json"
)

STATE_FILE = os.path.join(
    DATA_DIR,
    "oauth_state.txt"
)

VERIFIER_FILE = os.path.join(
    DATA_DIR,
    "oauth_code_verifier.txt"
)


# ============================================================
# GOOGLE OAUTH
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

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


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
# OAUTH FLOW
# ============================================================

def create_oauth_flow(
    code_verifier=None
):

    if not CLIENT_ID:

        raise RuntimeError(
            "YOUTUBE_CLIENT_ID is missing."
        )

    if not CLIENT_SECRET:

        raise RuntimeError(
            "YOUTUBE_CLIENT_SECRET is missing."
        )

    client_config = {

        "web": {

            "client_id": CLIENT_ID,

            "client_secret": CLIENT_SECRET,

            "auth_uri": (
                "https://accounts.google.com/o/oauth2/auth"
            ),

            "token_uri": (
                "https://oauth2.googleapis.com/token"
            ),

            "redirect_uris": [
                REDIRECT_URI
            ]
        }
    }

    flow = Flow.from_client_config(

        client_config,

        scopes=SCOPES,

        redirect_uri=REDIRECT_URI,

        code_verifier=code_verifier,

        autogenerate_code_verifier=(
            code_verifier is None
        )
    )

    return flow


# ============================================================
# SAVE CREDENTIALS
# ============================================================

def save_credentials(
    credentials
):

    data = {

        "token": credentials.token,

        "refresh_token": credentials.refresh_token,

        "token_uri": credentials.token_uri,

        "client_id": credentials.client_id,

        "client_secret": credentials.client_secret,

        "scopes": credentials.scopes,
    }

    with open(
        TOKEN_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2
        )

    print(
        "YouTube credentials saved.",
        flush=True
    )


# ============================================================
# LOAD CREDENTIALS
# ============================================================

def load_credentials():

    if not os.path.exists(
        TOKEN_FILE
    ):

        return None

    try:

        return (
            Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES
            )
        )

    except Exception as e:

        print(
            f"Credential load error: {e}",
            flush=True
        )

        return None


# ============================================================
# SAVE OAUTH STATE
# ============================================================

def save_oauth_state(
    state,
    code_verifier
):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            state
        )

    with open(
        VERIFIER_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            code_verifier
        )


# ============================================================
# LOAD OAUTH STATE
# ============================================================

def load_oauth_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return None

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read().strip()


# ============================================================
# LOAD CODE VERIFIER
# ============================================================

def load_code_verifier():

    if not os.path.exists(
        VERIFIER_FILE
    ):

        return None

    with open(
        VERIFIER_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read().strip()


# ============================================================
# CLEAR OAUTH TEMP DATA
# ============================================================

def clear_oauth_data():

    for path in [
        STATE_FILE,
        VERIFIER_FILE
    ]:

        try:

            if os.path.exists(
                path
            ):

                os.remove(
                    path
                )

        except Exception:

            pass


# ============================================================
# CHECK YOUTUBE CONNECTION
# ============================================================

def youtube_connected():

    return os.path.exists(
        TOKEN_FILE
    )


# ============================================================
# HTTP SERVER
# ============================================================

class AutomationHandler(
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

    # --------------------------------------------------------
    # SEND HTML
    # --------------------------------------------------------

    def send_html(
        self,
        html,
        status=200
    ):

        body = html.encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        # ====================================================
        # HOME
        # ====================================================

        if path == "/":

            connected = youtube_connected()

            status = (
                "✅ YouTube connected"
                if connected
                else "⚠️ YouTube not connected"
            )

            self.send_html(
                f"""
                <html>

                <head>
                <title>Pocket Option Automation</title>
                </head>

                <body>

                <h1>
                Pocket Option YouTube Automation
                </h1>

                <p>
                Status: {status}
                </p>

                <p>
                Schedule:
                10:00 AM IST and 6:00 PM IST
                </p>

                <p>
                Related Video:
                {RELATED_VIDEO_URL}
                </p>

                <p>
                <a href="/authorize">
                Connect / Reconnect YouTube
                </a>
                </p>

                </body>

                </html>
                """
            )

            return

        # ====================================================
        # HEALTH
        # ====================================================

        if path == "/health":

            self.send_html(
                """
                {
                    "status": "ok"
                }
                """
            )

            return

        # ====================================================
        # OAUTH AUTHORIZE
        # ====================================================

        if path == "/authorize":

            try:

                flow = create_oauth_flow()

                authorization_url, state = (
                    flow.authorization_url(

                        access_type="offline",

                        include_granted_scopes="true",

                        prompt="consent"
                    )
                )

                code_verifier = (
                    flow.code_verifier
                )

                if not code_verifier:

                    raise RuntimeError(
                        "OAuth code verifier was not generated."
                    )

                save_oauth_state(
                    state,
                    code_verifier
                )

                self.send_response(
                    302
                )

                self.send_header(
                    "Location",
                    authorization_url
                )

                self.end_headers()

            except Exception as e:

                self.send_html(
                    f"""
                    <html>

                    <body>

                    <h1>
                    OAuth Error
                    </h1>

                    <pre>{e}</pre>

                    </body>

                    </html>
                    """,
                    500
                )

            return

        # ====================================================
        # OAUTH CALLBACK
        # ====================================================

        if path == "/oauth2callback":

            query = parse_qs(
                parsed.query
            )

            error = query.get(
                "error",
                [None]
            )[0]

            if error:

                self.send_html(
                    f"""
                    <html>

                    <body>

                    <h1>
                    YouTube Authorization Failed
                    </h1>

                    <p>
                    {error}
                    </p>

                    </body>

                    </html>
                    """,
                    400
                )

                return

            code = query.get(
                "code",
                [None]
            )[0]

            returned_state = query.get(
                "state",
                [None]
            )[0]

            if not code:

                self.send_html(
                    """
                    <html>

                    <body>

                    <h1>
                    Authorization Error
                    </h1>

                    <p>
                    No authorization code received.
                    </p>

                    </body>

                    </html>
                    """,
                    400
                )

                return

            saved_state = (
                load_oauth_state()
            )

            if not saved_state:

                self.send_html(
                    """
                    <html>

                    <body>

                    <h1>
                    OAuth State Missing
                    </h1>

                    <p>
                    Please start authorization again.
                    </p>

                    </body>

                    </html>
                    """,
                    400
                )

                return

            if returned_state != saved_state:

                self.send_html(
                    """
                    <html>

                    <body>

                    <h1>
                    OAuth State Mismatch
                    </h1>

                    <p>
                    Please start authorization again.
                    </p>

                    </body>

                    </html>
                    """,
                    400
                )

                return

            code_verifier = (
                load_code_verifier()
            )

            if not code_verifier:

                self.send_html(
                    """
                    <html>

                    <body>

                    <h1>
                    OAuth Code Verifier Missing
                    </h1>

                    <p>
                    Please start authorization again.
                    </p>

                    </body>

                    </html>
                    """,
                    400
                )

                return

            try:

                flow = create_oauth_flow(
                    code_verifier=code_verifier
                )

                flow.fetch_token(
                    code=code
                )

                credentials = (
                    flow.credentials
                )

                save_credentials(
                    credentials
                )

                clear_oauth_data()

                self.send_html(
                    """
                    <html>

                    <head>
                    <title>YouTube Connected</title>
                    </head>

                    <body>

                    <h1>
                    ✅ YouTube Connected Successfully
                    </h1>

                    <p>
                    Your YouTube authorization was successful.
                    </p>

                    <p>
                    The token is stored in persistent Railway
                    storage.
                    </p>

                    <p>
                    You can close this page.
                    </p>

                    </body>

                    </html>
                    """
                )

            except Exception as e:

                print(
                    "\n===== YOUTUBE OAUTH ERROR =====",
                    flush=True
                )

                print(
                    str(e),
                    flush=True
                )

                self.send_html(
                    f"""
                    <html>

                    <body>

                    <h1>
                    YouTube OAuth Error
                    </h1>

                    <pre>{e}</pre>

                    </body>

                    </html>
                    """,
                    500
                )

            return

        # ====================================================
        # MANUAL TEST
        # ====================================================

        if path == "/run-test":

            if not youtube_connected():

                self.send_html(
                    """
                    <html>

                    <body>

                    <h1>
                    YouTube not connected
                    </h1>

                    </body>

                    </html>
                    """,
                    400
                )

                return

            threading.Thread(
                target=create_and_upload_short,
                args=("MANUAL TEST",),
                daemon=True
            ).start()

            self.send_html(
                """
                <html>

                <body>

                <h1>
                Test started
                </h1>

                <p>
                Check Railway logs for progress.
                </p>

                </body>

                </html>
                """
            )

            return

        # ====================================================
        # 404
        # ====================================================

        self.send_html(
            """
            <html>

            <body>

            <h1>
            404
            </h1>

            </body>

            </html>
            """,
            404
        )


# ============================================================
# START SERVER
# ============================================================

def start_server():

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
        AutomationHandler
    )

    print(
        f"HTTP server running on port {port}",
        flush=True
    )

    print(
        f"OAuth callback: {REDIRECT_URI}",
        flush=True
    )

    server.serve_forever()


# ============================================================
# CREATE ONE SHORT
# ============================================================

def create_and_upload_short(
    slot_name
):

    print(
        "\n" + "=" * 70,
        flush=True
    )

    print(
        f"CREATING SHORT: {slot_name}",
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
    # NEW CONTENT
    # --------------------------------------------------------

    content = generate_content()

    title = content[
        "title"
    ]

    script = content[
        "script"
    ]

    print(
        "\n===== NEW TITLE =====",
        flush=True
    )

    print(
        title,
        flush=True
    )

    print(
        "\n===== NEW SCRIPT =====",
        flush=True
    )

    print(
        script,
        flush=True
    )

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
    # FILE NAMES
    # --------------------------------------------------------

    timestamp = datetime.now(
        TIMEZONE
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
        "\n[1/3] ElevenLabs voice...",
        flush=True
    )

    voice_path = generate_voice(
        full_script,
        cta_text,
        voice_filename
    )

    print(
        f"Voice: {voice_path}",
        flush=True
    )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    print(
        "\n[2/3] Creating 4K Short...",
        flush=True
    )

    # Current video.py requires short_amount.
    # IMPORTANT:
    # Change the production opening in video.py before
    # publishing automated videos so it does not claim
    # fabricated daily earnings.
    short_amount = 0

    video_path = generate_video(
        full_script,
        voice_path,
        video_filename,
        short_amount
    )

    print(
        f"Video: {video_path}",
        flush=True
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
        "\n" + "=" * 70,
        flush=True
    )

    print(
        "SHORT UPLOAD COMPLETE",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    print(
        f"Title: {title}",
        flush=True
    )

    print(
        f"Video ID: {result['video_id']}",
        flush=True
    )

    print(
        f"URL: {result['url']}",
        flush=True
    )

    print(
        f"Related Video: {RELATED_VIDEO_URL}",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    return result


# ============================================================
# DAILY SCHEDULER
# ============================================================

last_10am_date = None
last_6pm_date = None


def scheduler_loop():

    global last_10am_date
    global last_6pm_date

    print(
        "\n===== DAILY SCHEDULER =====",
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

            now = datetime.now(
                TIMEZONE
            )

            today = (
                now.strftime(
                    "%Y-%m-%d"
                )
            )

            current_time = (
                now.strftime(
                    "%H:%M"
                )
            )

            # ------------------------------------------------
            # 10 AM
            # ------------------------------------------------

            if (
                current_time == "10:00"
                and
                last_10am_date != today
            ):

                last_10am_date = today

                print(
                    "\n10:00 AM trigger detected.",
                    flush=True
                )

                try:

                    create_and_upload_short(
                        "10:00 AM"
                    )

                except Exception as e:

                    print(
                        "\n10 AM ERROR:",
                        flush=True
                    )

                    print(
                        str(e),
                        flush=True
                    )

            # ------------------------------------------------
            # 6 PM
            # ------------------------------------------------

            if (
                current_time == "18:00"
                and
                last_6pm_date != today
            ):

                last_6pm_date = today

                print(
                    "\n6:00 PM trigger detected.",
                    flush=True
                )

                try:

                    create_and_upload_short(
                        "6:00 PM"
                    )

                except Exception as e:

                    print(
                        "\n6 PM ERROR:",
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

        # Check frequently enough to catch
        # the scheduled minute.
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

    # --------------------------------------------------------
    # ENVIRONMENT CHECK
    # --------------------------------------------------------

    if os.getenv(
        "ELEVENLABS_API_KEY"
    ):

        print(
            "✅ ElevenLabs API key detected.",
            flush=True
        )

    else:

        print(
            "❌ ELEVENLABS_API_KEY missing.",
            flush=True
        )

    if os.getenv(
        "GEMINI_API_KEY"
    ):

        print(
            "✅ Gemini API key detected.",
            flush=True
        )

    else:

        print(
            "⚠️ GEMINI_API_KEY missing.",
            flush=True
        )

    if youtube_connected():

        print(
            "✅ YouTube OAuth token detected.",
            flush=True
        )

    else:

        print(
            "❌ YouTube OAuth token missing.",
            flush=True
        )

    print(
        f"Related Video: {RELATED_VIDEO_URL}",
        flush=True
    )

    # --------------------------------------------------------
    # SERVER
    # --------------------------------------------------------

    server_thread = threading.Thread(
        target=start_server,
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

        now = datetime.now(
            TIMEZONE
        )

        print(
            f"[HEARTBEAT] "
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} IST",
            flush=True
        )

        time.sleep(
            300
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
