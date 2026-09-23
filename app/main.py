import os
import random
import threading
import time
import json

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, redirect, request

from google_auth_oauthlib.flow import Flow

from app.config import YOUTUBE_DESCRIPTION
from app.content import generate_content
from app.voice import generate_voice
from app.video import generate_video
from app.youtube import (
    upload_short,
    schedule_short,
    get_video_status,
)

from app.telegram import (
    telegram_webhook,
    initialize_telegram,
    load_automation_state,
    record_error,
)


# ============================================================
# APP
# ============================================================

app = Flask(__name__)


# ============================================================
# PATHS
# ============================================================

DATA_DIR = "/app/data"

OUTPUT_DIR = os.path.join(
    DATA_DIR,
    "output"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# TIMEZONE
# ============================================================

IST = ZoneInfo(
    "Asia/Kolkata"
)


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
# OAUTH
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

REDIRECT_URI = (
    "https://pocket-option-youtube-automation-production.up.railway.app"
    "/oauth2callback"
)

oauth_flow = None


# ============================================================
# BASIC HELPERS
# ============================================================

def now_ist():

    return datetime.now(
        IST
    )


def iso_now():

    return now_ist().isoformat()


# ============================================================
# AUTOMATION STATE
# ============================================================

def automation_is_enabled():

    state = load_automation_state()

    return bool(
        state.get(
            "enabled",
            True
        )
    )


# ============================================================
# BUFFER LOAD
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

            data[
                "slots"
            ] = []

        return data

    except Exception as e:

        print(
            f"Buffer load error: {e}",
            flush=True
        )

        return {
            "slots": []
        }


# ============================================================
# BUFFER SAVE
# ============================================================

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
# CLEAN OLD BUFFER SLOTS
# ============================================================

def cleanup_old_buffer_slots(
    data
):

    cutoff = (
        now_ist()
        - timedelta(
            days=2
        )
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

            cleaned.append(
                slot
            )

            continue

        try:

            publish_at = (
                datetime.fromisoformat(
                    publish_at_string
                )
            )

        except Exception:

            cleaned.append(
                slot
            )

            continue

        if publish_at >= cutoff:

            cleaned.append(
                slot
            )

    data[
        "slots"
    ] = cleaned

    return data


# ============================================================
# FIND SLOT
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

        if slot.get(
            "publish_at"
        ) == target:

            return slot

    return None


# ============================================================
# TOMORROW SLOTS
# ============================================================

def get_tomorrow_slots():

    tomorrow = (
        now_ist().date()
        + timedelta(
            days=1
        )
    )

    slots = []

    for hour, minute in BUFFER_TIMES:

        publish_at = datetime(
            tomorrow.year,
            tomorrow.month,
            tomorrow.day,
            hour,
            minute,
            tzinfo=IST
        )

        slots.append(
            publish_at
        )

    return slots


# ============================================================
# CREATE + SCHEDULE SHORT
# ============================================================

def create_and_schedule_short(
    publish_at,
    reason="BUFFER"
):

    print(
        f"[{reason}] Creating Short for "
        f"{publish_at.isoformat()}",
        flush=True
    )

    # --------------------------------------------------------
    # CHECK AUTOMATION
    # --------------------------------------------------------

    if not automation_is_enabled():

        print(
            "Automation is PAUSED. "
            "Skipping video creation.",
            flush=True
        )

        return None


    # --------------------------------------------------------
    # GENERATE CONTENT
    # --------------------------------------------------------

    title, script = (
        generate_content()
    )

    print(
        f"[{reason}] Title: {title}",
        flush=True
    )


    # --------------------------------------------------------
    # CTA
    # --------------------------------------------------------

    cta_text = (
        "Go to my channel description "
        "and click the Bot Activation button."
    )


    # --------------------------------------------------------
    # RANDOM DEMO AMOUNT
    # --------------------------------------------------------

    short_amount = random.randint(
        1000,
        2000
    )


    # --------------------------------------------------------
    # GENERATE VOICE
    # --------------------------------------------------------

    timestamp = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S_%f"
        )
    )

    voice_path = os.path.join(
        OUTPUT_DIR,
        f"voice_{timestamp}.mp3"
    )

    generate_voice(
        script,
        cta_text,
        voice_path
    )


    # --------------------------------------------------------
    # GENERATE VIDEO
    # --------------------------------------------------------

    video_path = generate_video(
        script=script,
        voice_path=voice_path,
        short_amount=short_amount
    )


    # --------------------------------------------------------
    # SCHEDULE ON YOUTUBE
    # --------------------------------------------------------

    video_id = schedule_short(
        video_path=video_path,
        title=title,
        description=YOUTUBE_DESCRIPTION,
        publish_at=publish_at
    )


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    record = {

        "title": title,

        "script": script,

        "video_path": video_path,

        "video_id": video_id,

        "url":
            f"https://www.youtube.com/watch?v={video_id}",

        "publish_at":
            publish_at.isoformat(),

        "privacy_status":
            "private",

        "status":
            "scheduled",

        "created_at":
            iso_now(),

        "reason":
            reason,
    }


    print(
        f"[{reason}] Scheduled successfully: "
        f"{video_id}",
        flush=True
    )

    return record


# ============================================================
# FILL TOMORROW BUFFER
# ============================================================

def fill_tomorrow_buffer():

    with BUFFER_LOCK:

        if not automation_is_enabled():

            print(
                "BUFFER: automation paused; "
                "no new videos will be created.",
                flush=True
            )

            return


        data = load_buffer()

        data = cleanup_old_buffer_slots(
            data
        )

        tomorrow_slots = (
            get_tomorrow_slots()
        )


        for publish_at in tomorrow_slots:

            # ----------------------------------------------
            # CHECK AGAIN BEFORE EACH VIDEO
            # ----------------------------------------------

            if not automation_is_enabled():

                print(
                    "BUFFER: automation paused "
                    "during buffer fill.",
                    flush=True
                )

                break


            existing = find_slot(
                data,
                publish_at
            )

            if existing:

                print(
                    "BUFFER: slot already exists:",
                    publish_at.isoformat(),
                    flush=True
                )

                continue


            # ----------------------------------------------
            # CREATE VIDEO
            # ----------------------------------------------

            try:

                record = (
                    create_and_schedule_short(
                        publish_at,
                        reason="BUFFER"
                    )
                )

                if record:

                    data[
                        "slots"
                    ].append(
                        record
                    )

                    save_buffer(
                        data
                    )

            except Exception as e:

                print(
                    "BUFFER ERROR:",
                    repr(e),
                    flush=True
                )

                record_error(
                    e
                )

                # Continue to next slot
                continue


        save_buffer(
            data
        )

        print(
            "BUFFER CHECK COMPLETE",
            flush=True
        )

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            ),
            flush=True
        )


# ============================================================
# BUFFER BACKGROUND
# ============================================================

def run_buffer_background(
    reason="BUFFER"
):

    def worker():

        try:

            print(
                f"{reason}: starting",
                flush=True
            )

            fill_tomorrow_buffer()

            print(
                f"{reason}: finished",
                flush=True
            )

        except Exception as e:

            print(
                f"{reason} ERROR:",
                repr(e),
                flush=True
            )

            record_error(
                e
            )

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()


# ============================================================
# MANUAL TEST SHORT
# ============================================================

def create_and_upload_short():

    print(
        "MANUAL TEST: creating Short",
        flush=True
    )


    # --------------------------------------------------------
    # GENERATE CONTENT
    # --------------------------------------------------------

    title, script = (
        generate_content()
    )


    # --------------------------------------------------------
    # CTA
    # --------------------------------------------------------

    cta_text = (
        "Go to my channel description "
        "and click the Bot Activation button."
    )


    # --------------------------------------------------------
    # RANDOM AMOUNT
    # --------------------------------------------------------

    short_amount = random.randint(
        1000,
        2000
    )


    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    timestamp = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S_%f"
        )
    )

    voice_path = os.path.join(
        OUTPUT_DIR,
        f"test_voice_{timestamp}.mp3"
    )


    generate_voice(
        script,
        cta_text,
        voice_path
    )


    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    video_path = generate_video(
        script=script,
        voice_path=voice_path,
        short_amount=short_amount
    )


    # --------------------------------------------------------
    # MANUAL UPLOAD = UNLISTED
    # --------------------------------------------------------

    video_id = upload_short(
        video_path=video_path,
        title=title,
        description=YOUTUBE_DESCRIPTION
    )


    result = {

        "title": title,

        "video_id": video_id,

        "url":
            f"https://www.youtube.com/watch?v={video_id}",

        "privacy_status":
            "unlisted",

        "created_at":
            iso_now(),
    }


    print(
        "MANUAL TEST COMPLETE:",
        json.dumps(
            result,
            indent=2
        ),
        flush=True
    )

    return result


# ============================================================
# MANUAL TEST BACKGROUND
# ============================================================

def run_short_background(
    reason="MANUAL TEST"
):

    def worker():

        try:

            print(
                f"{reason}: started",
                flush=True
            )

            create_and_upload_short()

            print(
                f"{reason}: finished",
                flush=True
            )

        except Exception as e:

            print(
                f"{reason} ERROR:",
                repr(e),
                flush=True
            )

            record_error(
                e
            )

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()


# ============================================================
# UPDATE YOUTUBE STATUSES
# ============================================================

def update_buffer_video_statuses():

    data = load_buffer()

    changed = False

    for slot in data.get(
        "slots",
        []
    ):

        video_id = slot.get(
            "video_id"
        )

        if not video_id:

            continue

        try:

            status = get_video_status(
                video_id
            )

            if not status:

                continue


            old_status = slot.get(
                "status"
            )


            # ------------------------------------------------
            # SCHEDULED / PUBLISHED
            # ------------------------------------------------

            privacy_status = (
                status.get(
                    "privacy_status"
                )
            )

            published_at = (
                status.get(
                    "published_at"
                )
            )

            upload_status = (
                status.get(
                    "upload_status"
                )
            )

            processing_status = (
                status.get(
                    "processing_status"
                )
            )


            if published_at:

                slot[
                    "status"
                ] = "published"

                slot[
                    "published_at"
                ] = published_at

            elif privacy_status == "private":

                slot[
                    "status"
                ] = "scheduled"

            elif upload_status == "failed":

                slot[
                    "status"
                ] = "failed"

            else:

                slot[
                    "status"
                ] = (
                    processing_status
                    or
                    privacy_status
                    or
                    "unknown"
                )


            slot[
                "youtube_status"
            ] = status


            if slot.get(
                "status"
            ) != old_status:

                changed = True


        except Exception as e:

            print(
                f"YouTube status check error "
                f"for {video_id}: {e}",
                flush=True
            )

            record_error(
                e
            )


    if changed:

        save_buffer(
            data
        )


# ============================================================
# YOUTUBE MONITOR
# ============================================================

def youtube_monitor_loop():

    print(
        "YouTube monitor started.",
        flush=True
    )

    while True:

        try:

            update_buffer_video_statuses()

        except Exception as e:

            print(
                "YouTube monitor error:",
                repr(e),
                flush=True
            )

            record_error(
                e
            )

        time.sleep(
            60
        )


# ============================================================
# SCHEDULER
# ============================================================

def scheduler_loop():

    print(
        "Buffer scheduler started.",
        flush=True
    )


    # --------------------------------------------------------
    # STARTUP CHECK
    # --------------------------------------------------------

    run_buffer_background(
        "STARTUP BUFFER CHECK"
    )


    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    while True:

        try:

            if automation_is_enabled():

                run_buffer_background(
                    "AUTOMATIC BUFFER CHECK"
                )

            else:

                print(
                    "Scheduler: automation paused.",
                    flush=True
                )


        except Exception as e:

            print(
                "Scheduler error:",
                repr(e),
                flush=True
            )

            record_error(
                e
            )


        time.sleep(
            BUFFER_CHECK_SECONDS
        )


# ============================================================
# HEARTBEAT
# ============================================================

def heartbeat_loop():

    print(
        "Heartbeat started.",
        flush=True
    )

    while True:

        try:

            state = load_automation_state()

            status = (
                "LIVE"
                if state.get(
                    "enabled",
                    True
                )
                else
                "PAUSED"
            )

            print(
                f"HEARTBEAT | "
                f"{iso_now()} | "
                f"AUTOMATION={status}",
                flush=True
            )

        except Exception as e:

            print(
                "Heartbeat error:",
                repr(e),
                flush=True
            )

        time.sleep(
            300
        )


# ============================================================
# TELEGRAM WEBHOOK ROUTE
# ============================================================

@app.route(
    "/telegram/webhook/<secret>",
    methods=["POST"]
)
def telegram_webhook_route(
    secret
):

    expected_secret = os.getenv(
        "TELEGRAM_WEBHOOK_SECRET",
        "pocket-option-telegram-secure"
    )


    if secret != expected_secret:

        return jsonify({
            "ok": False,
            "error": "Unauthorized"
        }), 403


    return jsonify(
        telegram_webhook(
            request
        )
    )


# ============================================================
# HOME
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    state = load_automation_state()

    buffer_data = load_buffer()

    return jsonify({

        "service":
            "Pocket Option YouTube Automation",

        "status":
            "running",

        "automation":
            (
                "LIVE"
                if state.get(
                    "enabled",
                    True
                )
                else
                "PAUSED"
            ),

        "buffer_mode":
            "1-day advance buffer",

        "scheduled_times":
            [
                "10:00 IST",
                "18:00 IST"
            ],

        "automated_privacy":
            "private + scheduled publishAt",

        "manual_test_privacy":
            "unlisted",

        "buffer_slots":
            len(
                buffer_data.get(
                    "slots",
                    []
                )
            ),

        "telegram":
            bool(
                os.getenv(
                    "TELEGRAM_BOT_TOKEN"
                )
                and
                os.getenv(
                    "TELEGRAM_ADMIN_CHAT_ID"
                )
            )
    })


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    state = load_automation_state()

    return jsonify({

        "ok":
            True,

        "service":
            "youtube-automation",

        "automation":
            (
                "LIVE"
                if state.get(
                    "enabled",
                    True
                )
                else
                "PAUSED"
            ),

        "youtube_token":
            os.path.exists(
                "/app/data/youtube_token.json"
            ),

        "gemini_key":
            bool(
                os.getenv(
                    "GEMINI_API_KEY"
                )
            ),

        "elevenlabs_key":
            bool(
                os.getenv(
                    "ELEVENLABS_API_KEY"
                )
            ),

        "telegram":
            bool(
                os.getenv(
                    "TELEGRAM_BOT_TOKEN"
                )
                and
                os.getenv(
                    "TELEGRAM_ADMIN_CHAT_ID"
                )
            ),

        "time":
            iso_now()
    })


# ============================================================
# BUFFER ENDPOINT
# ============================================================

@app.route(
    "/buffer",
    methods=["GET"]
)
def buffer_endpoint():

    return jsonify(
        load_buffer()
    )


# ============================================================
# FILL BUFFER ENDPOINT
# ============================================================

@app.route(
    "/fill-buffer",
    methods=["GET"]
)
def fill_buffer_endpoint():

    if not automation_is_enabled():

        return jsonify({

            "ok":
                False,

            "message":
                "Automation is currently paused."
        })


    run_buffer_background(
        "MANUAL BUFFER FILL"
    )

    return jsonify({

        "ok":
            True,

        "message":
            "Buffer check started."
    })


# ============================================================
# MANUAL TEST ENDPOINT
# ============================================================

@app.route(
    "/run-test",
    methods=["GET"]
)
def run_test_endpoint():

    run_short_background(
        "MANUAL TEST"
    )

    return jsonify({

        "ok":
            True,

        "message":
            "Manual test started.",

        "privacy":
            "unlisted"
    })


# ============================================================
# OAUTH AUTHORIZE
# ============================================================

@app.route(
    "/authorize",
    methods=["GET"]
)
def authorize():

    global oauth_flow

    client_id = os.getenv(
        "GOOGLE_CLIENT_ID"
    )

    client_secret = os.getenv(
        "GOOGLE_CLIENT_SECRET"
    )


    if not client_id or not client_secret:

        return (
            "Missing GOOGLE_CLIENT_ID "
            "or GOOGLE_CLIENT_SECRET.",
            500
        )


    client_config = {

        "web": {

            "client_id":
                client_id,

            "client_secret":
                client_secret,

            "auth_uri":
                "https://accounts.google.com/o/oauth2/auth",

            "token_uri":
                "https://oauth2.googleapis.com/token",

            "redirect_uris": [
                REDIRECT_URI
            ]
        }
    }


    oauth_flow = (
        Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
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

@app.route(
    "/oauth2callback",
    methods=["GET"]
)
def oauth2callback():

    global oauth_flow

    if oauth_flow is None:

        return (
            "OAuth flow expired. "
            "Open /authorize again.",
            400
        )


    try:

        oauth_flow.fetch_token(
            authorization_response=request.url
        )

        credentials = (
            oauth_flow.credentials
        )


        token_path = (
            "/app/data/youtube_token.json"
        )


        os.makedirs(
            "/app/data",
            exist_ok=True
        )


        with open(
            token_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                credentials.to_json()
            )


        oauth_flow = None


        return (
            "YouTube authorization successful. "
            "Token saved."
        )


    except Exception as e:

        print(
            "OAuth callback error:",
            repr(e),
            flush=True
        )

        record_error(
            e
        )

        return (
            f"OAuth error: {e}",
            500
        )


# ============================================================
# START BACKGROUND THREADS
# ============================================================

def start_background_threads():

    # --------------------------------------------------------
    # BUFFER SCHEDULER
    # --------------------------------------------------------

    scheduler_thread = threading.Thread(
        target=scheduler_loop,
        daemon=True
    )

    scheduler_thread.start()


    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------

    heartbeat_thread = threading.Thread(
        target=heartbeat_loop,
        daemon=True
    )

    heartbeat_thread.start()


    # --------------------------------------------------------
    # YOUTUBE MONITOR
    # --------------------------------------------------------

    monitor_thread = threading.Thread(
        target=youtube_monitor_loop,
        daemon=True
    )

    monitor_thread.start()


# ============================================================
# TELEGRAM INITIALIZATION
# ============================================================

def start_telegram():

    public_base_url = (
        "https://pocket-option-youtube-automation-production.up.railway.app"
    )

    initialize_telegram(
        public_base_url
    )


# ============================================================
# START EVERYTHING
# ============================================================

start_background_threads()

telegram_thread = threading.Thread(
    target=start_telegram,
    daemon=True
)

telegram_thread.start()


# ============================================================
# FLASK
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
