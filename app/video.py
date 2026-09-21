import os
import random
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
            f"Footage not found: {video_path}"
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
        "default=noprint_wrappers=1:nokey=0",
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
    # FIND ALL FOOTAGE
    # --------------------------------

    clips = []

    for filename in os.listdir(FOOTAGE_DIR):

        if filename.lower().endswith(".mp4"):

            clips.append(
                os.path.join(
                    FOOTAGE_DIR,
                    filename
                )
            )

    if len(clips) < 10:
        raise RuntimeError(
            f"Expected at least 10 MP4 clips, "
            f"but found only {len(clips)}."
        )

    # Use exactly 10 clips.
    clips = clips[:10]

    # Randomize order for every generated Short.
    random.shuffle(clips)

    print(
        "\n===== SELECTED FOOTAGE =====",
        flush=True
    )

    for index, clip in enumerate(
        clips,
        start=1
    ):
        print(
            f"{index}. {os.path.basename(clip)}",
            flush=True
        )

        validate_video(clip)

    print(
        "============================",
        flush=True
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

    # Each of the 10 clips gets an equal
    # section of the Short.
    segment_duration = (
        audio_duration / len(clips)
    )

    print(
        f"Each clip duration: "
        f"{segment_duration:.2f} seconds",
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
    # FFMPEG INPUTS
    # --------------------------------

    command = [
        "ffmpeg",
        "-y",
    ]

    # Add all 10 video inputs.
    # stream_loop allows a short source clip
    # to continue long enough for its segment.
    for clip in clips:

        command.extend([
            "-stream_loop",
            "-1",
            "-i",
            clip,
        ])

    # Add voiceover.
    command.extend([
        "-i",
        voice_path,
    ])

    # --------------------------------
    # FILTER GRAPH
    # --------------------------------

    filter_parts = []

    for index in range(len(clips)):

        filter_parts.append(
            f"[{index}:v]"
            f"trim=duration={segment_duration},"
            f"setpts=PTS-STARTPTS,"
            f"scale=1080:1920:"
            f"force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"setsar=1,"
            f"format=yuv420p"
            f"[v{index}]"
        )

    video_inputs = "".join(
        f"[v{i}]"
        for i in range(len(clips))
    )

    filter_parts.append(
        f"{video_inputs}"
        f"concat=n={len(clips)}:v=1:a=0,"
        f"format=yuv420p"
        f"[finalvideo]"
    )

    filter_complex = ";".join(
        filter_parts
    )

    audio_index = len(clips)

    command.extend([
        "-filter_complex",
        filter_complex,

        "-map",
        "[finalvideo]",

        "-map",
        f"{audio_index}:a:0",

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
    ])

    print(
        "\nRendering MIXED 10-CLIP YouTube Short...",
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
            "FFmpeg failed to render the mixed video."
        )

    # --------------------------------
    # VALIDATE OUTPUT
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
        "\n===== 10-CLIP VIDEO TEST: SUCCESS =====",
        flush=True
    )

    print(
        f"Final video: {output_path}",
        flush=True
    )

    return output_path
