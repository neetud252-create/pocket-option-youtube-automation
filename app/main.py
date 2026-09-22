import os
import time
import json
import threading

from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = "/app/output"
DATA_DIR = "/app/data"

CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")

REDIRECT_URI = (
    "https://pocket-option-youtube-automation-production"
    ".up.railway.app/oauth2callback"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


# ============================================================
# DIRECTORY
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


TOKEN_FILE = os.path.join(
    DATA_DIR,
    "youtube_token.json"
)


# ============================================================
# YOUTUBE OAUTH
# ============================================================

def create_oauth_flow():

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
        redirect_uri=REDIRECT_URI
    )

    return flow


def save_credentials(credentials):

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
        "\nYouTube OAuth credentials saved.",
        flush=True
    )


def load_credentials():

    if not os.path.exists(TOKEN_FILE):
        return None

    try:

        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

        return credentials

    except Exception as e:

        print(
            f"Could not load YouTube credentials: {e}",
            flush=True
        )

        return None


# ============================================================
# HTTP HANDLER
# ============================================================

class AutomationHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):

        print(
            f"[HTTP] {format % args}",
            flush=True
        )

    def send_html(
        self,
        html,
        status=200
    ):

        body = html.encode(
            "utf-8"
        )

        self.send_response(status)

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

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        # ----------------------------------------------------
        # HOME
        # ----------------------------------------------------

        if path == "/":

            credentials = load_credentials()

            if credentials:

                self.send_html(
                    """
                    <html>
                    <head>
                    <title>YouTube Automation</title>
                    </head>
                    <body>
                    <h1>YouTube Automation</h1>
                    <p>✅ YouTube account is connected.</p>
                    <p>The OAuth credentials have been saved.</p>
                    </body>
                    </html>
                    """
                )

            else:

                self.send_html(
                    """
                    <html>
                    <head>
                    <title>YouTube Automation</title>
                    </head>
                    <body>
                    <h1>YouTube Automation</h1>
                    <p>YouTube channel is not connected yet.</p>
                    <p>
                    <a href="/authorize">
                    Connect YouTube Channel
                    </a>
                    </p>
                    </body>
                    </html>
                    """
                )

            return

        # ----------------------------------------------------
        # START OAUTH
        # ----------------------------------------------------

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

                # Save state for callback verification
                state_file = os.path.join(
                    DATA_DIR,
                    "oauth_state.txt"
                )

                with open(
                    state_file,
                    "w",
                    encoding="utf-8"
                ) as file:

                    file.write(
                        state
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
                    <h1>OAuth Error</h1>
                    <pre>{e}</pre>
                    </body>
                    </html>
                    """,
                    500
                )

            return

        # ----------------------------------------------------
        # OAUTH CALLBACK
        # ----------------------------------------------------

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
                    <h1>YouTube Authorization Failed</h1>
                    <p>Error: {error}</p>
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

            if not code:

                self.send_html(
                    """
                    <html>
                    <body>
                    <h1>Authorization Error</h1>
                    <p>No authorization code was received.</p>
                    </body>
                    </html>
                    """,
                    400
                )

                return

            try:

                flow = create_oauth_flow()

                flow.fetch_token(
                    code=code
                )

                credentials = flow.credentials

                save_credentials(
                    credentials
                )

                self.send_html(
                    """
                    <html>
                    <head>
                    <title>YouTube Connected</title>
                    </head>
                    <body>
                    <h1>✅ YouTube Connected Successfully</h1>

                    <p>
                    Your YouTube authorization was successful.
                    </p>

                    <p>
                    You can now close this page.
                    </p>

                    <p>
                    The automation will use this authorization
                    for YouTube uploads.
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
                    <h1>YouTube OAuth Error</h1>
                    <pre>{e}</pre>
                    </body>
                    </html>
                    """,
                    500
                )

            return

        # ----------------------------------------------------
        # HEALTH CHECK
        # ----------------------------------------------------

        if path == "/health":

            self.send_html(
                """
                {
                    "status": "ok"
                }
                """
            )

            return

        # ----------------------------------------------------
        # 404
        # ----------------------------------------------------

        self.send_html(
            """
            <html>
            <body>
            <h1>404</h1>
            </body>
            </html>
            """,
            404
        )


# ============================================================
# SERVER
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
        "=" * 60,
        flush=True
    )

    print(
        "POCKET OPTION YOUTUBE AUTOMATION",
        flush=True
    )

    print(
        f"Server running on port {port}",
        flush=True
    )

    print(
        f"OAuth callback: {REDIRECT_URI}",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    server.serve_forever()


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\nStarting YouTube automation...",
        flush=True
    )

    if CLIENT_ID:
        print(
            "YOUTUBE_CLIENT_ID detected.",
            flush=True
        )
    else:
        print(
            "WARNING: YOUTUBE_CLIENT_ID missing.",
            flush=True
        )

    if CLIENT_SECRET:
        print(
            "YOUTUBE_CLIENT_SECRET detected.",
            flush=True
        )
    else:
        print(
            "WARNING: YOUTUBE_CLIENT_SECRET missing.",
            flush=True
        )

    existing_credentials = load_credentials()

    if existing_credentials:

        print(
            "✅ Existing YouTube authorization found.",
            flush=True
        )

    else:

        print(
            "YouTube authorization is not connected yet.",
            flush=True
        )

        print(
            "Open /authorize to connect the channel.",
            flush=True
        )

    start_server()


if __name__ == "__main__":
    main()
