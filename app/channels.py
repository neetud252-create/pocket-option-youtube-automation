"""Channel profiles; legacy records and callers belong to the original channel."""
import os

DATA_DIR = os.getenv("AUTOMATION_DATA_DIR", "/app/data")
DEFAULT_CHANNEL = "default"
CHANNELS = {
    "default": {"name": "Original channel", "times": ((10, 0), (18, 0)),
                "token": "youtube_token.json", "handle": None},
    "goplustrader": {"name": "@goplustrader", "times": ((0, 0), (18, 0)),
                    "token": "youtube_token_goplustrader.json", "handle": "goplustrader",
                    "client_id_env": "GOPLUS_YOUTUBE_CLIENT_ID",
                    "client_secret_env": "GOPLUS_YOUTUBE_CLIENT_SECRET"},
    "channel3": {"name": "Channel 3", "times": ((1, 0), (6, 0)),
                 "token": "youtube_token_channel3.json",
                 "handle": os.getenv("YOUTUBE_CHANNEL3_HANDLE", "").strip().lstrip("@"),
                 "token_env": "YOUTUBE_CHANNEL3_TOKEN_JSON",
                 "client_id_env": "YOUTUBE_CHANNEL3_CLIENT_ID",
                 "client_secret_env": "YOUTUBE_CHANNEL3_CLIENT_SECRET"},
}


def channel_profile(channel=DEFAULT_CHANNEL):
    if channel not in CHANNELS:
        raise ValueError("Unknown YouTube channel")
    return CHANNELS[channel]


def token_file(channel=DEFAULT_CHANNEL):
    return os.path.join(DATA_DIR, channel_profile(channel)["token"])


def connected_channels():
    return [channel for channel in CHANNELS if channel_connected(channel)]


def channel_connected(channel=DEFAULT_CHANNEL):
    profile = channel_profile(channel)
    if profile.get("token_env"):
        return bool(profile["handle"] and os.getenv(profile["token_env"]))
    return os.path.exists(token_file(channel))

