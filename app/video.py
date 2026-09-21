import os
import random
import subprocess
import tempfile


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOOTAGE_DIR = os.path.join(
    BASE_DIR,
    "assets",
    "footage"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)


def get_audio_duration(audio_path: str) -> float:

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def get_footage_files():

    if not os.path.exists(FOOTAGE_DIR):
        raise FileNotFoundError(
            f"Footage directory not found: {FOOTAGE_DIR}"
        )

    files = []

    for filename in os.listdir(FOOTAGE_DIR):

        if filename.lower().endswith(
            (".mp4", ".mov", ".mkv", ".avi")
        ):
            files.append(
                os.path.join(
                    FOOTAGE_DIR,
                    filename
                )
            )

    if not files:
        raise RuntimeError(
            "No footage files found in assets/footage."
        )

    return files


def generate_video(
    script: str,
    voice_path: str,
    output_filename: str = "short.mp4"
) -> str:

    if not script:
        raise ValueError("Script cannot be empty.")

    if not os.path.exists(voice_path):
        raise FileNotFoundError(
            f"Voice file not found: {voice_path}"
        )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    footage_files = get_footage_files()

    audio_duration = get_audio_duration(
        voice_path
    )

    print(
        f"Voice duration: {audio_duration:.2f} seconds",
        flush=True
    )

    # Select a random footage clip.
    selected_clip = random.choice(
        footage_files
    )

    print(
        f"Selected footage: {os.path.basename(selected_clip)}",
        flush=True
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    # Create a vertical 9:16 YouTube Short.
    #
    # The footage is:
    # - looped if necessary
    # - cropped to 9:16
    # - resized to 1080x1920
    # - matched to the voice duration
    #
    # The voice is added as the final audio track.

    command = [
        "ffmpeg",
        "-y",

        "-stream_loop",
        "-1",

        "-i",
        selected_clip,

        "-i",
        voice_path,

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1,"
            "format=yuv420p"
        ),

        "-t",
        str(audio_duration),

        "-r",
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-shortest",

        output_path,
    ]

    print(
        "Rendering vertical YouTube Short...",
        flush=True
    )

    subprocess.run(
        command,
        check=True
    )

    print(
        f"Video generated: {output_path}",
        flush=True
    )

    return output_path
