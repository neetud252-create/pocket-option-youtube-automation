import os
import time
import random
import threading

from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from app.voice import generate_voice
from app.video import generate_video


OUTPUT_DIR = "/app/output"


# ============================================================
# RANDOM DEMO AMOUNT
# Every new video gets a random amount from $1000 to $2000
# ============================================================

SHORT_AMOUNT = random.randint(
    1000,
    2000
)


# ============================================================
# VIDEO SERVER
# ============================================================

class VideoHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):

        super().__init__(
            *args,
            directory=OUTPUT_DIR,
            **kwargs
        )


def start_video_server():

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            port
        ),
        VideoHandler
    )

    print(
        f"Video server running on port {port}",
        flush=True
    )

    server.serve_forever()


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 60,
        flush=True
    )

    print(
        "AI TRADING SHORTS AUTOMATION",
        flush=True
    )

    print(
        "ELEVENLABS + RANDOM DEMO AMOUNT + 5 CLIPS + 4K",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # START VIDEO SERVER
    # --------------------------------------------------------

    server_thread = threading.Thread(
        target=start_video_server,
        daemon=True
    )

    server_thread.start()

    # --------------------------------------------------------
    # CHECK ELEVENLABS API KEY
    # --------------------------------------------------------

    elevenlabs_key = os.getenv(
        "ELEVENLABS_API_KEY"
    )

    if not elevenlabs_key:

        print(
            "\nERROR: ELEVENLABS_API_KEY is missing.",
            flush=True
        )

        print(
            "Add ELEVENLABS_API_KEY in Railway Variables.",
            flush=True
        )

        while True:

            print(
                "[HEARTBEAT] Waiting for ElevenLabs API key...",
                flush=True
            )

            time.sleep(300)

    print(
        "\nElevenLabs API key detected.",
        flush=True
    )

    # --------------------------------------------------------
    # RANDOM DEMO AMOUNT
    # --------------------------------------------------------

    print(
        "\n===== RANDOM DEMO AMOUNT =====",
        flush=True
    )

    print(
        f"Selected amount: ${SHORT_AMOUNT}",
        flush=True
    )

    print(
        "Range: $1,000 - $2,000",
        flush=True
    )

    print(
        "This amount is displayed as an example.",
        flush=True
    )

    print(
        "==============================",
        flush=True
    )

    # --------------------------------------------------------
    # TEMPORARY TEST SCRIPT
    # --------------------------------------------------------
    # Gemini is temporarily bypassed.
    # --------------------------------------------------------

    bot_text = (
        "An AI trading bot can study candlestick patterns "
        "and price movement to organize the information "
        "you see on a trading chart. "
        "It can also help analyze different parts "
        "of the chart in a structured way."
    )

    cta_text = (
        "Want to see how the complete setup works? "
        "Tap the Related Video below the title "
        "to watch the full tutorial and see the "
        "full bot setup step by step."
    )

    full_script = (
        bot_text
        + " "
        + cta_text
    )

    print(
        "\n===== BOT PART =====",
        flush=True
    )

    print(
        bot_text,
        flush=True
    )

    print(
        "\n===== CTA PART =====",
        flush=True
    )

    print(
        cta_text,
        flush=True
    )

    print(
        "\n===== FULL SCRIPT =====",
        flush=True
    )

    print(
        full_script,
        flush=True
    )

    print(
        "\nWord count:",
        len(
            full_script.split()
        ),
        flush=True
    )

    # --------------------------------------------------------
    # ELEVENLABS VOICE
    # --------------------------------------------------------

    try:

        print(
            "\n[1/2] Generating ElevenLabs voice...",
            flush=True
        )

        voice_path = generate_voice(
            full_script,
            cta_text,
            "test_voice.mp3"
        )

        print(
            "Voice created successfully:",
            flush=True
        )

        print(
            voice_path,
            flush=True
        )

    except Exception as e:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "ELEVENLABS VOICE GENERATION FAILED",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"Error: {e}",
            flush=True
        )

        while True:

            print(
                "[HEARTBEAT] Voice generation failed.",
                flush=True
            )

            time.sleep(300)

    # --------------------------------------------------------
    # VIDEO GENERATION
    # --------------------------------------------------------

    try:

        print(
            "\n[2/2] Generating 4K 5-clip Short...",
            flush=True
        )

        video_path = generate_video(
            full_script,
            voice_path,
            "test_short_4k.mp4",
            SHORT_AMOUNT
        )

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "4K VIDEO TEST SUCCESS",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"Final video:",
            flush=True
        )

        print(
            video_path,
            flush=True
        )

        print(
            "\nOpen:",
            flush=True
        )

        print(
            "/test_short_4k.mp4",
            flush=True
        )

    except Exception as e:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "VIDEO GENERATION FAILED",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"Error: {e}",
            flush=True
        )

    # --------------------------------------------------------
    # KEEP RAILWAY ALIVE
    # --------------------------------------------------------

    while True:

        print(
            f"[HEARTBEAT] Running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True
        )

        time.sleep(300)


if __name__ == "__main__":

    main()
