import os
import json
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


# ============================================================
# SETTINGS
# ============================================================

DATA_DIR = "/app/data"

TOKEN_FILE = os.path.join(
    DATA_DIR,
    "youtube_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


# ============================================================
# GET YOUTUBE SERVICE
# ============================================================

def get_youtube_service():

    if not os.path.exists(
        TOKEN_FILE
    ):
        raise RuntimeError(
            "YouTube authorization token not found."
        )

    credentials = (
        Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )
    )

    # --------------------------------------------------------
    # REFRESH EXPIRED TOKEN
    # --------------------------------------------------------

    if (
        credentials.expired
        and credentials.refresh_token
    ):
        credentials.refresh(
            Request()
        )

        save_credentials(
            credentials
        )

    # --------------------------------------------------------
    # VALIDATE CREDENTIALS
    # --------------------------------------------------------

    if not credentials.valid:
        raise RuntimeError(
            "YouTube credentials are invalid. "
            "Reconnect the YouTube account."
        )

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials
    )

    return youtube


# ============================================================
# SAVE CREDENTIALS
# ============================================================

def save_credentials(
    credentials
):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

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


# ============================================================
# INTERNAL UPLOAD FUNCTION
# ============================================================

def _upload_video(
    video_path,
    title,
    description,
    privacy_status,
    publish_at=None
):

    # --------------------------------------------------------
    # CHECK VIDEO
    # --------------------------------------------------------

    if not os.path.exists(
        video_path
    ):
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    youtube = get_youtube_service()

    # --------------------------------------------------------
    # VIDEO STATUS
    # --------------------------------------------------------

    status = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False,
    }

    # --------------------------------------------------------
    # SCHEDULED PUBLISH TIME
    # --------------------------------------------------------

    if publish_at is not None:

        if privacy_status != "private":
            raise ValueError(
                "Scheduled videos must use "
                "privacyStatus='private'."
            )

        if publish_at.tzinfo is None:
            raise ValueError(
                "publish_at must contain timezone information."
            )

        publish_at_utc = (
            publish_at.astimezone(
                timezone.utc
            )
        )

        publish_at_string = (
            publish_at_utc.isoformat()
            .replace(
                "+00:00",
                "Z"
            )
        )

        status["publishAt"] = (
            publish_at_string
        )

    # --------------------------------------------------------
    # REQUEST BODY
    # --------------------------------------------------------

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
        },

        "status": status
    }

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        "\n===== YOUTUBE UPLOAD =====",
        flush=True
    )

    print(
        f"File: {video_path}",
        flush=True
    )

    print(
        f"Title: {title}",
        flush=True
    )

    print(
        f"Privacy: {privacy_status.upper()}",
        flush=True
    )

    if publish_at is not None:

        print(
            f"Scheduled publish: "
            f"{publish_at.isoformat()}",
            flush=True
        )

    # --------------------------------------------------------
    # VIDEO FILE
    # --------------------------------------------------------

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024
    )

    # --------------------------------------------------------
    # CREATE REQUEST
    # --------------------------------------------------------

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    while response is None:

        status_response, response = (
            request.next_chunk()
        )

        if status_response:

            progress = int(
                status_response.progress() * 100
            )

            print(
                f"Upload progress: "
                f"{progress}%",
                flush=True
            )

    # --------------------------------------------------------
    # VIDEO ID
    # --------------------------------------------------------

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload completed "
            "but no video ID was returned."
        )

    # --------------------------------------------------------
    # VIDEO URL
    # --------------------------------------------------------

    video_url = (
        f"https://www.youtube.com/shorts/"
        f"{video_id}"
    )

    # --------------------------------------------------------
    # SUCCESS LOG
    # --------------------------------------------------------

    print(
        "\n===== YOUTUBE UPLOAD SUCCESS =====",
        flush=True
    )

    print(
        f"Video ID: {video_id}",
        flush=True
    )

    print(
        f"URL: {video_url}",
        flush=True
    )

    print(
        f"Privacy: {privacy_status.upper()}",
        flush=True
    )

    if publish_at is not None:

        print(
            f"Publish at: "
            f"{publish_at.isoformat()}",
            flush=True
        )

    print(
        "===================================",
        flush=True
    )

    return {
        "video_id": video_id,
        "url": video_url,
        "privacy_status": privacy_status,
        "publish_at": (
            publish_at.isoformat()
            if publish_at is not None
            else None
        )
    }


# ============================================================
# MANUAL TEST UPLOAD
# ============================================================

def upload_short(
    video_path,
    title,
    description
):

    print(
        "\n===== MANUAL TEST UPLOAD =====",
        flush=True
    )

    print(
        "Mode: UNLISTED",
        flush=True
    )

    return _upload_video(
        video_path=video_path,
        title=title,
        description=description,
        privacy_status="unlisted",
        publish_at=None
    )


# ============================================================
# SCHEDULE SHORT
# ============================================================

def schedule_short(
    video_path,
    title,
    description,
    publish_at
):

    if publish_at is None:

        raise ValueError(
            "publish_at is required "
            "for scheduled uploads."
        )

    if publish_at.tzinfo is None:

        raise ValueError(
            "publish_at must contain "
            "timezone information."
        )

    print(
        "\n===== SCHEDULED SHORT UPLOAD =====",
        flush=True
    )

    print(
        "Mode: PRIVATE + SCHEDULED",
        flush=True
    )

    print(
        f"Publish time: "
        f"{publish_at.isoformat()}",
        flush=True
    )

    result = _upload_video(
        video_path=video_path,
        title=title,
        description=description,
        privacy_status="private",
        publish_at=publish_at
    )

    return result


# ============================================================
# GET VIDEO STATUS
# ============================================================

def get_video_status(
    video_id
):

    if not video_id:

        raise ValueError(
            "video_id is required."
        )

    youtube = get_youtube_service()

    response = (
        youtube.videos()
        .list(
            part="snippet,status,processingDetails",
            id=video_id
        )
        .execute()
    )

    items = response.get(
        "items",
        []
    )

    if not items:

        return None

    video = items[0]

    snippet = video.get(
        "snippet",
        {}
    )

    status = video.get(
        "status",
        {}
    )

    processing = video.get(
        "processingDetails",
        {}
    )

    return {
        "video_id": video.get("id"),

        "title": snippet.get(
            "title"
        ),

        "published_at": snippet.get(
            "publishedAt"
        ),

        "privacy_status": status.get(
            "privacyStatus"
        ),

        "upload_status": status.get(
            "uploadStatus"
        ),

        "publish_at": status.get(
            "publishAt"
        ),

        "failure_reason": status.get(
            "failureReason"
        ),

        "rejection_reason": status.get(
            "rejectionReason"
        ),

        "processing_status": processing.get(
            "processingStatus"
        ),

        "url": (
            f"https://www.youtube.com/shorts/"
            f"{video.get('id')}"
        )
    }
