import os
import json

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


DATA_DIR = "/app/data"

TOKEN_FILE = os.path.join(
    DATA_DIR,
    "youtube_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_youtube_service():

    if not os.path.exists(TOKEN_FILE):

        raise RuntimeError(
            "YouTube authorization token not found."
        )

    credentials = (
        Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )
    )

    # Refresh expired access token
    if credentials.expired and credentials.refresh_token:

        credentials.refresh(
            Request()
        )

        save_credentials(
            credentials
        )

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


def upload_short(
    video_path,
    title,
    description
):

    if not os.path.exists(video_path):

        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    youtube = get_youtube_service()

    body = {

        "snippet": {

            "title": title,

            "description": description,

            "categoryId": "22",

        },

        "status": {

            "privacyStatus": "public",

            "selfDeclaredMadeForKids": False,

        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024
    )

    print(
        "\n===== YOUTUBE UPLOAD =====",
        flush=True
    )

    print(
        f"Title: {title}",
        flush=True
    )

    print(
        "Uploading...",
        flush=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            print(
                f"Upload progress: "
                f"{int(status.progress() * 100)}%",
                flush=True
            )

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload completed "
            "but no video ID was returned."
        )

    video_url = (
        f"https://www.youtube.com/shorts/"
        f"{video_id}"
    )

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

    return {
        "video_id": video_id,
        "url": video_url
    }
