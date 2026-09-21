import os
import time
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from app.content import generate_script
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
        os.getenv("PORT", "8080")
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
        "Pocket Option YouTube Automation",
        flush=True
    )
    print(
        "Testing Gemini + Piper + Video Generator...",
        flush=True
    )
    print("=" * 60, flush=True)

    # --------------------------------
    # START VIDEO SERVER
    # --------------------------------

    server_thread = threading.Thread(
        target=start_video_server,
        daemon=True
    )

    server_thread.start()

    # --------------------------------
    # TEST TOPIC
    # --------------------------------

    topic = (
        "How an AI trading bot analyzes "
        "a trading chart"
    )

    try:

        # --------------------------------
        # 1. GEMINI
        # --------------------------------

        print(
            "\n[1/3] Generating Gemini script...",
            flush=True
        )

        script = generate_script(
            topic
        )

        print(
            "\n===== GENERATED SCRIPT =====",
            flush=True
        )

        print(
            script,
            flush=True
        )

        print(
            "============================",
            flush=True
        )

        # --------------------------------
        # 2. PIPER
        # --------------------------------

        print(
            "\n[2/3] Generating Piper voice...",
            flush=True
        )

        voice_path = generate_voice(
            script,
            "test_voice.wav"
        )

        print(
            f"Voice created: {voice_path}",
            flush=True
        )

        # --------------------------------
        # 3. VIDEO
        # --------------------------------

        print(
            "\n[3/3] Generating YouTube Short...",
            flush=True
        )

        video_path = generate_video(
            script,
            voice_path,
            "test_short.mp4"
        )

        print(
            "\n===== VIDEO TEST: SUCCESS =====",
            flush=True
        )

        print(
            f"Final video: {video_path}",
            flush=True
        )

        print(
            "\nVIDEO URL PATH:",
            flush=True
        )

        print(
            "/test_short.mp4",
            flush=True
        )

    except Exception as e:

        print(
            "\n===== VIDEO TEST: FAILED =====",
            flush=True
        )

        print(
            f"Error: {e}",
            flush=True
        )

    # --------------------------------
    # KEEP RAILWAY RUNNING
    # --------------------------------

    while True:

        print(
            f"[HEARTBEAT] Running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True
        )

        time.sleep(300)


if __name__ == "__main__":
    main()
