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


MIN_DURATION = 15.0
MAX_DURATION = 20.0

CLIPS_PER_SHORT = 5


def get_duration(file_path: str) -> float:

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read duration:\n"
            f"{result.stderr}"
        )

    return float(
        result.stdout.strip()
    )


def validate_video(video_path: str):

    if not os.path.exists(video_path):
        raise FileNotFoundError(
            f"Footage not found: {video_path}"
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
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Invalid video:\n"
            f"{result.stderr}"
        )

    if not result.stdout.strip():
        raise RuntimeError(
            "Video does not contain a valid video stream."
        )

    print(
        f"Validated: "
        f"{os.path.basename(video_path)}",
        flush=True
    )


def create_arrow_overlay(
    output_path: str,
    duration: float
):

    # Large animated downward arrow.
    #
    # It points toward the lower part of the
    # Shorts player where the Related Video
    # link can appear.

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        (
            f"color=c=black@0.0:"
            f"s=1080x1920:"
            f"d={duration}:"
            f"r=30"
        ),

        "-vf",
        (
            "format=rgba,"
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "text='↓':"
            "fontcolor=white:"
            "fontsize=150:"
            "x=(w-text_w)/2:"
            "y=1650"
        ),

        "-c:v",
        "qtrle",

        output_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Could not create arrow overlay:\n"
            + result.stderr
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

    all_clips = []

    for filename in os.listdir(
        FOOTAGE_DIR
    ):

        if filename.lower().endswith(
            ".mp4"
        ):

            all_clips.append(
                os.path.join(
                    FOOTAGE_DIR,
                    filename
                )
            )

    if len(all_clips) < 10:

        raise RuntimeError(
            f"Expected 10 footage clips, "
            f"but found {len(all_clips)}."
        )

    # --------------------------------
    # RANDOMLY SELECT EXACTLY 5
    # --------------------------------

    selected_clips = random.sample(
        all_clips,
        CLIPS_PER_SHORT
    )

    random.shuffle(
        selected_clips
    )

    print(
        "\n===== RANDOM 5-CLIP SELECTION =====",
        flush=True
    )

    for index, clip in enumerate(
        selected_clips,
        start=1
    ):

        print(
            f"{index}. "
            f"{os.path.basename(clip)}",
            flush=True
        )

        validate_video(
            clip
        )

    print(
        "====================================",
        flush=True
    )

    # --------------------------------
    # VOICE DURATION
    # --------------------------------

    voice_duration = get_duration(
        voice_path
    )

    print(
        f"Voice duration: "
        f"{voice_duration:.2f} seconds",
        flush=True
    )

    # We need the final video to be
    # between 15 and 20 seconds.
    #
    # If voice is longer than 20 seconds,
    # this test uses the first 20 seconds.
    #
    # If voice is shorter than 15 seconds,
    # the video follows the voice duration.

    final_duration = min(
        voice_duration,
        MAX_DURATION
    )

    if final_duration < MIN_DURATION:

        print(
            f"Voice is shorter than "
            f"{MIN_DURATION}s. "
            f"Using {final_duration:.2f}s.",
            flush=True
        )

    else:

        print(
            f"Final Short duration target: "
            f"{final_duration:.2f}s",
            flush=True
        )

    # --------------------------------
    # EACH CLIP DURATION
    # --------------------------------

    clip_duration = (
        final_duration /
        CLIPS_PER_SHORT
    )

    print(
        f"Each selected clip: "
        f"{clip_duration:.2f}s",
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

    for clip in selected_clips:

        command.extend([
            "-stream_loop",
            "-1",
            "-i",
            clip
        ])

    # Voice input.
    command.extend([
        "-i",
        voice_path
    ])

    # --------------------------------
    # VIDEO FILTER
    # --------------------------------

    filter_parts = []

    for index in range(
        CLIPS_PER_SHORT
    ):

        filter_parts.append(
            f"[{index}:v]"
            f"trim=duration={clip_duration},"
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
        for i in range(
            CLIPS_PER_SHORT
        )
    )

    filter_parts.append(
        f"{video_inputs}"
        f"concat=n={CLIPS_PER_SHORT}:"
        f"v=1:a=0,"
        f"format=yuv420p"
        f"[basevideo]"
    )

    # --------------------------------
    # ARROW
    # --------------------------------

    filter_parts.append(
        "[basevideo]"
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf:"
        "text='↓':"
        "fontcolor=white:"
        "fontsize=150:"
        "borderw=8:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=1640"
        "[finalvideo]"
    )

    filter_complex = ";".join(
        filter_parts
    )

    audio_index = CLIPS_PER_SHORT

    command.extend([
        "-filter_complex",
        filter_complex,

        "-map",
        "[finalvideo]",

        "-map",
        f"{audio_index}:a:0",

        "-t",
        str(final_duration),

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

        output_path
    ])

    # --------------------------------
    # RENDER
    # --------------------------------

    print(
        "\nRendering 5-CLIP Short...",
        flush=True
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
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
            "FFmpeg failed."
        )

    # --------------------------------
    # VALIDATE OUTPUT
    # --------------------------------

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "Output video was not created."
        )

    output_size = os.path.getsize(
        output_path
    )

    final_file_duration = get_duration(
        output_path
    )

    print(
        f"Final video size: "
        f"{output_size / 1024 / 1024:.2f} MB",
        flush=True
    )

    print(
        f"Final video duration: "
        f"{final_file_duration:.2f}s",
        flush=True
    )

    if output_size < 10000:

        raise RuntimeError(
            "Generated video appears empty."
        )

    print(
        "\n===== 5-CLIP VIDEO TEST: SUCCESS =====",
        flush=True
    )

    print(
        f"Final video: {output_path}",
        flush=True
    )

    return output_path
