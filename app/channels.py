"""Persistent multi-channel YouTube profiles.

The first three automation slots use separate OAuth tokens on the Railway
volume. Two or more slots may belong to the same Gmail; the OAuth grant is
still saved separately for each selected YouTube channel.
"""
import json
import os

DATA_DIR = os.getenv("AUTOMATION_DATA_DIR", "/app/data")
DEFAULT_CHANNEL = "default"

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
        "times": ((0, 0), (18, 0)),
        "token": "youtube_token_goplustrader.json",
        "metadata": "youtube_channel_goplustrader.json",
        "client_id_env": "GOPLUS_YOUTUBE_CLIENT_ID",
        "client_secret_env": "GOPLUS_YOUTUBE_CLIENT_SECRET",
        "handle_env": "YOUTUBE_CHANNEL2_HANDLE",
    },
    "channel3": {
        "name": "Channel 3",
        "times": ((1, 0), (6, 0)),
        "token": "youtube_token_channel3.json",
        "metadata": "youtube_channel_channel3.json",
        "client_id_env": "YOUTUBE_CHANNEL3_CLIENT_ID",
        "client_secret_env": "YOUTUBE_CHANNEL3_CLIENT_SECRET",
        "handle_env": "YOUTUBE_CHANNEL3_HANDLE",
    },
}


def channel_profile(channel=DEFAULT_CHANNEL):
    if channel not in CHANNELS:
        raise ValueError("Unknown YouTube channel")
    return CHANNELS[channel]


def token_file(channel=DEFAULT_CHANNEL):
    return os.path.join(DATA_DIR, channel_profile(channel)["token"])


def metadata_file(channel=DEFAULT_CHANNEL):
    return os.path.join(DATA_DIR, channel_profile(channel)["metadata"])


def configured_handle(channel=DEFAULT_CHANNEL):
    env_name = channel_profile(channel).get("handle_env")
    return os.getenv(env_name, "").strip().lstrip("@") if env_name else ""


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
