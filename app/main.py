import os
import time
import json
import threading

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
# CREATE OAUTH FLOW
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
        "\nYouTube OAuth credentials saved.",
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

        credentials = (
            Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES
            )
        )

        return credentials

    except Exception as e:

        print(
            f"Could not load YouTube credentials: {e}",
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

    print(
        "OAuth state and PKCE verifier saved.",
        flush=True
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

    for file_path in [
        STATE_FILE,
        VERIFIER_FILE
    ]:

        try:

            if os.path.exists(
                file_path
            ):

                os.remove(
                    file_path
                )

        except Exception:

            pass


# ============================================================
# HTTP HANDLER
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

                    <p>
                    ✅ YouTube account is connected.
                    </p>

                    <p>
                    OAuth credentials are saved.
                    </p>

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

                    <p>
                    YouTube channel is not connected yet.
                    </p>

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

        # ====================================================
        # AUTHORIZE
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

                code_verifier = flow.code_verifier

                if not code_verifier:

                    raise RuntimeError(
                        "OAuth code verifier was not generated."
                    )

                save_oauth_state(
                    state,
                    code_verifier
                )

                print(
                    "\n===== YOUTUBE OAUTH STARTED =====",
                    flush=True
                )

                print(
                    f"State saved: {state[:20]}...",
                    flush=True
                )

                print(
                    "PKCE code verifier saved.",
                    flush=True
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

                print(
                    "\n===== OAUTH START ERROR =====",
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

                    <h1>OAuth Error</h1>

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

                    <h1>YouTube Authorization Failed</h1>

                    <p>
                    Error: {error}
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

                    <h1>Authorization Error</h1>

                    <p>
                    No authorization code was received.
                    </p>

                    </body>
                    </html>
                    """,
                    400
                )

                return

            # ------------------------------------------------
            # LOAD SAVED STATE
            # ------------------------------------------------

            saved_state = load_oauth_state()

            if not saved_state:

                self.send_html(
                    """
                    <html>
                    <body>

                    <h1>OAuth State Missing</h1>

                    <p>
                    Please start the authorization again.
                    </p>

                    </body>
                    </html>
                    """,
                    400
                )

                return

            # ------------------------------------------------
            # VERIFY STATE
            # ------------------------------------------------

            if returned_state != saved_state:

                print(
                    "OAuth state mismatch.",
                    flush=True
                )

                self.send_html(
                    """
                    <html>
                    <body>

                    <h1>OAuth State Mismatch</h1>

                    <p>
                    Please start the authorization again.
                    </p>

                    </body>
                    </html>
                    """,
                    400
                )

                return

            # ------------------------------------------------
            # LOAD PKCE VERIFIER
            # ------------------------------------------------

            code_verifier = load_code_verifier()

            if not code_verifier:

                self.send_html(
                    """
                    <html>
                    <body>

                    <h1>OAuth Code Verifier Missing</h1>

                    <p>
                    Please start the authorization again.
                    </p>

                    </body>
                    </html>
                    """,
                    400
                )

                return

            # ------------------------------------------------
            # EXCHANGE CODE
            # ------------------------------------------------

            try:

                flow = create_oauth_flow(
                    code_verifier=code_verifier
                )

                flow.fetch_token(
                    code=code
                )

                credentials = flow.credentials

                if not credentials.refresh_token:

                    print(
                        "WARNING: No refresh token returned.",
                        flush=True
                    )

                save_credentials(
                    credentials
                )

                clear_oauth_data()

                print(
                    "\n" + "=" * 60,
                    flush=True
                )

                print(
                    "YOUTUBE OAUTH SUCCESS",
                    flush=True
                )

                print(
                    "=" * 60,
                    flush=True
                )

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
                    The authorization token has been saved
                    to persistent Railway storage.
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

                print(
                    "Please restart the authorization flow.",
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

                    <p>
                    Please go back and start the
                    authorization process again.
                    </p>

                    </body>

                    </html>
                    """,
                    500
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
        # 404
        # ====================================================

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

    existing_credentials = (
        load_credentials()
    )

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
