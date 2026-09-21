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

    port = int(os.getenv("PORT", "8080"))

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
        "10-CLIP MIX TEST",
        flush=True
    )
    print("=" * 60, flush=True)

    server_thread = threading.Thread(
        target=start_video_server,
        daemon=True
    )

    server_thread.start()

    # TEMPORARY TEST SCRIPT
    # Gemini is intentionally bypassed because
    # the current free-tier quota is exhausted.

    script = (
        "Ever wondered how an AI trading bot reads a chart? "
        "Instead of watching every price movement manually, "
        "the system can analyze chart patterns, support and "
        "resistance levels, and other market information. "
        "Understanding how these elements work together can "
        "help you better understand what the bot is analyzing. "
        "Watch the related tutorial to see how the complete "
        "setup works."
    )

    try:

        print(
            "\n===== TEST SCRIPT =====",
            flush=True
        )

        print(
            script,
            flush=True
        )

        print(
            "======================",
            flush=True
        )

        print(
            "\n[1/2] Generating Piper voice...",
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

        print(
            "\n[2/2] Generating 10-CLIP Short...",
            flush=True
        )

        video_path = generate_video(
            script,
            voice_path,
            "test_short.mp4"
        )

        print(
            "\n===== 10-CLIP TEST SUCCESS =====",
            flush=True
        )

        print(
            f"Final video: {video_path}",
            flush=True
        )

        print(
            "Open /test_short.mp4 on the Railway domain.",
            flush=True
        )

    except Exception as e:

        print(
            "\n===== 10-CLIP TEST FAILED =====",
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
