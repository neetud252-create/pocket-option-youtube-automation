import os
import random
import subprocess
import json


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


TARGET_WIDTH = 2160
TARGET_HEIGHT = 3840

NUMBER_OF_CLIPS = 5

MIN_DURATION = 15.0
MAX_DURATION = 20.0


def get_media_duration(
    file_path: str
) -> float:

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        file_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read duration: {file_path}"
        )

    data = json.loads(
        result.stdout
    )

    return float(
        data["format"]["duration"]
    )


def validate_video(
    file_path: str
):

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Video not found: {file_path}"
        )

    duration = get_media_duration(
        file_path
    )

    if duration <= 0:
        raise RuntimeError(
            f"Invalid video duration: {file_path}"
        )

    print(
        f"Validated: {os.path.basename(file_path)} "
        f"({duration:.2f}s)",
        flush=True
    )

    return duration


def get_voice_duration(
    voice_path: str
) -> float:

    return get_media_duration(
        voice_path
    )


def generate_video(
    script: str,
    voice_path: str,
    output_filename: str = "short.mp4"
) -> str:

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    if not os.path.exists(FOOTAGE_DIR):
        raise FileNotFoundError(
            f"Footage directory not found: "
            f"{FOOTAGE_DIR}"
        )

    # ---------------------------------------------------------
    # FIND ALL FOOTAGE
    # ---------------------------------------------------------

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

    all_clips.sort()

    print(
        f"\nFound {len(all_clips)} MP4 clips.",
        flush=True
    )

    if len(all_clips) < 10:
        raise RuntimeError(
            f"Need at least 10 clips. "
            f"Found {len(all_clips)}."
        )

    # ---------------------------------------------------------
    # RANDOMLY SELECT EXACTLY 5 CLIPS
    # ---------------------------------------------------------

    selected_clips = random.sample(
        all_clips,
        NUMBER_OF_CLIPS
    )

    random.shuffle(
        selected_clips
    )

    print(
        "\n===== SELECTED CLIPS =====",
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
        "==========================",
        flush=True
    )

    # ---------------------------------------------------------
    # VOICE DURATION
    # ---------------------------------------------------------

    voice_duration = get_voice_duration(
        voice_path
    )

    print(
        f"\nVoice duration: "
        f"{voice_duration:.2f} seconds",
        flush=True
    )

    # ---------------------------------------------------------
    # TARGET VIDEO DURATION
    #
    # Keep final Short between 15 and 20 seconds.
    # ---------------------------------------------------------

    final_duration = min(
        voice_duration,
        MAX_DURATION
    )

    if final_duration < MIN_DURATION:

        raise RuntimeError(
            f"Voice is only "
            f"{final_duration:.2f}s. "
            f"Need at least {MIN_DURATION}s."
        )

    print(
        f"Final Short duration target: "
        f"{final_duration:.2f}s",
        flush=True
    )

    # ---------------------------------------------------------
    # CTA TIMING
    #
    # Our script is intentionally divided approximately
    # 50/50 between BOT explanation and CTA.
    #
    # Therefore the arrow appears during the second half.
    # ---------------------------------------------------------

    cta_start = final_duration * 0.50

    cta_end = final_duration

    print(
        f"CTA starts at: "
        f"{cta_start:.2f}s",
        flush=True
    )

    print(
        f"CTA ends at: "
        f"{cta_end:.2f}s",
        flush=True
    )

    # ---------------------------------------------------------
    # EACH CLIP DURATION
    # ---------------------------------------------------------

    clip_duration = (
        final_duration /
        NUMBER_OF_CLIPS
    )

    print(
        f"Each selected clip: "
        f"{clip_duration:.2f}s",
        flush=True
    )

    # ---------------------------------------------------------
    # BUILD FILTERS
    # ---------------------------------------------------------

    filter_parts = []

    for index in range(
        NUMBER_OF_CLIPS
    ):

        filter_parts.append(
            (
                f"[{index}:v]"
                f"trim=duration={clip_duration:.4f},"
                f"setpts=PTS-STARTPTS,"
                f"scale={TARGET_WIDTH}:"
                f"{TARGET_HEIGHT}:"
                f"force_original_aspect_ratio=increase:"
                f"flags=lanczos,"
                f"crop={TARGET_WIDTH}:"
                f"{TARGET_HEIGHT},"
                f"setsar=1,"
                f"unsharp="
                f"5:5:0.65:"
                f"5:5:0,"
                f"eq="
                f"contrast=1.02:"
                f"saturation=1.03,"
                f"format=yuv420p"
                f"[v{index}]"
            )
        )

    # ---------------------------------------------------------
    # CONCATENATE 5 CLIPS
    # ---------------------------------------------------------

    concat_inputs = "".join(
        f"[v{i}]"
        for i in range(
            NUMBER_OF_CLIPS
        )
    )

    filter_parts.append(
        (
            f"{concat_inputs}"
            f"concat="
            f"n={NUMBER_OF_CLIPS}:"
            f"v=1:"
            f"a=0,"
            f"trim=duration={final_duration:.4f},"
            f"setpts=PTS-STARTPTS"
            f"[basevideo]"
        )
    )

    # ---------------------------------------------------------
    # CTA ARROW
    #
    # Arrow appears ONLY during the CTA.
    #
    # Large white arrow with black outline makes it visible
    # against different footage.
    # ---------------------------------------------------------

    arrow_filter = (
        "[basevideo]"
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        "text='↓':"
        "fontcolor=white:"
        "bordercolor=black:"
        "borderw=12:"
        "fontsize=300:"
        "x=(w-text_w)/2:"
        "y=3000:"
        f"enable='between(t,{cta_start:.3f},{cta_end:.3f})'"
        "[finalvideo]"
    )

    filter_parts.append(
        arrow_filter
    )

    filter_complex = ";".join(
        filter_parts
    )

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    # Remove old output
    if os.path.exists(
        output_path
    ):

        os.remove(
            output_path
        )

    # ---------------------------------------------------------
    # FFMPEG COMMAND
    # ---------------------------------------------------------

    command = [
        "ffmpeg",
        "-y"
    ]

    # Add each selected clip
    for clip in selected_clips:

        command.extend([
            "-stream_loop",
            "-1",
            "-i",
            clip
        ])

    # Add voice
    command.extend([
        "-i",
        voice_path
    ])

    command.extend([
        "-filter_complex",
        filter_complex,

        "-map",
        "[finalvideo]",

        "-map",
        f"{NUMBER_OF_CLIPS}:a",

        "-t",
        f"{final_duration:.3f}",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "19",

        "-profile:v",
        "high",

        "-level",
        "5.2",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "44100",

        "-movflags",
        "+faststart",

        output_path
    ])

    print(
        "\nRendering 5-CLIP 4K Short...",
        flush=True
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "\n===== FFMPEG ERROR =====",
            flush=True
        )

        print(
            result.stderr[-10000:],
            flush=True
        )

        raise RuntimeError(
            "FFmpeg video rendering failed."
        )

    # ---------------------------------------------------------
    # VERIFY OUTPUT
    # ---------------------------------------------------------

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "Final video was not created."
        )

    final_file_duration = (
        get_media_duration(
            output_path
        )
    )

    file_size_mb = (
        os.path.getsize(
            output_path
        )
        /
        (1024 * 1024)
    )

    print(
        f"\nFinal video size: "
        f"{file_size_mb:.2f} MB",
        flush=True
    )

    print(
        f"Final video duration: "
        f"{final_file_duration:.2f}s",
        flush=True
    )

    print(
        f"Final resolution: "
        f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
        flush=True
    )

    print(
        "\n===== 5-CLIP 4K VIDEO SUCCESS =====",
        flush=True
    )

    print(
        f"Final video: {output_path}",
        flush=True
    )

    return output_path
