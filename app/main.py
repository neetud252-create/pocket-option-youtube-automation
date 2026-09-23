import os
import random
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, redirect, request
from google_auth_oauthlib.flow import Flow

from app.config import (
    YOUTUBE_DESCRIPTION,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)
from app.content import generate_content
from app.voice import generate_voice
from app.video import generate_video
from app.youtube import upload_short


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = "/app/data"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMEZONE = ZoneInfo("Asia/Kolkata")

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = (
    "https://pocket-option-youtube-automation-production.up.railway.app"
    "/oauth2callback"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

oauth_flow = None


# ============================================================
# RANDOM TEST AMOUNT
# ============================================================

def generate_demo_volume():
    amount = random.randint(1000, 2000)

    print(
        f"Random test amount generated: ${amount}",
        flush=True
    )

    return amount


# ============================================================
# CREATE + UPLOAD SHORT
# ============================================================

def create_and_upload_short(reason="SCHEDULED"):

    print("\n" + "=" * 60, flush=True)
    print("STARTING SHORT CREATION", flush=True)
    print(f"Reason: {reason}", flush=True)
    print("=" * 60, flush=True)

    try:

        # ----------------------------------------------------
        # 1. Generate content
        # ----------------------------------------------------

        print("\n[1/5] Generating content...", flush=True)

        content = generate_content()

        title = content["title"]
        script = content["script"]

        print("\n===== GENERATED CONTENT =====", flush=True)
        print(f"Title: {title}", flush=True)
        print(f"Script: {script}", flush=True)
        print("==============================", flush=True)

        # ----------------------------------------------------
        # 2. CTA
        # ----------------------------------------------------

        cta_text = (
            "Want to activate the Pocket Option AI Bot? "
            "Go to my channel, open the channel description, "
            "and click the Bot Activation button."
        )

        full_script = (
            script.strip()
            + " "
            + cta_text
        )

        print(
            "\nCTA:",
            "Go to the channel description and click the Bot Activation button.",
            flush=True
        )

        # ----------------------------------------------------
        # 3. Voice
        # ----------------------------------------------------

        print("\n[2/5] Generating voice...", flush=True)

        timestamp = int(time.time())

        voice_path = os.path.join(
            OUTPUT_DIR,
            f"voice_{timestamp}.mp3"
        )

        generate_voice(
            full_script,
            cta_text,
            voice_path
        )

        print(
            f"Voice created: {voice_path}",
            flush=True
        )

        # ----------------------------------------------------
        # 4. Random amount
        # ----------------------------------------------------

        short_amount = generate_demo_volume()

        # ----------------------------------------------------
        # 5. Generate video
        # ----------------------------------------------------

        print(
            "\n[3/5] Creating random-duration Short...",
            flush=True
        )

        video_filename = (
            f"short_{timestamp}.mp4"
        )

        video_path = generate_video(
            script=script,
            voice_path=voice_path,
            output_filename=video_filename,
            short_amount=short_amount
        )

        print(
            f"Video created: {video_path}",
            flush=True
        )

        # ----------------------------------------------------
        # 6. Upload to YouTube
        # ----------------------------------------------------

        print(
            "\n[4/5] Uploading to YouTube...",
            flush=True
        )

        upload_result = upload_short(
            video_path=video_path,
            title=title,
            description=YOUTUBE_DESCRIPTION
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        print("\n[5/5] COMPLETE", flush=True)

        print("\n" + "=" * 60, flush=True)
        print("SHORT CREATED SUCCESSFULLY", flush=True)
        print("=" * 60, flush=True)

        print(
            f"Title: {title}",
            flush=True
        )

        print(
            f"Video: {upload_result['url']}",
            flush=True
        )

        print(
            "Privacy: UNLISTED",
            flush=True
        )

        print(
            "CTA: 6-second activation CTA at the end",
            flush=True
        )

        print(
            "CTA message: Channel description → Bot Activation button",
            flush=True
        )

        print(
            "Red arrow: REMOVED",
            flush=True
        )

        print("=" * 60 + "\n", flush=True)

        return upload_result

    except Exception as e:

        print("\n" + "=" * 60, flush=True)
        print("SHORT CREATION FAILED", flush=True)
        print("=" * 60, flush=True)
        print(
            f"ERROR: {type(e).__name__}: {e}",
            flush=True
        )
        print("=" * 60 + "\n", flush=True)

        raise


# ============================================================
# BACKGROUND RUNNER
# ============================================================

def run_short_background(reason="MANUAL"):

    def worker():

        try:
            create_and_upload_short(reason)

        except Exception as e:

            print(
                f"Background Short failed: {e}",
                flush=True
            )

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "status": "online",
        "service": "Pocket Option YouTube Automation",
        "timezone": "Asia/Kolkata",
        "schedule": [
            "10:00 AM IST",
            "06:00 PM IST"
        ],
        "upload_privacy": "unlisted",
        "cta": "6-second Bot Activation CTA"
    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "healthy",
        "time": datetime.now(TIMEZONE).isoformat()
    })


# ============================================================
# MANUAL TEST
# ============================================================

@app.route("/run-test")
def run_test():

    print(
        "\nMANUAL TEST REQUEST RECEIVED",
        flush=True
    )

    run_short_background(
        "MANUAL TEST"
    )

    return jsonify({
        "status": "started",
        "message": "Short generation started in background.",
        "privacy": "unlisted"
    })


# ============================================================
# GOOGLE AUTHORIZATION
# ============================================================

@app.route("/authorize")
def authorize():

    global oauth_flow

    if not CLIENT_ID or not CLIENT_SECRET:
        return jsonify({
            "error": "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET missing"
        }), 500

    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                REDIRECT_URI
            ]
        }
    }

    oauth_flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = (
        oauth_flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
    )

    return redirect(
        authorization_url
    )


# ============================================================
# OAUTH CALLBACK
# ============================================================

@app.route("/oauth2callback")
def oauth2callback():

    global oauth_flow

    if oauth_flow is None:

        return jsonify({
            "error": "OAuth session expired. Open /authorize again."
        }), 400

    try:

        oauth_flow.fetch_token(
            authorization_response=request.url
        )

        credentials = oauth_flow.credentials

        token_file = os.path.join(
            DATA_DIR,
            "youtube_token.json"
        )

        import json

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        with open(
            token_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                token_data,
                file,
                indent=2
            )

        print(
            "YouTube OAuth token saved.",
            flush=True
        )

        return """
        <html>
        <body>
        <h2>YouTube authorization successful.</h2>
        <p>You can close this window.</p>
        </body>
        </html>
        """

    except Exception as e:

        print(
            f"OAuth callback error: {e}",
            flush=True
        )

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# SCHEDULER
# ============================================================

def scheduler_loop():

    print(
        "\n===== SCHEDULER STARTED =====",
        flush=True
    )

    print(
        "Schedule: 10:00 AM IST",
        flush=True
    )

    print(
        "Schedule: 06:00 PM IST",
        flush=True
    )

    last_run_date = None
    last_run_hour = None

    while True:

        try:

            now = datetime.now(TIMEZONE)

            current_date = now.date()
            current_hour = now.hour
            current_minute = now.minute

            should_run = (
                current_hour in [10, 18]
                and current_minute == 0
            )

            already_ran = (
                last_run_date == current_date
                and last_run_hour == current_hour
            )

            if should_run and not already_ran:

                if current_hour == 10:
                    reason = "SCHEDULED 10 AM IST"
                else:
                    reason = "SCHEDULED 6 PM IST"

                print(
                    f"\nSCHEDULE TRIGGERED: {reason}",
                    flush=True
                )

                run_short_background(
                    reason
                )

                last_run_date = current_date
                last_run_hour = current_hour

            time.sleep(20)

        except Exception as e:

            print(
                f"Scheduler error: {e}",
                flush=True
            )

            time.sleep(20)


# ============================================================
# HEARTBEAT
# ============================================================

def heartbeat_loop():

    while True:

        try:

            now = datetime.now(
                TIMEZONE
            )

            print(
                f"Heartbeat: {now.isoformat()}",
                flush=True
            )

        except Exception as e:

            print(
                f"Heartbeat error: {e}",
                flush=True
            )

        time.sleep(300)


# ============================================================
# START BACKGROUND TASKS
# ============================================================

scheduler_thread = threading.Thread(
    target=scheduler_loop,
    daemon=True
)

scheduler_thread.start()


heartbeat_thread = threading.Thread(
    target=heartbeat_loop,
    daemon=True
)

heartbeat_thread.start()


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    print(
        f"Starting server on port {port}",
        flush=True
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
