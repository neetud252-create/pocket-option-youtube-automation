import os
import random
import subprocess
import json


# ============================================================
# PATHS
# ============================================================

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


# ============================================================
# VIDEO SETTINGS
# ============================================================

TARGET_WIDTH = 2160
TARGET_HEIGHT = 3840

NUMBER_OF_CLIPS = 5

MIN_DURATION = 15.0
MAX_DURATION = 20.0

OPENING_TEXT_DURATION = 3.0


# ============================================================
# GET MEDIA DURATION
# ============================================================

def get_media_duration(file_path: str) -> float:

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
            f"Could not read media duration: {file_path}"
        )

    data = json.loads(
        result.stdout
    )

    return float(
        data["format"]["duration"]
    )


# ============================================================
# VALIDATE VIDEO
# ============================================================

def validate_video(file_path: str):

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            f"Video not found: {file_path}"
        )

    duration = get_media_duration(
        file_path
    )

    if duration <= 0:

        raise RuntimeError(
            f"Invalid video: {file_path}"
        )

    print(
        f"Validated: "
        f"{os.path.basename(file_path)} "
        f"({duration:.2f}s)",
        flush=True
    )

    return duration


# ============================================================
# ELEVENLABS CTA TIMING
# ============================================================

def get_cta_timing(
    voice_path: str,
    final_duration: float
):

    metadata_path = (
        os.path.splitext(
            voice_path
        )[0]
        + ".json"
    )

    print(
        "\nLooking for ElevenLabs timing metadata:",
        flush=True
    )

    print(
        metadata_path,
        flush=True
    )

    cta_start = None
    cta_end = None

    if os.path.exists(metadata_path):

        try:

            with open(
                metadata_path,
                "r",
                encoding="utf-8"
            ) as metadata_file:

                metadata = json.load(
                    metadata_file
                )

            cta_start = metadata.get(
                "cta_start"
            )

            cta_end = metadata.get(
                "cta_end"
            )

            if cta_start is not None:

                cta_start = float(
                    cta_start
                )

            if cta_end is not None:

                cta_end = float(
                    cta_end
                )

            print(
                f"ElevenLabs CTA start: "
                f"{cta_start}",
                flush=True
            )

            print(
                f"ElevenLabs CTA end: "
                f"{cta_end}",
                flush=True
            )

        except Exception as e:

            print(
                f"Could not read timing metadata: {e}",
                flush=True
            )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if (
        cta_start is None
        or cta_end is None
    ):

        print(
            "CTA timing unavailable.",
            flush=True
        )

        print(
            "Using 50% fallback timing.",
            flush=True
        )

        cta_start = (
            final_duration * 0.50
        )

        cta_end = final_duration

    # --------------------------------------------------------
    # SAFETY LIMITS
    # --------------------------------------------------------

    cta_start = max(
        0.0,
        min(
            cta_start,
            final_duration
        )
    )

    cta_end = max(
        cta_start,
        min(
            cta_end,
            final_duration
        )
    )

    return (
        cta_start,
        cta_end
    )


# ============================================================
# GENERATE VIDEO
# ============================================================

def generate_video(
    script: str,
    voice_path: str,
    output_filename: str = "short.mp4",
    short_amount: int = 1500
) -> str:

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # ========================================================
    # FIND ALL FOOTAGE
    # ========================================================

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

    # ========================================================
    # SELECT EXACTLY 5 RANDOM CLIPS
    # ========================================================

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

    # ========================================================
    # VOICE DURATION
    # ========================================================

    voice_duration = get_media_duration(
        voice_path
    )

    print(
        f"Voice duration: "
        f"{voice_duration:.2f} seconds",
        flush=True
    )

    final_duration = min(
        voice_duration,
        MAX_DURATION
    )

    if final_duration < MIN_DURATION:

        raise RuntimeError(
            f"Voice is only "
            f"{final_duration:.2f}s. "
            f"Need at least "
            f"{MIN_DURATION:.2f}s."
        )

    print(
        f"Final Short duration target: "
        f"{final_duration:.2f}s",
        flush=True
    )

    # ========================================================
    # CTA TIMING
    # ========================================================

    cta_start, cta_end = get_cta_timing(
        voice_path,
        final_duration
    )

    print(
        "\n===== CTA TIMING =====",
        flush=True
    )

    print(
        f"CTA starts: "
        f"{cta_start:.2f}s",
        flush=True
    )

    print(
        f"CTA ends: "
        f"{cta_end:.2f}s",
        flush=True
    )

    print(
        "======================",
        flush=True
    )

    # ========================================================
    # CLIP DURATION
    # ========================================================

    clip_duration = (
        final_duration
        /
        NUMBER_OF_CLIPS
    )

    print(
        f"\nEach selected clip: "
        f"{clip_duration:.2f}s",
        flush=True
    )

    # ========================================================
    # TEMPORARY 1080P FILE
    # ========================================================

    temp_concat = os.path.join(
        OUTPUT_DIR,
        "temp_concat.mp4"
    )

    if os.path.exists(
        temp_concat
    ):

        os.remove(
            temp_concat
        )

    # ========================================================
    # STEP 1 — 1080P CLIP SEQUENCE
    # ========================================================

    filter_parts = []

    for index in range(
        NUMBER_OF_CLIPS
    ):

        filter_parts.append(
            (
                f"[{index}:v]"
                f"trim="
                f"duration="
                f"{clip_duration:.4f},"
                f"setpts=PTS-STARTPTS,"
                f"scale=1080:1920:"
                f"force_original_aspect_ratio=increase:"
                f"flags=lanczos,"
                f"crop=1080:1920,"
                f"setsar=1,"
                f"format=yuv420p"
                f"[v{index}]"
            )
        )

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
            f"trim="
            f"duration="
            f"{final_duration:.4f},"
            f"setpts=PTS-STARTPTS"
            f"[concatvideo]"
        )
    )

    filter_complex = ";".join(
        filter_parts
    )

    command = [
        "ffmpeg",
        "-y"
    ]

    for clip in selected_clips:

        command.extend([
            "-stream_loop",
            "-1",
            "-i",
            clip
        ])

    command.extend([
        "-filter_complex",
        filter_complex,

        "-map",
        "[concatvideo]",

        "-an",

        "-t",
        f"{final_duration:.3f}",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        temp_concat
    ])

    print(
        "\nStep 1/2: "
        "Creating 1080p clip sequence...",
        flush=True
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "\n===== STEP 1 FFMPEG ERROR =====",
            flush=True
        )

        print(
            result.stderr[-12000:],
            flush=True
        )

        raise RuntimeError(
            "1080p clip sequence rendering failed."
        )

    if not os.path.exists(
        temp_concat
    ):

        raise RuntimeError(
            "Temporary clip sequence "
            "was not created."
        )

    # ========================================================
    # STEP 2 — 4K + TEXT + ANIMATED RED ARROW
    # ========================================================

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    if os.path.exists(
        output_path
    ):

        os.remove(
            output_path
        )

    # ========================================================
    # IMPORTANT:
    # The colon after "EXAMPLE" is escaped as \:
    # so FFmpeg doesn't treat it as a filter separator.
    # ========================================================

    opening_text = (
        f"AI TRADING EXAMPLE\\: ${short_amount}"
    )

    final_filter = (

        "[0:v]"

        # ----------------------------------------------------
        # 4K UPSCALE
        # ----------------------------------------------------

        "scale=2160:3840:"
        "flags=lanczos,"

        # ----------------------------------------------------
        # IMAGE ENHANCEMENT
        # ----------------------------------------------------

        "unsharp=5:5:0.45:5:5:0,"
        "eq=contrast=1.02:saturation=1.03,"

        # ====================================================
        # OPENING TEXT — FIRST 3 SECONDS
        # ====================================================

        # LINE 1
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        f"text='{opening_text}':"
        "fontcolor=#9CFF00:"
        "bordercolor=black:"
        "borderw=12:"
        "fontsize=105:"
        "x=(w-text_w)/2:"
        "y=430:"
        "enable='between(t,0,3)',"

        # LINE 2
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        "text='USING AI':"
        "fontcolor=#FFF500:"
        "bordercolor=black:"
        "borderw=12:"
        "fontsize=118:"
        "x=(w-text_w)/2:"
        "y=580:"
        "enable='between(t,0,3)',"

        # LINE 3
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        "text='LINK IN BIO':"
        "fontcolor=#FFF500:"
        "bordercolor=black:"
        "borderw=10:"
        "fontsize=105:"
        "x=(w-text_w)/2:"
        "y=730:"
        "enable='between(t,0,3)',"

        # ====================================================
        # RED ANIMATED ARROW
        # ====================================================

        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        "text='↓':"
        "fontcolor=#FF0000:"
        "bordercolor=black:"
        "borderw=14:"
        "fontsize=300:"
        "x=(w-text_w)/2:"
        "y=3200+70*sin(t*8):"
        f"enable='between(t,"
        f"{cta_start:.3f},"
        f"{cta_end:.3f})'"

        "[finalvideo]"
    )

    # ========================================================
    # FINAL FFMPEG RENDER
    # ========================================================

    command = [
        "ffmpeg",
        "-y",

        "-i",
        temp_concat,

        "-i",
        voice_path,

        "-filter_complex",
        final_filter,

        "-map",
        "[finalvideo]",

        "-map",
        "1:a",

        "-t",
        f"{final_duration:.3f}",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-movflags",
        "+faststart",

        output_path
    ]

    print(
        "\nStep 2/2: "
        "Upscaling to 4K + opening text "
        "+ animated red bottom arrow...",
        flush=True
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "\n===== STEP 2 FFMPEG ERROR =====",
            flush=True
        )

        print(
            result.stderr[-12000:],
            flush=True
        )

        raise RuntimeError(
            "4K final rendering failed."
        )

    # ========================================================
    # VERIFY OUTPUT
    # ========================================================

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
        f"Random demo amount: "
        f"${short_amount}",
        flush=True
    )

    print(
        "Opening text duration: "
        f"{OPENING_TEXT_DURATION:.2f}s",
        flush=True
    )

    print(
        "CTA arrow: RED + ANIMATED + BOTTOM",
        flush=True
    )

    # ========================================================
    # REMOVE TEMP FILE
    # ========================================================

    try:

        os.remove(
            temp_concat
        )

    except Exception:

        pass

    print(
        "\n===== 5-CLIP 4K VIDEO SUCCESS =====",
        flush=True
    )

    print(
        f"Final video: "
        f"{output_path}",
        flush=True
    )

    return output_path
