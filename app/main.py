import os
import random
import shutil
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
from app.video import (
    generate_video,
    ASSETS_DIR,
    CTA_SOURCE,
    RANDOM_VIDEO_FILES,
)
from app.youtube import upload_short, schedule_short, get_video_status
from app.telegram import (
    telegram_webhook,
    initialize_telegram,
    load_automation_state,
    record_error,
)


# ============================================================
# APP / PATHS
# ============================================================

app = Flask(__name__)

DATA_DIR = "/app/data"
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
BUFFER_FILE = os.path.join(DATA_DIR, "buffer_queue.json")
YOUTUBE_TOKEN_FILE = os.path.join(DATA_DIR, "youtube_token.json")
PIPER_MODEL_FILE = "/app/voices/en_US-lessac-medium.onnx"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# TIME / SCHEDULER SETTINGS
# ============================================================

IST = ZoneInfo("Asia/Kolkata")

BUFFER_TIMES = [
    (10, 0),
    (18, 0),
]

# Daily creation time: 10:00 PM IST.
CREATION_HOUR_IST = 22
CREATION_MINUTE_IST = 0

# Recovery behavior:
# - after 10 PM -> ensure tomorrow 10 AM + 6 PM
# - after midnight but before 10 AM -> ensure today's 10 AM + 6 PM
# - after 10 AM but before 6 PM -> ensure today's 6 PM
# This protects the schedule if Railway or an API was down at 10 PM.
SCHEDULER_CHECK_SECONDS = 60
FAILED_RETRY_COOLDOWN_SECONDS = 300
MIN_SCHEDULE_LEAD_MINUTES = 5
YOUTUBE_MONITOR_SECONDS = 600

BUFFER_LOCK = threading.Lock()
JOB_LOCK = threading.Lock()
THREAD_START_LOCK = threading.Lock()
BACKGROUND_THREADS_STARTED = False

_last_failed_fill_monotonic = 0.0


# ============================================================
# OAUTH
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

PUBLIC_BASE_URL = (
    "https://pocket-option-youtube-automation-production.up.railway.app"
)
REDIRECT_URI = PUBLIC_BASE_URL + "/oauth2callback"
oauth_flow = None


# ============================================================
# BASIC HELPERS
# ============================================================

def now_ist():
    return datetime.now(IST)


def iso_now():
    return now_ist().isoformat()


def automation_is_enabled():
    state = load_automation_state()
    return bool(state.get("enabled", True))


def safe_remove(path):
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:
        print(f"Cleanup warning for {path}: {exc}", flush=True)


# ============================================================
# BUFFER STORAGE
# ============================================================

def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        return {"slots": []}

    try:
        with open(BUFFER_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {"slots": []}

        if not isinstance(data.get("slots"), list):
            data["slots"] = []

        return data

    except Exception as exc:
        print(f"Buffer load error: {exc}", flush=True)
        return {"slots": []}


def save_buffer(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = BUFFER_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    os.replace(temp_file, BUFFER_FILE)


def cleanup_old_buffer_slots(data):
    cutoff = now_ist() - timedelta(days=3)
    cleaned = []

    for slot in data.get("slots", []):
        publish_at_string = slot.get("publish_at")

        if not publish_at_string:
            cleaned.append(slot)
            continue

        try:
            publish_at = datetime.fromisoformat(publish_at_string)
        except Exception:
            cleaned.append(slot)
            continue

        if publish_at >= cutoff:
            cleaned.append(slot)

    data["slots"] = cleaned
    return data


def find_slot(data, publish_at):
    target = publish_at.isoformat()
    for slot in data.get("slots", []):
        if slot.get("publish_at") == target:
            return slot
    return None


def get_slots_for_date(target_date):
    return [
        datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            tzinfo=IST,
        )
        for hour, minute in BUFFER_TIMES
    ]


def get_tomorrow_slots():
    return get_slots_for_date(now_ist().date() + timedelta(days=1))


def get_required_scheduler_slots(current_time=None):
    """
    Return only the publish slots that should exist right now.

    Normal run:
      22:00-23:59 -> tomorrow 10:00 and 18:00.

    Recovery:
      00:00-09:59 -> today 10:00 and 18:00.
      10:00-17:59 -> today 18:00.
      18:00-21:59 -> nothing left today; wait for 22:00.
    """
    current_time = current_time or now_ist()
    today = current_time.date()

    if current_time.hour >= CREATION_HOUR_IST:
        candidates = get_slots_for_date(today + timedelta(days=1))
    elif current_time.hour < 10:
        candidates = get_slots_for_date(today)
    elif current_time.hour < 18:
        candidates = [
            datetime(
                today.year,
                today.month,
                today.day,
                18,
                0,
                tzinfo=IST,
            )
        ]
    else:
        candidates = []

    minimum_publish_time = current_time + timedelta(
        minutes=MIN_SCHEDULE_LEAD_MINUTES
    )

    return [
        slot for slot in candidates
        if slot > minimum_publish_time
    ]


def missing_slots(slots, data=None):
    data = data or load_buffer()
    return [
        slot for slot in slots
        if find_slot(data, slot) is None
    ]


# ============================================================
# PREFLIGHT
# ============================================================

def preflight_status():
    available_clips = [
        filename
        for filename in RANDOM_VIDEO_FILES
        if os.path.exists(os.path.join(ASSETS_DIR, filename))
    ]

    return {
        "youtube_token": os.path.exists(YOUTUBE_TOKEN_FILE),
        "cta_video": os.path.exists(CTA_SOURCE),
        "normal_clips_found": len(available_clips),
        "normal_clips_required": 4,
        "piper_model": os.path.exists(PIPER_MODEL_FILE),
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "piper": shutil.which("piper") is not None,
        "gemini_key_present": bool(os.getenv("GEMINI_API_KEY")),
        "elevenlabs_key_present": bool(os.getenv("ELEVENLABS_API_KEY")),
    }


def ensure_preflight_ready():
    status = preflight_status()
    critical_failures = []

    if not status["youtube_token"]:
        critical_failures.append("YouTube token is missing")

    if not status["cta_video"]:
        critical_failures.append("activation_cta.mp4 is missing")

    if status["normal_clips_found"] < status["normal_clips_required"]:
        critical_failures.append(
            f"Only {status['normal_clips_found']} normal clips are available"
        )

    if not status["ffmpeg"]:
        critical_failures.append("ffmpeg is missing")

    if not status["ffprobe"]:
        critical_failures.append("ffprobe is missing")

    if not status["piper_model"] or not status["piper"]:
        critical_failures.append("Piper fallback voice is unavailable")

    if critical_failures:
        raise RuntimeError(
            "Preflight failed: " + "; ".join(critical_failures)
        )

    return status


# ============================================================
# CREATE + SCHEDULE SHORT
# ============================================================

def create_and_schedule_short(publish_at, reason="BUFFER"):
    if not automation_is_enabled():
        print("Automation is PAUSED. Skipping video creation.", flush=True)
        return None

    if publish_at.tzinfo is None:
        raise ValueError("publish_at must contain timezone information.")

    if publish_at <= now_ist() + timedelta(minutes=MIN_SCHEDULE_LEAD_MINUTES):
        raise RuntimeError(
            f"Publish time is too close or already passed: {publish_at.isoformat()}"
        )

    ensure_preflight_ready()

    print(
        f"[{reason}] Creating Short for {publish_at.isoformat()}",
        flush=True,
    )

    title, script = generate_content()
    print(f"[{reason}] Title: {title}", flush=True)

    cta_text = (
        "Go to my channel description and click the Bot Activation button."
    )
    short_amount = random.randint(1000, 2000)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    unique_name = f"{publish_at.strftime('%Y%m%d_%H%M')}_{timestamp}"

    voice_path = os.path.join(
        OUTPUT_DIR,
        f"voice_{unique_name}.mp3",
    )
    video_filename = f"short_{unique_name}.mp4"
    video_path = None

    try:
        generate_voice(
            script,
            cta_text,
            voice_path,
        )

        video_path = generate_video(
            script=script,
            voice_path=voice_path,
            short_amount=short_amount,
            output_filename=video_filename,
        )

        video_id = schedule_short(
            video_path=video_path,
            title=title,
            description=YOUTUBE_DESCRIPTION,
            publish_at=publish_at,
        )

        record = {
            "title": title,
            "script": script,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "publish_at": publish_at.isoformat(),
            "privacy_status": "private",
            "status": "scheduled",
            "created_at": iso_now(),
            "reason": reason,
            "demo_amount": short_amount,
        }

        print(
            f"[{reason}] Scheduled successfully: {video_id}",
            flush=True,
        )
        return record

    finally:
        safe_remove(voice_path)
        safe_remove(os.path.splitext(voice_path)[0] + ".json")
        safe_remove(video_path)


# ============================================================
# BUFFER FILL
# ============================================================

def fill_slots(target_slots, reason="BUFFER"):
    if not target_slots:
        return {"created": 0, "existing": 0, "failed": 0}

    if not JOB_LOCK.acquire(blocking=False):
        print(f"{reason}: another video job is already running.", flush=True)
        return {"busy": True}

    try:
        if not automation_is_enabled():
            print(f"{reason}: automation is paused.", flush=True)
            return {"paused": True}

        with BUFFER_LOCK:
            data = cleanup_old_buffer_slots(load_buffer())
            save_buffer(data)

        created = 0
        existing_count = 0
        failed = 0

        for publish_at in target_slots:
            if not automation_is_enabled():
                print(f"{reason}: automation paused during fill.", flush=True)
                break

            if publish_at <= now_ist() + timedelta(
                minutes=MIN_SCHEDULE_LEAD_MINUTES
            ):
                print(
                    f"{reason}: skipping past/too-close slot "
                    f"{publish_at.isoformat()}",
                    flush=True,
                )
                continue

            with BUFFER_LOCK:
                data = cleanup_old_buffer_slots(load_buffer())
                existing = find_slot(data, publish_at)

            if existing:
                existing_count += 1
                print(
                    f"{reason}: slot already exists: {publish_at.isoformat()}",
                    flush=True,
                )
                continue

            try:
                record = create_and_schedule_short(
                    publish_at,
                    reason=reason,
                )

                if record:
                    with BUFFER_LOCK:
                        data = cleanup_old_buffer_slots(load_buffer())

                        if not find_slot(data, publish_at):
                            data["slots"].append(record)
                            save_buffer(data)

                    created += 1

            except Exception as exc:
                failed += 1
                print(
                    f"{reason} ERROR for {publish_at.isoformat()}: {repr(exc)}",
                    flush=True,
                )
                record_error(exc)

        print(
            f"{reason} COMPLETE | created={created} "
            f"existing={existing_count} failed={failed}",
            flush=True,
        )

        return {
            "created": created,
            "existing": existing_count,
            "failed": failed,
        }

    finally:
        JOB_LOCK.release()


def run_buffer_background(target_slots, reason="BUFFER"):
    def worker():
        try:
            print(f"{reason}: starting", flush=True)
            fill_slots(target_slots, reason=reason)
            print(f"{reason}: finished", flush=True)
        except Exception as exc:
            print(f"{reason} ERROR: {repr(exc)}", flush=True)
            record_error(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


# ============================================================
# MANUAL TEST SHORT
# ============================================================

def create_and_upload_short():
    ensure_preflight_ready()

    title, script = generate_content()

    cta_text = (
        "Go to my channel description and click the Bot Activation button."
    )
    short_amount = random.randint(1000, 2000)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    voice_path = os.path.join(
        OUTPUT_DIR,
        f"test_voice_{timestamp}.mp3",
    )
    video_path = None

    try:
        generate_voice(
            script,
            cta_text,
            voice_path,
        )

        video_path = generate_video(
            script=script,
            voice_path=voice_path,
            short_amount=short_amount,
            output_filename=f"test_short_{timestamp}.mp4",
        )

        video_id = upload_short(
            video_path=video_path,
            title=title,
            description=YOUTUBE_DESCRIPTION,
        )

        result = {
            "title": title,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "privacy_status": "unlisted",
            "created_at": iso_now(),
        }

        print(
            "MANUAL TEST COMPLETE: "
            + json.dumps(result, indent=2),
            flush=True,
        )
        return result

    finally:
        safe_remove(voice_path)
        safe_remove(os.path.splitext(voice_path)[0] + ".json")
        safe_remove(video_path)


def run_short_background(reason="MANUAL TEST"):
    def worker():
        if not JOB_LOCK.acquire(blocking=False):
            print(f"{reason}: another video job is already running.", flush=True)
            return

        try:
            print(f"{reason}: started", flush=True)
            create_and_upload_short()
            print(f"{reason}: finished", flush=True)
        except Exception as exc:
            print(f"{reason} ERROR: {repr(exc)}", flush=True)
            record_error(exc)
        finally:
            JOB_LOCK.release()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


# ============================================================
# YOUTUBE STATUS MONITOR
# ============================================================

def update_buffer_video_statuses():
    with BUFFER_LOCK:
        data = cleanup_old_buffer_slots(load_buffer())

    changed = False

    for slot in data.get("slots", []):
        video_id = slot.get("video_id")

        if not video_id or not isinstance(video_id, str):
            continue

        try:
            status = get_video_status(video_id)
            if not status:
                continue

            old_status = slot.get("status")
            privacy_status = status.get("privacy_status")
            published_at = status.get("published_at")
            upload_status = status.get("upload_status")
            processing_status = status.get("processing_status")

            if published_at and privacy_status == "public":
                slot["status"] = "published"
                slot["published_at"] = published_at
            elif privacy_status == "private":
                slot["status"] = "scheduled"
            elif upload_status == "failed":
                slot["status"] = "failed"
            else:
                slot["status"] = (
                    processing_status
                    or privacy_status
                    or "unknown"
                )

            slot["youtube_status"] = status

            if slot.get("status") != old_status:
                changed = True

        except Exception as exc:
            print(
                f"YouTube status check error for {video_id}: {exc}",
                flush=True,
            )
            record_error(exc)

    if changed:
        with BUFFER_LOCK:
            save_buffer(data)


def youtube_monitor_loop():
    print("YouTube monitor started.", flush=True)

    while True:
        try:
            update_buffer_video_statuses()
        except Exception as exc:
            print(f"YouTube monitor error: {repr(exc)}", flush=True)
            record_error(exc)

        time.sleep(YOUTUBE_MONITOR_SECONDS)


# ============================================================
# ROBUST 10 PM SCHEDULER + CATCH-UP
# ============================================================

def scheduler_loop():
    global _last_failed_fill_monotonic

    print("10 PM buffer scheduler started.", flush=True)
    print(
        "Automatic creation time: 10:00 PM IST | "
        "Publish times: 10:00 AM and 6:00 PM IST",
        flush=True,
    )
    print(
        "Recovery mode is enabled for Railway/API outages.",
        flush=True,
    )

    while True:
        try:
            current_time = now_ist()

            if not automation_is_enabled():
                time.sleep(SCHEDULER_CHECK_SECONDS)
                continue

            target_slots = get_required_scheduler_slots(current_time)
            missing = missing_slots(target_slots)

            if missing:
                since_last_failure = (
                    time.monotonic() - _last_failed_fill_monotonic
                )

                if (
                    _last_failed_fill_monotonic == 0.0
                    or since_last_failure >= FAILED_RETRY_COOLDOWN_SECONDS
                ):
                    print(
                        "Scheduler found missing required slots: "
                        + ", ".join(slot.isoformat() for slot in missing),
                        flush=True,
                    )

                    result = fill_slots(
                        missing,
                        reason="AUTO BUFFER",
                    )

                    if result.get("failed", 0) > 0:
                        _last_failed_fill_monotonic = time.monotonic()
                        print(
                            "Automatic fill had an error. "
                            "Retrying after 5 minutes.",
                            flush=True,
                        )
                    else:
                        _last_failed_fill_monotonic = 0.0

        except Exception as exc:
            _last_failed_fill_monotonic = time.monotonic()
            print(f"Scheduler error: {repr(exc)}", flush=True)
            record_error(exc)

        time.sleep(SCHEDULER_CHECK_SECONDS)


# ============================================================
# HEARTBEAT
# ============================================================

def heartbeat_loop():
    print("Heartbeat started.", flush=True)

    while True:
        try:
            state = load_automation_state()
            status = "LIVE" if state.get("enabled", True) else "PAUSED"
            required = get_required_scheduler_slots(now_ist())
            missing = missing_slots(required)
            print(
                f"HEARTBEAT | {iso_now()} | AUTOMATION={status} | "
                f"missing_required_slots={len(missing)}",
                flush=True,
            )
        except Exception as exc:
            print(f"Heartbeat error: {repr(exc)}", flush=True)

        time.sleep(300)


# ============================================================
# ROUTES
# ============================================================

@app.route("/telegram/webhook/<secret>", methods=["POST"])
def telegram_webhook_route(secret):
    expected_secret = os.getenv(
        "TELEGRAM_WEBHOOK_SECRET",
        "pocket-option-telegram-secure",
    )

    if secret != expected_secret:
        return jsonify({"ok": False, "error": "Unauthorized"}), 403

    return jsonify(telegram_webhook(request))


@app.route("/", methods=["GET"])
def home():
    state = load_automation_state()
    buffer_data = load_buffer()

    return jsonify({
        "service": "Pocket Option YouTube Automation",
        "status": "running",
        "automation": (
            "LIVE" if state.get("enabled", True) else "PAUSED"
        ),
        "creation_time": "22:00 IST",
        "publish_times": ["10:00 IST", "18:00 IST"],
        "buffer_mode": "1-day advance + outage catch-up",
        "automated_privacy": "private + scheduled publishAt",
        "manual_test_privacy": "unlisted",
        "buffer_slots": len(buffer_data.get("slots", [])),
        "telegram": bool(
            os.getenv("TELEGRAM_BOT_TOKEN")
            and os.getenv("TELEGRAM_ADMIN_CHAT_ID")
        ),
    })


@app.route("/health", methods=["GET"])
def health():
    state = load_automation_state()
    required = get_required_scheduler_slots(now_ist())
    data = load_buffer()
    missing = missing_slots(required, data)
    preflight = preflight_status()

    internal_ready = (
        preflight["cta_video"]
        and preflight["normal_clips_found"] >= 4
        and preflight["piper_model"]
        and preflight["ffmpeg"]
        and preflight["ffprobe"]
        and preflight["piper"]
    )

    return jsonify({
        "ok": internal_ready,
        "service": "youtube-automation",
        "automation": (
            "LIVE" if state.get("enabled", True) else "PAUSED"
        ),
        "creation_time": "22:00 IST",
        "publish_times": ["10:00 IST", "18:00 IST"],
        "recovery_mode": True,
        "youtube_token": preflight["youtube_token"],
        "gemini_key_present": preflight["gemini_key_present"],
        "elevenlabs_key_present": preflight["elevenlabs_key_present"],
        "piper_fallback_ready": (
            preflight["piper_model"] and preflight["piper"]
        ),
        "cta_video_ready": preflight["cta_video"],
        "normal_clips_found": preflight["normal_clips_found"],
        "internal_runtime_ready": internal_ready,
        "required_slots_now": [
            slot.isoformat() for slot in required
        ],
        "missing_required_slots": [
            slot.isoformat() for slot in missing
        ],
        "time": iso_now(),
    })


@app.route("/buffer", methods=["GET"])
def buffer_endpoint():
    return jsonify(load_buffer())


@app.route("/fill-buffer", methods=["GET"])
def fill_buffer_endpoint():
    if not automation_is_enabled():
        return jsonify({
            "ok": False,
            "message": "Automation is currently paused.",
        })

    slots = get_tomorrow_slots()
    run_buffer_background(
        slots,
        "MANUAL TOMORROW BUFFER FILL",
    )

    return jsonify({
        "ok": True,
        "message": "Tomorrow buffer check started.",
        "slots": [slot.isoformat() for slot in slots],
    })


@app.route("/fill-required", methods=["GET"])
def fill_required_endpoint():
    if not automation_is_enabled():
        return jsonify({
            "ok": False,
            "message": "Automation is currently paused.",
        })

    slots = get_required_scheduler_slots(now_ist())
    run_buffer_background(
        slots,
        "MANUAL RECOVERY FILL",
    )

    return jsonify({
        "ok": True,
        "message": "Required-slot recovery check started.",
        "slots": [slot.isoformat() for slot in slots],
    })


@app.route("/run-test", methods=["GET"])
def run_test_endpoint():
    run_short_background("MANUAL TEST")
    return jsonify({
        "ok": True,
        "message": "Manual test started.",
        "privacy": "unlisted",
    })


# ============================================================
# YOUTUBE OAUTH
# ============================================================

@app.route("/authorize", methods=["GET"])
def authorize():
    global oauth_flow

    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return (
            "Missing YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET.",
            500,
        )

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }

    oauth_flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    authorization_url, _state = oauth_flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return redirect(authorization_url)


@app.route("/oauth2callback", methods=["GET"])
def oauth2callback():
    global oauth_flow

    if oauth_flow is None:
        return (
            "OAuth flow expired. Open /authorize again.",
            400,
        )

    try:
        oauth_flow.fetch_token(
            authorization_response=request.url
        )
        credentials = oauth_flow.credentials

        os.makedirs(DATA_DIR, exist_ok=True)
        temp_file = YOUTUBE_TOKEN_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as file:
            file.write(credentials.to_json())

        os.replace(temp_file, YOUTUBE_TOKEN_FILE)
        oauth_flow = None

        return "YouTube authorization successful. Token saved."

    except Exception as exc:
        print(f"OAuth callback error: {repr(exc)}", flush=True)
        record_error(exc)
        return f"OAuth error: {exc}", 500


# ============================================================
# BACKGROUND THREADS
# ============================================================

def start_background_threads():
    global BACKGROUND_THREADS_STARTED

    with THREAD_START_LOCK:
        if BACKGROUND_THREADS_STARTED:
            return

        BACKGROUND_THREADS_STARTED = True

        threading.Thread(
            target=scheduler_loop,
            daemon=True,
            name="buffer-scheduler",
        ).start()

        threading.Thread(
            target=heartbeat_loop,
            daemon=True,
            name="heartbeat",
        ).start()

        threading.Thread(
            target=youtube_monitor_loop,
            daemon=True,
            name="youtube-monitor",
        ).start()

        def start_telegram():
            try:
                initialize_telegram(PUBLIC_BASE_URL)
            except Exception as exc:
                print(
                    f"Telegram initialization warning: {repr(exc)}",
                    flush=True,
                )
                record_error(exc)

        threading.Thread(
            target=start_telegram,
            daemon=True,
            name="telegram-init",
        ).start()


start_background_threads()


# ============================================================
# LOCAL DEVELOPMENT ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
