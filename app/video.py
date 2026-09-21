import os
import subprocess


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FOOTAGE_DIR = os.path.join(
    BASE_DIR,
    "assets",
    "footage"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

# TEST MODE
# We are deliberately using one known clip first.
TEST_FOOTAGE = "01_chart_overview.mp4"


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
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Could not read audio duration:\n"
            + result.stderr
        )

    return float(
        result.stdout.strip()
    )


def validate_video(video_path: str):

    if not os.path.exists(video_path):
        raise FileNotFoundError(
            f"Test footage not found: {video_path}"
        )

    print(
        f"Checking footage: "
        f"{os.path.basename(video_path)}",
        flush=True
    )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,duration",
        "-of",
        "default=noprint_wrappers=1",
        video_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "FFprobe could not read the footage:\n"
            + result.stderr
        )

    if not result.stdout.strip():
        raise RuntimeError(
            "The footage does not contain a valid video stream."
        )

    print(
        "Footage validation successful.",
        flush=True
    )

    print(
        result.stdout.strip(),
        flush=True
    )


def generate_video(
    script: str,
    voice_path: str,
    output_filename: str = "test_short.mp4"
) -> str:

    if not script:
        raise ValueError(
            "Script cannot be empty."
        )

    if not os.path.exists(voice_path):
        raise FileNotFoundError(
            f"Voice file not found: {voice_path}"
        )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # --------------------------------
    # TEST FOOTAGE
    # --------------------------------

    selected_clip = os.path.join(
        FOOTAGE_DIR,
        TEST_FOOTAGE
    )

    print(
        f"Using TEST footage: {TEST_FOOTAGE}",
        flush=True
    )

    validate_video(
        selected_clip
    )

    # --------------------------------
    # AUDIO DURATION
    # --------------------------------

    audio_duration = get_audio_duration(
        voice_path
    )

    print(
        f"Voice duration: "
        f"{audio_duration:.2f} seconds",
        flush=True
    )

    # --------------------------------
    # OUTPUT
    # --------------------------------

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    # --------------------------------
    # FFMPEG
    # --------------------------------

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

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        print(
            "FFmpeg rendering failed.",
            flush=True
        )

        print(
            result.stderr,
            flush=True
        )

        raise RuntimeError(
            "FFmpeg failed to render the video."
        )

    print(
        f"Video generated: {output_path}",
        flush=True
    )

    # --------------------------------
    # FINAL OUTPUT VALIDATION
    # --------------------------------

    if not os.path.exists(output_path):
        raise RuntimeError(
            "FFmpeg finished but output video "
            "was not created."
        )

    output_size = os.path.getsize(
        output_path
    )

    print(
        f"Final video size: "
        f"{output_size / 1024 / 1024:.2f} MB",
        flush=True
    )

    if output_size < 10000:
        raise RuntimeError(
            "Generated video appears to be empty."
        )

    print(
        "VIDEO RENDER TEST: SUCCESS",
        flush=True
    )

    return output_path
