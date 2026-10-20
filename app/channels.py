"""Persistent multi-channel YouTube profiles.

All five automation slots use separate OAuth tokens on the Railway
volume. Two or more slots may belong to the same Gmail; the OAuth grant is
still saved separately for each selected YouTube channel.
"""
import json
import os
from datetime import date

DATA_DIR = os.getenv("AUTOMATION_DATA_DIR", "/app/data")
DEFAULT_CHANNEL = "default"
SCHEDULE_EFFECTIVE_DATE = date(2026, 10, 21)
# Preserve the already-queued publication day during the timetable change.
PREVIOUS_TIMES = {
    "default": ((10, 0), (18, 0)),
    "goplustrader": ((0, 0), (18, 0)),
    "channel3": ((1, 0), (6, 0)),
    "pockettrade": ((10, 0), (18, 0)),
    "zingtrader": ((10, 0), (18, 0)),
}
UPLOAD_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)

CHANNELS = {
    "default": {
        "name": "Channel 1",
        "times": ((10, 0), (18, 0)),
        "token": "youtube_token.json",
        "metadata": "youtube_channel_default.json",
        "client_id_env": "YOUTUBE_CLIENT_ID",
        "client_secret_env": "YOUTUBE_CLIENT_SECRET",
        "handle_env": "YOUTUBE_CHANNEL1_HANDLE",
    },
    "goplustrader": {
        "name": "Channel 2",
        "times": ((11, 0), (19, 0)),
        "token": "youtube_token_goplustrader.json",
        "metadata": "youtube_channel_goplustrader.json",
        "client_id_env": "GOPLUS_YOUTUBE_CLIENT_ID",
        "client_secret_env": "GOPLUS_YOUTUBE_CLIENT_SECRET",
        "handle_env": "YOUTUBE_CHANNEL2_HANDLE",
    },
    "channel3": {
        "name": "Channel 3",
        "times": ((6, 0), (14, 0)),
        "token": "youtube_token_channel3.json",
        "metadata": "youtube_channel_channel3.json",
        "client_id_env": "YOUTUBE_CHANNEL3_CLIENT_ID",
        "client_secret_env": "YOUTUBE_CHANNEL3_CLIENT_SECRET",
        "handle_env": "YOUTUBE_CHANNEL3_HANDLE",
    },
    "pockettrade": {
        "name": "Channel 4 - PocketTrade",
        "scopes": UPLOAD_SCOPES,
        "times": ((12, 0), (20, 0)),
        "token": "youtube_token_pockettrade.json",
        "metadata": "youtube_channel_pockettrade.json",
        "client_id_env": "GOPLUS_YOUTUBE_CLIENT_ID",
        "client_secret_env": "GOPLUS_YOUTUBE_CLIENT_SECRET",
        "handle_env": "POCKETTRADE_YOUTUBE_HANDLE",
        "handle": "PocketTrade-u1l",
    },
    "zingtrader": {
        "name": "Channel 5 - zingTrader",
        "scopes": UPLOAD_SCOPES,
        "times": ((13, 0), (21, 0)),
        "token": "youtube_token_zingtrader.json",
        "metadata": "youtube_channel_zingtrader.json",
        "client_id_env": "GOPLUS_YOUTUBE_CLIENT_ID",
        "client_secret_env": "GOPLUS_YOUTUBE_CLIENT_SECRET",
        "handle_env": "ZINGTRADER_YOUTUBE_HANDLE",
        "handle": "zingTrader-s5t",
    },
}


def channel_profile(channel=DEFAULT_CHANNEL):
    if channel not in CHANNELS:
        raise ValueError("Unknown YouTube channel")
    return CHANNELS[channel]


def publication_times(target_date, channel=DEFAULT_CHANNEL):
    """Choose by the IST publication date, including advance preparation."""
    profile = channel_profile(channel)
    if target_date < SCHEDULE_EFFECTIVE_DATE:
        return PREVIOUS_TIMES[channel]
    return profile["times"]


def token_file(channel=DEFAULT_CHANNEL):
    return os.path.join(DATA_DIR, channel_profile(channel)["token"])


def metadata_file(channel=DEFAULT_CHANNEL):
    return os.path.join(DATA_DIR, channel_profile(channel)["metadata"])


def configured_handle(channel=DEFAULT_CHANNEL):
    profile = channel_profile(channel)
    env_name = profile.get("handle_env")
    override = os.getenv(env_name, "").strip() if env_name else ""
    return (override or profile.get("handle", "")).strip().lstrip("@")


def load_channel_metadata(channel=DEFAULT_CHANNEL):
    path = metadata_file(channel)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_channel_metadata(channel, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = metadata_file(channel)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def channel_connected(channel=DEFAULT_CHANNEL):
    return os.path.isfile(token_file(channel)) and os.path.getsize(token_file(channel)) > 0


def connected_channels():
    return [channel for channel in CHANNELS if channel_connected(channel)]


def channel_display_name(channel=DEFAULT_CHANNEL):
    metadata = load_channel_metadata(channel)
    return metadata.get("title") or channel_profile(channel)["name"]

