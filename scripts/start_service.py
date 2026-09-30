import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main():
    replace_date = os.getenv("FORCE_REPLACE_DATE", "").strip()
    replace_version = os.getenv("FORCE_REPLACE_VERSION", "").strip()

    if replace_date and replace_version:
        print(
            f"Running one-time ElevenLabs schedule replacement: {replace_version}",
            flush=True,
        )
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT_DIR, "scripts", "replace_scheduled.py")],
            cwd=ROOT_DIR,
        )
        if result.returncode != 0:
            print(
                "One-time replacement did not complete. Starting the web service anyway so OAuth/recovery remain available.",
                flush=True,
            )

    version = os.getenv("RUN_UNLISTED_TEST_VERSION", "").strip()

    if version:
        print(
            f"Launching one-time unlisted test worker for version: {version}",
            flush=True,
        )
        subprocess.Popen(
            [sys.executable, os.path.join(ROOT_DIR, "scripts", "run_unlisted_test.py")],
            cwd=ROOT_DIR,
        )

    print("Starting Gunicorn service on port 8080...", flush=True)
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "--workers",
            "1",
            "--threads",
            "4",
            "--timeout",
            "120",
            "--bind",
            "0.0.0.0:8080",
            "app.start:app",
        ],
    )


if __name__ == "__main__":
    main()
