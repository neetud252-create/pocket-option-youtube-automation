import json
import os
import random
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# When Railway runs this file directly as `python scripts/replace_scheduled.py`,
# Python places /app/scripts on sys.path instead of the repository root. Add the
# repo root explicitly so imports from the app package always work.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.config import YOUTUBE_DESCRIPTION
from app.content import generate_content
from app.video import generate_video
from app.voice import generate_voice
from app.youtube import get_youtube_service, schedule_short


DATA_DIR = "/app/data"
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
BUFFER_FILE = os.path.join(DATA_DIR, "buffer_queue.json")
IST = ZoneInfo("Asia/Kolkata")
CTA_TEXT = (
    "Want a smarter chart workflow? Open the channel description and tap "
    "Bot Activation to see how the process works."
)


def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        return {"slots": []}

    try:
        with open(BUFFER_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            data = {"slots": []}
        if not isinstance(data.get("slots"), list):
            data["slots"] = []
        return data
    except Exception:
        return {"slots": []}


def save_buffer(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    temporary = BUFFER_FILE + ".tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temporary, BUFFER_FILE)


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def parse_target_date():
    value = os.getenv("FORCE_REPLACE_DATE", "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def target_slots(target_date):
    return [
        datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            10,
            0,
            tzinfo=IST,
        ),
        datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            18,
            0,
            tzinfo=IST,
        ),
    ]


def slot_matches_target(record, target_iso_values):
    return record.get("channel", "default") == "default" and str(record.get("publish_at", "")) in target_iso_values


def unschedule_video(video_id):
    """Keep the old Short private but remove its scheduled publish time.

    The current OAuth grant includes youtube.upload + youtube.readonly. That
    grant can update an uploaded video's status, while videos.delete requires
    a broader scope. Updating the status lets us safely replace tomorrow's
    scheduled Shorts without asking the user for another OAuth scope.
    """
    youtube = get_youtube_service()

    response = (
        youtube.videos()
        .list(part="status", id=video_id)
        .execute()
    )
    items = response.get("items", [])
    if not items:
        print(f"Old scheduled video already missing: {video_id}", flush=True)
        return True

    current_status = items[0].get("status", {})
    new_status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": bool(
            current_status.get("selfDeclaredMadeForKids", False)
        ),
    }

    youtube.videos().update(
        part="status",
        body={
            "id": video_id,
            "status": new_status,
        },
    ).execute()

    verify = (
        youtube.videos()
        .list(part="status", id=video_id)
        .execute()
    )
    verify_items = verify.get("items", [])
    if not verify_items:
        print(f"Old scheduled video disappeared after update: {video_id}", flush=True)
        return True

    verify_status = verify_items[0].get("status", {})
    if verify_status.get("publishAt"):
        raise RuntimeError(
            f"Old video is still scheduled after status update: {video_id}"
        )

    if verify_status.get("privacyStatus") != "private":
        raise RuntimeError(
            f"Old video is not private after status update: {video_id}"
        )

    print(f"Old scheduled video unscheduled and kept private: {video_id}", flush=True)
    return True


def main():
    target_date = parse_target_date()

    if target_date is None:
        print("One-time replacement: FORCE_REPLACE_DATE not set; skipping.", flush=True)
        return 0

    version = os.getenv(
        "FORCE_REPLACE_VERSION",
        f"replace-{target_date.isoformat()}",
    ).strip()

    safe_version = "".join(
        ch if ch.isalnum() or ch in "-_" else "_"
        for ch in version
    )
    marker_file = os.path.join(
        DATA_DIR,
        f"scheduled_replacement_{safe_version}.json",
    )

    if os.path.exists(marker_file):
        print(
            f"One-time replacement already completed: {marker_file}",
            flush=True,
        )
        return 0

    slots = target_slots(target_date)
    now = datetime.now(IST)

    if any(slot <= now + timedelta(minutes=5) for slot in slots):
        raise RuntimeError(
            "One-time replacement target has a slot that is already past or too close."
        )

    print("\n==================================================", flush=True)
    print("ONE-TIME ELEVENLABS SCHEDULE REPLACEMENT", flush=True)
    print(f"Target date: {target_date.isoformat()}", flush=True)
    print("Target times: 10:00 AM IST and 6:00 PM IST", flush=True)
    print("Voice: ElevenLabs REQUIRED", flush=True)
    print("==================================================", flush=True)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = load_buffer()
    target_iso_values = {slot.isoformat() for slot in slots}

    existing_ids = []
    for record in data.get("slots", []):
        if slot_matches_target(record, target_iso_values):
            video_id = record.get("video_id")
            if video_id:
                existing_ids.append(str(video_id))

    extra_ids = os.getenv("FORCE_REPLACE_VIDEO_IDS", "").strip()
    if extra_ids:
        existing_ids.extend(
            item.strip()
            for item in extra_ids.split(",")
            if item.strip()
        )

    existing_ids = list(dict.fromkeys(existing_ids))

    for video_id in existing_ids:
        print(f"Unscheduling old scheduled video: {video_id}", flush=True)
        unschedule_video(video_id)

    data = load_buffer()
    data["slots"] = [
        record
        for record in data.get("slots", [])
        if not slot_matches_target(record, target_iso_values)
    ]
    save_buffer(data)

    created_records = []

    for publish_at in slots:
        print(
            f"\nCreating fresh replacement for {publish_at.isoformat()}",
            flush=True,
        )

        title, script = generate_content()
        amount = random.randint(1000, 2000)
        timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S_%f")
        voice_path = os.path.join(
            OUTPUT_DIR,
            f"replacement_voice_{timestamp}.mp3",
        )
        video_path = None

        try:
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
                output_filename=f"replacement_short_{timestamp}.mp4",
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
                "created_at": datetime.now(IST).isoformat(),
                "reason": "ONE-TIME ELEVENLABS REPLACEMENT",
                "demo_amount": amount,
                "voice_provider": "elevenlabs",
            }

            data = load_buffer()
            data["slots"].append(record)
            save_buffer(data)
            created_records.append(record)

            print(
                f"Replacement scheduled successfully: {video_id}",
                flush=True,
            )

        finally:
            safe_remove(voice_path)
            safe_remove(os.path.splitext(voice_path)[0] + ".json")
            safe_remove(video_path)

    if len(created_records) != 2:
        raise RuntimeError(
            f"Replacement incomplete: created {len(created_records)} of 2 Shorts."
        )

    with open(marker_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "version": version,
                "target_date": target_date.isoformat(),
                "completed_at": datetime.now(IST).isoformat(),
                "videos": created_records,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\nONE-TIME REPLACEMENT COMPLETE", flush=True)
    for record in created_records:
        print(
            f"{record['publish_at']} | {record['video_id']} | {record['title']}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ONE-TIME REPLACEMENT FAILED: {repr(exc)}", flush=True)
        sys.exit(1)
