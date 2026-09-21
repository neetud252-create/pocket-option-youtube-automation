import os
import time
import random
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
        "AI TRADING SHORTS AUTOMATION",
        flush=True
    )

    print("=" * 60, flush=True)

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # Start public video server
    server_thread = threading.Thread(
        target=start_video_server,
        daemon=True
    )

    server_thread.start()

    # ---------------------------------------------------------
    # TOPIC ROTATION
    # ---------------------------------------------------------

    topics = [

        "how an AI trading bot analyzes candlestick patterns",

        "how an AI trading bot studies price movement",

        "how an AI trading bot analyzes support and resistance",

        "how an AI trading bot identifies chart patterns",

        "how an AI trading bot analyzes indicators",

        "how an AI trading bot studies market structure",

        "how an AI trading bot processes trading information",

        "how an AI trading bot analyzes possible trade setups",

        "how an AI trading bot reads changing market conditions",

        "how an AI trading bot combines different chart signals",

    ]

    topic = random.choice(
        topics
    )

    print(
        f"\nSelected topic:\n{topic}",
        flush=True
    )

    try:

        # -----------------------------------------------------
        # 1. GENERATE NEW SCRIPT
        # -----------------------------------------------------

        print(
            "\n[1/3] Generating new script...",
            flush=True
        )

        script_data = generate_script(
            topic
        )

        bot_text = script_data["bot"]

        cta_text = script_data["cta"]

        full_script = script_data["full"]

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

        # -----------------------------------------------------
        # 2. GENERATE ENHANCED VOICE
        # -----------------------------------------------------

        print(
            "\n[2/3] Generating enhanced voice...",
            flush=True
        )

        voice_path = generate_voice(
            full_script,
            "short_voice.wav"
        )

        print(
            f"Voice created:\n{voice_path}",
            flush=True
        )

        # -----------------------------------------------------
        # 3. GENERATE VIDEO
        # -----------------------------------------------------

        print(
            "\n[3/3] Generating 5-clip Short...",
            flush=True
        )

        video_path = generate_video(
            full_script,
            voice_path,
            "short.mp4"
        )

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "SHORT GENERATION SUCCESS",
            flush=True
        )

        print(
            "=" * 60,
            flush=True
        )

        print(
            f"Video: {video_path}",
            flush=True
        )

        print(
            "Open /short.mp4 on the Railway domain.",
            flush=True
        )

    except Exception as e:

        print(
            "\n" + "=" * 60,
            flush=True
        )

        print(
            "SHORT GENERATION FAILED",
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

    # Keep Railway service alive
    while True:

        print(
            f"[HEARTBEAT] Running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True
        )

        time.sleep(300)


if __name__ == "__main__":
    main()
