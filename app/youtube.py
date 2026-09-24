import os
import random
import threading
import time
from datetime import timezone

import httplib2

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


# ============================================================
# SETTINGS
# ============================================================

DATA_DIR = "/app/data"
TOKEN_FILE = os.path.join(DATA_DIR, "youtube_token.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

UPLOAD_RETRY_COUNT = 6
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
YOUTUBE_AUTH_LOCK = threading.Lock()


# ============================================================
# CREDENTIALS
# ============================================================

def save_credentials(credentials):
    """
    Persist the complete Google credential JSON, including expiry.
    Atomic replacement protects the persistent token file from partial writes.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = TOKEN_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(credentials.to_json())

    os.replace(temp_file, TOKEN_FILE)


def get_youtube_service():
    """
    Build an authenticated YouTube client.

    The lock prevents the scheduler and status-monitor thread from trying to
    refresh and rewrite the same OAuth token at the same time.
    """
    with YOUTUBE_AUTH_LOCK:
        if not os.path.exists(TOKEN_FILE):
            raise RuntimeError(
                "YouTube authorization token not found. "
                "Open /authorize and reconnect YouTube."
            )

        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                save_credentials(credentials)
                print("YouTube OAuth token refreshed.", flush=True)
            except Exception as exc:
                raise RuntimeError(
                    "YouTube token refresh failed. "
                    "Open /authorize and reconnect YouTube."
                ) from exc

        if not credentials.valid:
            raise RuntimeError(
                "YouTube credentials are invalid. "
                "Open /authorize and reconnect YouTube."
            )

        return build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )


# ============================================================
# RETRY HELPERS
# ============================================================

def retry_delay(attempt_number):
    base = min(60, 2 ** attempt_number)
    return base + random.uniform(0.0, 1.5)


def is_retryable_http_error(exc):
    try:
        return int(exc.resp.status) in RETRYABLE_HTTP_CODES
    except Exception:
        return False


# ============================================================
# INTERNAL UPLOAD
# ============================================================

def _upload_video(
    video_path,
    title,
    description,
    privacy_status,
    publish_at=None,
):
    if not os.path.exists(video_path):
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    if os.path.getsize(video_path) <= 0:
        raise RuntimeError(
            f"Video is empty: {video_path}"
        )

    youtube = get_youtube_service()

    status = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False,
    }

    if publish_at is not None:
        if privacy_status != "private":
            raise ValueError(
                "Scheduled videos must use privacyStatus='private'."
            )

        if publish_at.tzinfo is None:
            raise ValueError(
                "publish_at must contain timezone information."
            )

        publish_at_utc = publish_at.astimezone(timezone.utc)
        publish_at_string = (
            publish_at_utc.isoformat().replace("+00:00", "Z")
        )
        status["publishAt"] = publish_at_string

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
        },
        "status": status,
    }

    print("\n===== YOUTUBE UPLOAD =====", flush=True)
    print(f"File: {video_path}", flush=True)
    print(f"Title: {title}", flush=True)
    print(f"Privacy: {privacy_status.upper()}", flush=True)

    if publish_at is not None:
        print(
            f"Scheduled publish: {publish_at.isoformat()}",
            flush=True,
        )

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024,
    )

    upload_request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    retry_attempt = 0

    while response is None:
        try:
            status_response, response = upload_request.next_chunk()

            if status_response:
                progress = int(status_response.progress() * 100)
                print(
                    f"Upload progress: {progress}%",
                    flush=True,
                )

            retry_attempt = 0

        except HttpError as exc:
            if (
                not is_retryable_http_error(exc)
                or retry_attempt >= UPLOAD_RETRY_COUNT
            ):
                raise

            retry_attempt += 1
            delay = retry_delay(retry_attempt)

            print(
                f"YouTube transient HTTP {exc.resp.status}. "
                f"Retry {retry_attempt}/{UPLOAD_RETRY_COUNT} "
                f"in {delay:.1f}s.",
                flush=True,
            )
            time.sleep(delay)

        except (httplib2.HttpLib2Error, OSError, TimeoutError) as exc:
            if retry_attempt >= UPLOAD_RETRY_COUNT:
                raise

            retry_attempt += 1
            delay = retry_delay(retry_attempt)

            print(
                f"YouTube network error: {exc}. "
                f"Retry {retry_attempt}/{UPLOAD_RETRY_COUNT} "
                f"in {delay:.1f}s.",
                flush=True,
            )
            time.sleep(delay)

    video_id = response.get("id")

    if not video_id:
        raise RuntimeError(
            "YouTube upload completed but no video ID was returned."
        )

    video_url = f"https://www.youtube.com/shorts/{video_id}"

    print("\n===== YOUTUBE UPLOAD SUCCESS =====", flush=True)
    print(f"Video ID: {video_id}", flush=True)
    print(f"URL: {video_url}", flush=True)
    print(f"Privacy: {privacy_status.upper()}", flush=True)

    if publish_at is not None:
        print(
            f"Publish at: {publish_at.isoformat()}",
            flush=True,
        )

    return {
        "video_id": video_id,
        "url": video_url,
        "privacy_status": privacy_status,
        "publish_at": (
            publish_at.isoformat()
            if publish_at is not None
            else None
        ),
    }


# ============================================================
# PUBLIC UPLOAD FUNCTIONS
# ============================================================

def upload_short(video_path, title, description):
    print("\n===== MANUAL TEST UPLOAD =====", flush=True)
    print("Mode: UNLISTED", flush=True)

    result = _upload_video(
        video_path=video_path,
        title=title,
        description=description,
        privacy_status="unlisted",
        publish_at=None,
    )

    return result["video_id"]


def schedule_short(
    video_path,
    title,
    description,
    publish_at,
):
    if publish_at is None:
        raise ValueError(
            "publish_at is required for scheduled uploads."
        )

    if publish_at.tzinfo is None:
        raise ValueError(
            "publish_at must contain timezone information."
        )

    print("\n===== SCHEDULED SHORT UPLOAD =====", flush=True)
    print("Mode: PRIVATE + SCHEDULED", flush=True)
    print(
        f"Publish time: {publish_at.isoformat()}",
        flush=True,
    )

    result = _upload_video(
        video_path=video_path,
        title=title,
        description=description,
        privacy_status="private",
        publish_at=publish_at,
    )

    return result["video_id"]


# ============================================================
# STATUS
# ============================================================

def get_video_status(video_id):
    if not video_id:
        raise ValueError("video_id is required.")

    if not isinstance(video_id, str):
        raise TypeError("video_id must be a string.")

    youtube = get_youtube_service()

    response = (
        youtube.videos()
        .list(
            part="snippet,status,processingDetails",
            id=video_id,
        )
        .execute()
    )

    items = response.get("items", [])

    if not items:
        return None

    video = items[0]
    snippet = video.get("snippet", {})
    status = video.get("status", {})
    processing = video.get("processingDetails", {})

    return {
        "video_id": video.get("id"),
        "title": snippet.get("title"),
        "published_at": snippet.get("publishedAt"),
        "privacy_status": status.get("privacyStatus"),
        "upload_status": status.get("uploadStatus"),
        "processing_status": processing.get("processingStatus"),
        "rejection_reason": status.get("rejectionReason"),
        "failure_reason": status.get("failureReason"),
    }
