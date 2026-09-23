import os
import random
import threading
import time
import json

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, redirect, request
from google_auth_oauthlib.flow import Flow

from app.config import (
    YOUTUBE_DESCRIPTION,
)

from app.content import (
    generate_content,
)

from app.voice import (
    generate_voice,
)

from app.video import (
    generate_video,
)

from app.youtube import (
    upload_short,
    schedule_short,
    get_video_status,
)


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = "/app/data"

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

TIMEZONE = ZoneInfo(
    "Asia/Kolkata"
)

CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET"
)

REDIRECT_URI = (
    "https://pocket-option-youtube-automation-production.up.railway.app"
    "/oauth2callback"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


# ============================================================
# BUFFER SETTINGS
# ============================================================

BUFFER_FILE = os.path.join(
    DATA_DIR,
    "buffer_queue.json"
)

BUFFER_LOCK = threading.Lock()

BUFFER_TIMES = [
    (10, 0),
    (18, 0),
]

BUFFER_CHECK_SECONDS = 20


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__
)

oauth_flow = None


# ============================================================
# RANDOM TEST AMOUNT
# ============================================================

def generate_demo_volume():

    amount = random.randint(
        1000,
        2000
    )

    print(
        f"Random test amount generated: "
        f"${amount}",
        flush=True
    )

    return amount


# ============================================================
# BUFFER FILE HELPERS
# ============================================================

def load_buffer():

    if not os.path.exists(
        BUFFER_FILE
    ):

        return {
            "slots": []
        }

    try:

        with open(
            BUFFER_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict
        ):

            return {
                "slots": []
            }

        if "slots" not in data:

            data["slots"] = []

        return data

    except Exception as e:

        print(
            f"Buffer file read error: {e}",
            flush=True
        )

        return {
            "slots": []
        }


def save_buffer(
    data
):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    temp_file = (
        BUFFER_FILE
        + ".tmp"
    )

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp_file,
        BUFFER_FILE
    )


# ============================================================
# BUFFER CLEANUP
# ============================================================

def cleanup_old_buffer_slots(
    data
):

    now = datetime.now(
        TIMEZONE
    )

    cleaned = []

    for slot in data.get(
        "slots",
        []
    ):

        publish_at_string = (
            slot.get(
                "publish_at"
            )
        )

        if not publish_at_string:

            continue

        try:

            publish_at = (
                datetime.fromisoformat(
                    publish_at_string
                )
            )

        except Exception:

            continue

        # Keep current/future slots.
        # Keep past slots for 24 hours so
        # status information remains available.
        if publish_at >= (
            now - timedelta(hours=24)
        ):

            cleaned.append(
                slot
            )

    data["slots"] = cleaned

    return data


# ============================================================
# FIND BUFFER SLOT
# ============================================================

def find_slot(
    data,
    publish_at
):

    target = publish_at.isoformat()

    for slot in data.get(
        "slots",
        []
    ):

        if (
            slot.get(
                "publish_at"
            )
            == target
        ):

            return slot

    return None


# ============================================================
# TOMORROW'S SCHEDULE
# ============================================================

def get_tomorrow_slots():

    now = datetime.now(
        TIMEZONE
    )

    tomorrow = (
        now.date()
        + timedelta(days=1)
    )

    slots = []

    for hour, minute in BUFFER_TIMES:

        publish_at = datetime(
            tomorrow.year,
            tomorrow.month,
            tomorrow.day,
            hour,
            minute,
            tzinfo=TIMEZONE
        )

        slots.append(
            publish_at
        )

    return slots


# ============================================================
# CREATE + SCHEDULE ONE SHORT
# ============================================================

def create_and_schedule_short(
    publish_at,
    reason="BUFFER"
):

    print(
        "\n" + "=" * 60,
        flush=True
    )

    print(
        "STARTING BUFFER SHORT CREATION",
        flush=True
    )

    print(
        f"Reason: {reason}",
        flush=True
    )

    print(
        f"Target publish: "
        f"{publish_at.isoformat()}",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    timestamp = int(
        time.time()
    )

    try:

        # ====================================================
        # 1. CONTENT
        # ====================================================

        print(
            "\n[1/5] Generating content...",
            flush=True
        )

        content = generate_content()

        title = content[
            "title"
        ]

        script = content[
            "script"
        ]

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
        # 2. CTA
        # ====================================================

        cta_text = (
            "Go to my channel description "
            "and click the Bot Activation button."
        )

        full_script = (
            script.strip()
            + " "
            + cta_text
        )

        print(
            "\nCTA:",
            flush=True
        )

        print(
            "Go to my channel description "
            "and click the Bot Activation button.",
            flush=True
        )


        # ====================================================
        # 3. VOICE
        # ====================================================

        print(
            "\n[2/5] Generating voice...",
            flush=True
        )

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


        # ====================================================
        # 4. RANDOM AMOUNT
        # ====================================================

        short_amount = (
            generate_demo_volume()
        )


        # ====================================================
        # 5. VIDEO
        # ====================================================

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


        # ====================================================
        # 6. YOUTUBE SCHEDULE
        # ====================================================

        print(
            "\n[4/5] Uploading and scheduling to YouTube...",
            flush=True
        )

        upload_result = schedule_short(
            video_path=video_path,
            title=title,
            description=YOUTUBE_DESCRIPTION,
            publish_at=publish_at
        )


        # ====================================================
        # 7. SAVE BUFFER RECORD
        # ====================================================

        print(
            "\n[5/5] Saving buffer record...",
            flush=True
        )

        return {
            "title": title,
            "script": script,
            "video_path": video_path,
            "video_id": upload_result[
                "video_id"
            ],
            "url": upload_result[
                "url"
            ],
            "publish_at": publish_at.isoformat(),
            "privacy_status": "private",
            "created_at": datetime.now(
                TIMEZONE
            ).isoformat(),
            "status": "scheduled",
        }

    except Exception as e:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "BUFFER SHORT CREATION FAILED",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"ERROR: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        raise


# ============================================================
# FILL TOMORROW'S BUFFER
# ============================================================

def fill_tomorrow_buffer():

    with BUFFER_LOCK:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "CHECKING 1-DAY BUFFER",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        data = load_buffer()

        data = cleanup_old_buffer_slots(
            data
        )

        save_buffer(
            data
        )

        tomorrow_slots = (
            get_tomorrow_slots()
        )

        print(
            "\nTomorrow requires:",
            flush=True
        )

        for publish_at in tomorrow_slots:

            print(
                f"  - {publish_at.isoformat()}",
                flush=True
            )


        # ====================================================
        # PROCESS EACH SLOT
        # ====================================================

        for publish_at in tomorrow_slots:

            existing = find_slot(
                data,
                publish_at
            )

            # ------------------------------------------------
            # ALREADY SCHEDULED
            # ------------------------------------------------

            if existing:

                print(
                    "\nBUFFER SLOT ALREADY EXISTS",
                    flush=True
                )

                print(
                    f"Publish: "
                    f"{publish_at.isoformat()}",
                    flush=True
                )

                print(
                    f"Video ID: "
                    f"{existing.get('video_id')}",
                    flush=True
                )

                print(
                    f"Status: "
                    f"{existing.get('status')}",
                    flush=True
                )

                continue


            # ------------------------------------------------
            # CREATE NEW SHORT
            # ------------------------------------------------

            print(
                "\nBUFFER SLOT EMPTY",
                flush=True
            )

            print(
                f"Creating Short for: "
                f"{publish_at.isoformat()}",
                flush=True
            )

            try:

                result = (
                    create_and_schedule_short(
                        publish_at=publish_at,
                        reason=(
                            "1-DAY BUFFER"
                        )
                    )
                )

                data["slots"].append(
                    result
                )

                save_buffer(
                    data
                )

                print(
                    "\nBUFFER SLOT CREATED",
                    flush=True
                )

                print(
                    f"Title: "
                    f"{result['title']}",
                    flush=True
                )

                print(
                    f"Video ID: "
                    f"{result['video_id']}",
                    flush=True
                )

                print(
                    f"Publish: "
                    f"{result['publish_at']}",
                    flush=True
                )

                print(
                    "Status: SCHEDULED",
                    flush=True
                )

            except Exception as e:

                print(
                    "\nBUFFER SLOT FAILED",
                    flush=True
                )

                print(
                    f"Target: "
                    f"{publish_at.isoformat()}",
                    flush=True
                )

                print(
                    f"ERROR: "
                    f"{type(e).__name__}: {e}",
                    flush=True
                )

                # Continue to the second slot.
                # This means if 10 AM fails, 6 PM
                # can still be attempted.
                continue


        # ====================================================
        # FINAL BUFFER STATUS
        # ====================================================

        data = load_buffer()

        data = cleanup_old_buffer_slots(
            data
        )

        save_buffer(
            data
        )

        print(
            "\n===== BUFFER CHECK COMPLETE =====",
            flush=True
        )

        for publish_at in tomorrow_slots:

            slot = find_slot(
                data,
                publish_at
            )

            if slot:

                print(
                    f"✅ {publish_at.strftime('%Y-%m-%d %I:%M %p')}"
                    f" → {slot.get('status')}",
                    flush=True
                )

            else:

                print(
                    f"❌ {publish_at.strftime('%Y-%m-%d %I:%M %p')}"
                    f" → MISSING",
                    flush=True
                )

        print(
            "=================================",
            flush=True
        )


# ============================================================
# BUFFER BACKGROUND RUNNER
# ============================================================

def run_buffer_background(
    reason="BUFFER CHECK"
):

    def worker():

        try:

            print(
                f"\nStarting buffer background job: "
                f"{reason}",
                flush=True
            )

            fill_tomorrow_buffer()

        except Exception as e:

            print(
                f"Background buffer failed: "
                f"{type(e).__name__}: {e}",
                flush=True
            )

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()


# ============================================================
# MANUAL TEST SHORT
# ============================================================

def create_and_upload_short(
    reason="MANUAL TEST"
):

    print(
        "\n" + "=" * 60,
        flush=True
    )

    print(
        "STARTING MANUAL TEST SHORT CREATION",
        flush=True
    )

    print(
        f"Reason: {reason}",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    try:

        # ====================================================
        # 1. CONTENT
        # ====================================================

        print(
            "\n[1/5] Generating content...",
            flush=True
        )

        content = generate_content()

        title = content[
            "title"
        ]

        script = content[
            "script"
        ]

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
        # 2. CTA
        # ====================================================

        cta_text = (
            "Go to my channel description "
            "and click the Bot Activation button."
        )

        full_script = (
            script.strip()
            + " "
            + cta_text
        )

        print(
            "\nCTA:",
            flush=True
        )

        print(
            "Go to my channel description "
            "and click the Bot Activation button.",
            flush=True
        )


        # ====================================================
        # 3. VOICE
        # ====================================================

        print(
            "\n[2/5] Generating voice...",
            flush=True
        )

        timestamp = int(
            time.time()
        )

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


        # ====================================================
        # 4. RANDOM AMOUNT
        # ====================================================

        short_amount = (
            generate_demo_volume()
        )


        # ====================================================
        # 5. VIDEO
        # ====================================================

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


        # ====================================================
        # 6. YOUTUBE TEST UPLOAD
        # ====================================================

        print(
            "\n[4/5] Uploading to YouTube...",
            flush=True
        )

        upload_result = upload_short(
            video_path=video_path,
            title=title,
            description=YOUTUBE_DESCRIPTION
        )


        # ====================================================
        # SUCCESS
        # ====================================================

        print(
            "\n[5/5] COMPLETE",
            flush=True
        )

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "MANUAL TEST SHORT CREATED SUCCESSFULLY",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"Title: {title}",
            flush=True
        )

        print(
            f"Video: "
            f"{upload_result['url']}",
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
            "CTA: Channel description → "
            "Bot Activation button",
            flush=True
        )

        print(
            "Red arrow: REMOVED",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        return upload_result

    except Exception as e:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "MANUAL TEST SHORT FAILED",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"ERROR: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        raise


# ============================================================
# MANUAL TEST BACKGROUND
# ============================================================

def run_short_background(
    reason="MANUAL"
):

    def worker():

        try:

            create_and_upload_short(
                reason
            )

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

    return jsonify(
        {
            "status": "online",

            "service":
                "Pocket Option YouTube Automation",

            "timezone":
                "Asia/Kolkata",

            "schedule": [
                "Tomorrow 10:00 AM IST",
                "Tomorrow 06:00 PM IST"
            ],

            "buffer":
                "1-day advance",

            "automated_upload_privacy":
                "private + scheduled",

            "manual_test_privacy":
                "unlisted",

            "short_duration":
                "20-25 seconds",

            "normal_clips":
                4,

            "cta_duration":
                "6 seconds",

            "cta":
                "Channel description → "
                "Bot Activation button"
        }
    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify(
        {
            "status": "healthy",

            "time":
                datetime.now(
                    TIMEZONE
                ).isoformat(),

            "buffer":
                "1-day advance"
        }
    )


# ============================================================
# BUFFER STATUS
# ============================================================

@app.route("/buffer")
def buffer_status():

    data = load_buffer()

    data = cleanup_old_buffer_slots(
        data
    )

    save_buffer(
        data
    )

    return jsonify(
        {
            "status": "ok",

            "timezone":
                "Asia/Kolkata",

            "tomorrow_slots":
                get_tomorrow_slots(),

            "buffer":
                data
        }
    )


# ============================================================
# MANUALLY FILL BUFFER
# ============================================================

@app.route("/fill-buffer")
def fill_buffer():

    print(
        "\nMANUAL BUFFER FILL REQUEST RECEIVED",
        flush=True
    )

    run_buffer_background(
        "MANUAL BUFFER FILL"
    )

    return jsonify(
        {
            "status":
                "started",

            "message":
                "1-day buffer check started "
                "in background."
        }
    )


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

    return jsonify(
        {
            "status":
                "started",

            "message":
                "Short generation started "
                "in background.",

            "privacy":
                "unlisted"
        }
    )


# ============================================================
# GOOGLE AUTHORIZE
# ============================================================

@app.route("/authorize")
def authorize():

    global oauth_flow

    if not CLIENT_ID:

        return jsonify(
            {
                "error":
                    "GOOGLE_CLIENT_ID missing"
            }
        ), 500

    if not CLIENT_SECRET:

        return jsonify(
            {
                "error":
                    "GOOGLE_CLIENT_SECRET missing"
            }
        ), 500

    client_config = {
        "web": {

            "client_id":
                CLIENT_ID,

            "client_secret":
                CLIENT_SECRET,

            "auth_uri":
                "https://accounts.google.com/o/oauth2/auth",

            "token_uri":
                "https://oauth2.googleapis.com/token",

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

        return jsonify(
            {
                "error":
                    "OAuth session expired. "
                    "Open /authorize again."
            }
        ), 400

    try:

        oauth_flow.fetch_token(
            authorization_response=request.url
        )

        credentials = (
            oauth_flow.credentials
        )

        token_file = os.path.join(
            DATA_DIR,
            "youtube_token.json"
        )

        token_data = {
            "token":
                credentials.token,

            "refresh_token":
                credentials.refresh_token,

            "token_uri":
                credentials.token_uri,

            "client_id":
                credentials.client_id,

            "client_secret":
                credentials.client_secret,

            "scopes":
                credentials.scopes,
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

        return jsonify(
            {
                "error":
                    str(e)
            }
        ), 500


# ============================================================
# BUFFER SCHEDULER
# ============================================================

def scheduler_loop():

    print(
        "\n===== 1-DAY BUFFER SCHEDULER STARTED =====",
        flush=True
    )

    print(
        "Buffer target:",
        flush=True
    )

    print(
        "Tomorrow 10:00 AM IST",
        flush=True
    )

    print(
        "Tomorrow 06:00 PM IST",
        flush=True
    )

    print(
        "Scheduler check:",
        f"every {BUFFER_CHECK_SECONDS} seconds",
        flush=True
    )

    # --------------------------------------------------------
    # FIRST CHECK
    # --------------------------------------------------------

    # This means when Railway starts/restarts,
    # it immediately checks whether tomorrow's
    # two videos already exist.
    run_buffer_background(
        "STARTUP BUFFER CHECK"
    )

    while True:

        try:

            now = datetime.now(
                TIMEZONE
            )

            print(
                f"\nBuffer heartbeat: "
                f"{now.isoformat()}",
                flush=True
            )

            # ------------------------------------------------
            # CHECK BUFFER
            # ------------------------------------------------

            run_buffer_background(
                "AUTOMATIC BUFFER CHECK"
            )

            time.sleep(
                BUFFER_CHECK_SECONDS
            )

        except Exception as e:

            print(
                f"Buffer scheduler error: "
                f"{type(e).__name__}: {e}",
                flush=True
            )

            time.sleep(
                BUFFER_CHECK_SECONDS
            )


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
                f"Heartbeat: "
                f"{now.isoformat()}",
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
# START BACKGROUND THREADS
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
# SERVER
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
