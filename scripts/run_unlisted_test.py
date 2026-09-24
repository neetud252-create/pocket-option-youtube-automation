import json
import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.config import YOUTUBE_DESCRIPTION
from app.content import generate_content
from app.video import generate_video
from app.voice import generate_voice
from app.youtube import upload_short

DATA_DIR = "/app/data"
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
IST = ZoneInfo("Asia/Kolkata")
CTA_TEXT = "Go to my channel description and click the Bot Activation button."


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def safe_version(value):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


def main():
    version = os.getenv("RUN_UNLISTED_TEST_VERSION", "").strip()
    if not version:
        print("STARTUP TEST: no RUN_UNLISTED_TEST_VERSION; skipping.", flush=True)
        return 0

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    version_key = safe_version(version)
    marker_path = os.path.join(DATA_DIR, f"unlisted_test_{version_key}.json")
    lock_path = os.path.join(DATA_DIR, f"unlisted_test_{version_key}.lock")

    if os.path.exists(marker_path):
        print(f"STARTUP TEST: already completed for {version}.", flush=True)
        return 0

    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        os.close(lock_fd)
    except FileExistsError:
        print(f"STARTUP TEST: already running for {version}.", flush=True)
        return 0

    timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S_%f")
    voice_path = os.path.join(OUTPUT_DIR, f"startup_test_voice_{timestamp}.mp3")
    video_path = None

    try:
        print("\n==================================================", flush=True)
        print("CREATING ONE UNLISTED SAMPLE SHORT", flush=True)
        print("Voice: ElevenLabs REQUIRED", flush=True)
        print("==================================================", flush=True)

        title, script = generate_content()
        amount = random.randint(1000, 2000)

        generate_voice(
            script,
            CTA_TEXT,
            voice_path,
            require_elevenlabs=True,
        )

        video_path = generate_video(
            script=script,
            voice_path=voice_path,
            short_amount=amount,
            output_filename=f"startup_test_short_{timestamp}.mp4",
        )

        video_id = upload_short(
            video_path=video_path,
            title=title,
            description=YOUTUBE_DESCRIPTION,
        )

        result = {
            "version": version,
            "title": title,
            "script": script,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "privacy_status": "unlisted",
            "voice_provider": "elevenlabs",
            "demo_amount": amount,
            "created_at": datetime.now(IST).isoformat(),
        }

        with open(marker_path, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=False)

        print("STARTUP TEST COMPLETE", flush=True)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        return 0

    except Exception as exc:
        print(f"STARTUP TEST FAILED: {repr(exc)}", flush=True)
        return 1

    finally:
        safe_remove(voice_path)
        safe_remove(os.path.splitext(voice_path)[0] + ".json")
        safe_remove(video_path)
        safe_remove(lock_path)


if __name__ == "__main__":
    sys.exit(main())
