"""
Pocket Option YouTube Automation
Initial Railway health/startup service.

This is intentionally a small first deployment step.
The real content-generation and YouTube upload modules will be added
after the Railway service starts successfully.
"""

import os
import time
from datetime import datetime, timezone


def main() -> None:
    print("=" * 60, flush=True)
    print("Pocket Option YouTube Automation", flush=True)
    print("Service started successfully.", flush=True)
    print(f"UTC time: {datetime.now(timezone.utc).isoformat()}", flush=True)
    print("Waiting for the next automation module...", flush=True)
    print("=" * 60, flush=True)

    # Keep the Railway service alive while we build the automation.
    while True:
        print(
            f"[HEARTBEAT] Service running: "
            f"{datetime.now(timezone.utc).isoformat()}",
            flush=True,
        )
        time.sleep(300)


if __name__ == "__main__":
    main()
