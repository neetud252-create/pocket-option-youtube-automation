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

CTA_FILE = os.path.join(
    FOOTAGE_DIR,
    "activation_cta.mp4"
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

# 4 RANDOM CLIPS + 1 FIXED CTA CLIP
NUMBER_OF_CLIPS = 4

MIN_DURATION = 15.0
MAX_DURATION = 20.0

CTA_DURATION = 6.0

# OPENING TEXT NOW SHOWS FOR 5 SECONDS
OPENING_TEXT_DURATION = 5.0


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
# GET ELEVENLABS CTA TIMING
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

    if os.path.exists(
        metadata_path
    ):

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
    # CHECK CTA FILE
    # ========================================================

    if not os.path.exists(
        CTA_FILE
    ):
        raise FileNotFoundError(
            f"CTA video not found: {CTA_FILE}"
        )

    cta_actual_duration = validate_video(
        CTA_FILE
    )

    print(
        f"\nCTA video found: "
        f"{os.path.basename(CTA_FILE)}",
        flush=True
    )

    print(
        f"CTA duration: "
        f"{cta_actual_duration:.2f}s",
        flush=True
    )

    # ========================================================
    # FIND ALL NORMAL FOOTAGE
    # ========================================================

    all_clips = []

    for filename in os.listdir(
        FOOTAGE_DIR
    ):

        if filename.lower().endswith(
            ".mp4"
        ):

            # IMPORTANT:
            # CTA MUST NEVER BE RANDOMLY SELECTED
            if filename.lower() == "activation_cta.mp4":
                continue

            all_clips.append(
                os.path.join(
                    FOOTAGE_DIR,
                    filename
                )
            )

    all_clips.sort()

    print(
        f"\nFound {len(all_clips)} normal MP4 clips.",
        flush=True
    )

    if len(all_clips) < NUMBER_OF_CLIPS:

        raise RuntimeError(
            f"Need at least {NUMBER_OF_CLIPS} "
            f"normal footage clips. "
            f"Found {len(all_clips)}."
        )

    # ========================================================
    # SELECT EXACTLY 4 RANDOM NORMAL CLIPS
    # ========================================================

    selected_clips = random.sample(
        all_clips,
        NUMBER_OF_CLIPS
    )

    random.shuffle(
        selected_clips
    )

    print(
        "\n===== SELECTED RANDOM CLIPS =====",
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
        "=================================",
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

    # ========================================================
    # MAIN VIDEO DURATION
    # ========================================================

    main_duration = min(
        voice_duration,
        MAX_DURATION
    )

    if main_duration < MIN_DURATION:

        raise RuntimeError(
            f"Voice is only "
            f"{main_duration:.2f}s. "
            f"Need at least "
            f"{MIN_DURATION:.2f}s."
        )

    # Final duration = main video + CTA
    final_duration = (
        main_duration
        + cta_actual_duration
    )

    print(
        f"Main content duration: "
        f"{main_duration:.2f}s",
        flush=True
    )

    print(
        f"CTA duration: "
        f"{cta_actual_duration:.2f}s",
        flush=True
    )

    print(
        f"Final Short duration: "
        f"{final_duration:.2f}s",
        flush=True
    )

    # ========================================================
    # OLD ELEVENLABS CTA TIMING
    # KEEPING FOR TESTING
    # ========================================================

    cta_start, cta_end = get_cta_timing(
        voice_path,
        main_duration
    )

    print(
        "\n===== OLD CTA TIMING =====",
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
        "==========================",
        flush=True
    )

    # ========================================================
    # CLIP DURATION
    # ========================================================

    clip_duration = (
        main_duration
        /
        NUMBER_OF_CLIPS
    )

    print(
        f"\nEach selected clip: "
        f"{clip_duration:.2f}s",
        flush=True
    )

    # ========================================================
    # TEMPORARY MAIN VIDEO
    # ========================================================

    temp_main = os.path.join(
        OUTPUT_DIR,
        "temp_main.mp4"
    )

    if os.path.exists(
        temp_main
    ):
        os.remove(
            temp_main
        )

    # ========================================================
    # STEP 1 — CREATE 1080P MAIN CLIP SEQUENCE
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
            f"{main_duration:.4f},"
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
        f"{main_duration:.3f}",

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

        temp_main
    ])

    print(
        "\nStep 1/3: "
        "Creating 1080p main clip sequence...",
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
            "1080p main clip sequence rendering failed."
        )

    if not os.path.exists(
        temp_main
    ):

        raise RuntimeError(
            "Temporary main video was not created."
        )

    # ========================================================
    # STEP 2 — 4K MAIN VIDEO
    # ========================================================

    temp_4k = os.path.join(
        OUTPUT_DIR,
        "temp_main_4k.mp4"
    )

    if os.path.exists(
        temp_4k
    ):
        os.remove(
            temp_4k
        )

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
    # OPENING TEXT
    # ========================================================

    opening_text = (
        f"I MADE\\: "
        f"${short_amount} EVERY DAY"
    )

    # ========================================================
    # MAIN VIDEO FILTER
    # ========================================================

    main_filter = (

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
        # OPENING TEXT — FIRST 5 SECONDS
        # ====================================================

        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        f"text='{opening_text}':"
        "fontcolor=#9CFF00:"
        "bordercolor=black:"
        "borderw=12:"
        "fontsize=92:"
        "x=(w-text_w)/2:"
        "y=500:"
        "enable='between(t,0,5)',"

        # ----------------------------------------------------
        # LINE 2
        # ----------------------------------------------------

        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:"
        "text='LINK IN BIO':"
        "fontcolor=#FFF500:"
        "bordercolor=black:"
        "borderw=12:"
        "fontsize=120:"
        "x=(w-text_w)/2:"
        "y=680:"
        "enable='between(t,0,5)',"

        # ====================================================
        # RED ANIMATED BOTTOM ARROW
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

        "[mainvideo]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        temp_main,

        "-filter_complex",
        main_filter,

        "-map",
        "[mainvideo]",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        temp_4k
    ]

    print(
        "\nStep 2/3: "
        "Upscaling main video to 4K + existing testing text + arrow...",
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
            "4K main video rendering failed."
        )

    if not os.path.exists(
        temp_4k
    ):

        raise RuntimeError(
            "Temporary 4K main video was not created."
        )

    # ========================================================
    # STEP 3 — APPEND FIXED CTA VIDEO
    # ========================================================

    print(
        "\nStep 3/3: "
        "Appending activation_cta.mp4...",
        flush=True
    )

    final_command = [
        "ffmpeg",
        "-y",

        # MAIN VIDEO
        "-i",
        temp_4k,

        # CTA VIDEO
        "-i",
        CTA_FILE,

        # VOICE AUDIO
        "-i",
        voice_path,

        "-filter_complex",

        (
            "[0:v]"
            "setpts=PTS-STARTPTS"
            "[main];"

            "[1:v]"
            "scale=2160:3840:"
            "force_original_aspect_ratio=increase:"
            "flags=lanczos,"
            "crop=2160:3840,"
            "setsar=1,"
            "fps=30,"
            "format=yuv420p,"
            "setpts=PTS-STARTPTS"
            "[cta];"

            "[main][cta]"
            "concat=n=2:v=1:a=0"
            "[finalvideo]"
        ),

        "-map",
        "[finalvideo]",

        "-map",
        "2:a",

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

    result = subprocess.run(
        final_command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "\n===== STEP 3 FFMPEG ERROR =====",
            flush=True
        )

        print(
            result.stderr[-12000:],
            flush=True
        )

        raise RuntimeError(
            "CTA append rendering failed."
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
        f"Random test amount: "
        f"${short_amount}",
        flush=True
    )

    print(
        "Opening text:",
        flush=True
    )

    print(
        f"I MADE: "
        f"${short_amount} EVERY DAY",
        flush=True
    )

    print(
        "LINK IN BIO",
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

    print(
        "Final CTA: activation_cta.mp4",
        flush=True
    )

    print(
        f"Final CTA duration: "
        f"{cta_actual_duration:.2f}s",
        flush=True
    )

    # ========================================================
    # REMOVE TEMPORARY FILES
    # ========================================================

    for temp_file in [
        temp_main,
        temp_4k
    ]:

        try:

            if os.path.exists(
                temp_file
            ):

                os.remove(
                    temp_file
                )

        except Exception:
            pass

    print(
        "\n===== 4-CLIP + CTA 4K VIDEO SUCCESS =====",
        flush=True
    )

    print(
        f"Final video: "
        f"{output_path}",
        flush=True
    )

    return output_path
