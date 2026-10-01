"""Channel profiles; legacy records and callers belong to the original channel."""
import os

DATA_DIR = os.getenv("AUTOMATION_DATA_DIR", "/app/data")
DEFAULT_CHANNEL = "default"
CHANNELS = {
    "default": {"name": "Original channel", "times": ((10, 0), (18, 0)),
                "token": "youtube_token.json", "handle": None},
    "goplustrader": {"name": "@goplustrader", "times": ((0, 0), (18, 0)),
                    "token": "youtube_token_goplustrader.json", "handle": "goplustrader"},
}


def channel_profile(channel=DEFAULT_CHANNEL):
    if channel not in CHANNELS:
        raise ValueError("Unknown YouTube channel")
    return CHANNELS[channel]


def token_file(channel=DEFAULT_CHANNEL):
    return os.path.join(DATA_DIR, channel_profile(channel)["token"])


def connected_channels():
    return [channel for channel in CHANNELS if os.path.exists(token_file(channel))]
