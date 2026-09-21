import time
from datetime import datetime, timezone

from app.content import generate_script


def main():
    print("=" * 60, flush=True)
    print("Pocket Option YouTube Automation", flush=True)
    print("Testing Gemini API...", flush=True)
    print("=" * 60, flush=True)

    topic = "How an AI trading bot analyzes a trading chart"

    try:
        script = generate_script(topic)

        print("\n===== GEMINI GENERATED SCRIPT =====", flush=True)
        print(script, flush=True)
        print("===== END SCRIPT =====\n", flush=True)

        print("GEMINI TEST: SUCCESS", flush=True)

    except Exception as e:
        print("GEMINI TEST: FAILED", flush=True)
        print(f"Error: {e}", flush=True)

    while True:
        print(
            f"[HEARTBEAT] Running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True,
        )
        time.sleep(300)


if __name__ == "__main__":
    main()
