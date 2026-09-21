import time
from datetime import datetime, timezone

from app.content import generate_script
from app.voice import generate_voice
from app.video import generate_video


def main():

    print("=" * 60, flush=True)
    print("Pocket Option YouTube Automation", flush=True)
    print("Testing Gemini + Piper + Video Generator...", flush=True)
    print("=" * 60, flush=True)

    topic = "How an AI trading bot analyzes a trading chart"

    try:

        # --------------------------------
        # STEP 1: Generate Gemini script
        # --------------------------------

        print(
            "\n[1/3] Generating Gemini script...",
            flush=True
        )

        script = generate_script(topic)

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
        # STEP 2: Generate Piper voice
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
        # STEP 3: Generate YouTube Short
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

    except Exception as e:

        print(
            "\n===== VIDEO TEST: FAILED =====",
            flush=True
        )

        print(
            f"Error: {e}",
            flush=True
        )

    # Keep Railway service running.
    while True:

        print(
            f"[HEARTBEAT] Running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True
        )

        time.sleep(300)


if __name__ == "__main__":
    main()
