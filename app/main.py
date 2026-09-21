import os
import time
import threading

from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from app.voice import generate_voice
from app.video import generate_video


OUTPUT_DIR = "/app/output"


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
        ("0.0.0.0", port),
        VideoHandler
    )

    print(
        f"Video server running on port {port}",
        flush=True
    )

    server.serve_forever()


def main():

    print("=" * 60, flush=True)

    print(
        "AI TRADING SHORTS - VIDEO TEST",
        flush=True
    )

    print("=" * 60, flush=True)

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    server_thread = threading.Thread(
        target=start_video_server,
        daemon=True
    )

    server_thread.start()

    # ---------------------------------------------------------
    # TEMPORARY TEST SCRIPT
    # Gemini is bypassed because its current free quota
    # is exhausted.
    # ---------------------------------------------------------

    bot_text = (
        "An AI trading bot can study candlestick patterns "
        "and price movement to organize the information "
        "you see on a trading chart."
    )

    cta_text = (
        "Want to see how the complete setup works? "
        "Tap the Related Video below the title "
        "to watch the full tutorial."
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

    try:

        print(
            "\n[1/2] Generating enhanced Piper voice...",
            flush=True
        )

        voice_path = generate_voice(
            full_script,
            "test_voice.wav"
        )

        print(
            f"Voice created: {voice_path}",
            flush=True
        )

        print(
            "\n[2/2] Generating 4K 5-clip Short...",
            flush=True
        )

        video_path = generate_video(
            full_script,
            voice_path,
            "test_short_4k.mp4"
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
            f"Final video: {video_path}",
            flush=True
        )

        print(
            "Open /test_short_4k.mp4 on the Railway domain.",
            flush=True
        )

    except Exception as e:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "VIDEO TEST FAILED",
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
            f"[HEARTBEAT] Running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True
        )

        time.sleep(300)


if __name__ == "__main__":
    main()
