import json
import os
import random
import shutil
import subprocess
import tempfile
import uuid




# ============================================================
# CONFIG
# ============================================================


ASSETS_DIR = "/app/assets/footage"
OUTPUT_DIR = "/app/output"
BACKGROUND_MUSIC = "/app/assets/background_music.mp3"
BACKGROUND_MUSIC_VOLUME = 0.10


NUMBER_OF_CLIPS = 4
CTA_DURATION = 5.0
MIN_VIDEO_DURATION = 20.0
MAX_VIDEO_DURATION = 26.0
FPS = 30
OPENING_TEXT_DURATION = 5.0


CTA_SOURCE = os.path.join(
    ASSETS_DIR,
    "activation_cta.mp4",
)


OVERLAY_FONT_FILE = (
    "/usr/share/fonts/truetype/dejavu/"
    "DejaVuSans-Bold.ttf"
)


RANDOM_VIDEO_FILES = [
    "01_chart_overview.mp4",
    "02_candlestick_chart.mp4",
