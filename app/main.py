import os
import time
from datetime import datetime, timezone

from app.content import generate_script
from app.voice import generate_voice


def main():
    print("=" * 60, flush=True)
    print("Pocket Option YouTube Automation", flush=True)
    print("Testing Gemini + Piper Voice...", flush=True)
    print("=" * 60, flush=True)

    topic = "How an AI trading bot analyzes a trading chart"

    try:
        # -----------------------------
        # STEP 1: Generate script
        # -----------------------------
        print("\n[1/2] Generating Gemini script...", flush=True)

        script = generate_script(topic)

        print("\n===== GENERATED SCRIPT =====", flush=True)
        print(script, flush=True)
        print("============================", flush=True)

        # -----------------------------
        # STEP 2: Generate voice
        # -----------------------------
        print("\n[2/2] Generating Piper voice...", flush=True)

        output_path = generate_voice(
            script,
            "test_voice.wav"
        )

        print(
            f"\nVOICE TEST: SUCCESS",
            flush=True
        )

        print(
            f"Audio file created at: {output_path}",
            flush=True
        )

    except Exception as e:

        print(
            "\nVOICE TEST: FAILED",
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
