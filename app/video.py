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

CTA_FILE = os.path.join(
    FOOTAGE_DIR,
    "activation_cta.mp4"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

TARGET_WIDTH = 2160
TARGET_HEIGHT = 3840

NUMBER_OF_CLIPS = 4

MIN_FINAL_DURATION = 20.0
MAX_FINAL_DURATION = 25.0

CTA_TARGET_DURATION = 6.0

OPENING_TEXT_DURATION = 5.0


# ============================================================
# MEDIA DURATION
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
        f"Validated: {os.path.basename(file_path)} "
        f"({duration:.2f}s)",
        flush=True
    )

    return duration


# ============================================================
# CTA DURATION
# ============================================================

def get_cta_duration():

    duration = validate_video(
        CTA_FILE
    )

    print(
        f"CTA actual duration: {duration:.2f}s",
        flush=True
    )

    return duration


# ============================================================
# FORCE CTA TO EXACTLY 6 SECONDS
# ============================================================

def create_cta_6sec():

    cta_6sec = os.path.join(
        OUTPUT_DIR,
        "cta_6sec.mp4"
    )

    if os.path.exists(cta_6sec):
        os.remove(cta_6sec)

    command = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        CTA_FILE,

        "-t",
        f"{CTA_TARGET_DURATION:.3f}",

        "-vf",
        (
            "scale=2160:3840:"
            "force_original_aspect_ratio=increase:"
            "flags=lanczos,"
            "crop=2160:3840,"
            "setsar=1,"
            "fps=30,"
            "format=yuv420p"
        ),

        "-an",

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

        cta_6sec
    ]

    print(
        "\nCreating fixed 6-second CTA...",
        flush=True
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "\n===== CTA FFMPEG ERROR =====",
            flush=True
        )

        print(
            result.stderr[-12000:],
            flush=True
        )

        raise RuntimeError(
            "6-second CTA creation failed."
        )

    if not os.path.exists(cta_6sec):

        raise RuntimeError(
            "6-second CTA file was not created."
        )

    actual_duration = get_media_duration(
        cta_6sec
    )

    print(
        f"Fixed CTA duration: {actual_duration:.2f}s",
        flush=True
    )

    return cta_6sec


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

    # --------------------------------------------------------
    # CHECK CTA
    # --------------------------------------------------------

    if not os.path.exists(CTA_FILE):

        raise FileNotFoundError(
            f"CTA video not found: {CTA_FILE}"
        )

    original_cta_duration = get_cta_duration()

    print(
        "\n===== CTA INFORMATION =====",
        flush=True
    )

    print(
        "CTA file: activation_cta.mp4",
        flush=True
    )

    print(
        f"Original CTA duration: "
        f"{original_cta_duration:.2f}s",
        flush=True
    )

    print(
        "Final CTA duration: 6.00s",
        flush=True
    )

    print(
        "CTA message: Go to channel description "
        "and click the Bot Activation button.",
        flush=True
    )

    print(
        "===========================",
        flush=True
    )

    # --------------------------------------------------------
    # RANDOM TOTAL SHORT DURATION
    # --------------------------------------------------------

    target_final_duration = random.uniform(
        MIN_FINAL_DURATION,
        MAX_FINAL_DURATION
    )

    # Round to milliseconds
    target_final_duration = round(
        target_final_duration,
        3
    )

    # Main footage duration = total - 6 sec CTA
    main_duration = (
        target_final_duration
        - CTA_TARGET_DURATION
    )

    print(
        "\n===== RANDOM SHORT DURATION =====",
        flush=True
    )

    print(
        f"Random total duration: "
        f"{target_final_duration:.3f}s",
        flush=True
    )

    print(
        f"Main footage duration: "
        f"{main_duration:.3f}s",
        flush=True
    )

    print(
        "CTA duration: 6.000s",
        flush=True
    )

    print(
        f"Final duration: "
        f"{target_final_duration:.3f}s",
        flush=True
    )

    print(
        "=================================",
        flush=True
    )

    # --------------------------------------------------------
    # FIND NORMAL FOOTAGE
    # --------------------------------------------------------

    all_clips = []

    for filename in os.listdir(
        FOOTAGE_DIR
    ):

        if filename.lower().endswith(".mp4"):

            if filename.lower() == "activation_cta.mp4":
                continue

            if filename.lower() == "cta_6sec.mp4":
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
            f"Need at least "
            f"{NUMBER_OF_CLIPS} normal footage clips. "
            f"Found {len(all_clips)}."
        )

    # --------------------------------------------------------
    # RANDOM 4 CLIPS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    voice_duration = get_media_duration(
        voice_path
    )

    print(
        f"\nVoice duration: "
        f"{voice_duration:.2f}s",
        flush=True
    )

    # We need the voice to fit inside the main section.
    if voice_duration > main_duration:

        print(
            "\nWARNING:",
            flush=True
        )

        print(
            f"Voice is {voice_duration:.2f}s "
            f"but main section is "
            f"{main_duration:.2f}s.",
            flush=True
        )

        print(
            "The main video will use the requested "
            "random total duration.",
            flush=True
        )

    # --------------------------------------------------------
    # CREATE 6-SECOND CTA
    # --------------------------------------------------------

    cta_6sec = create_cta_6sec()

    # --------------------------------------------------------
    # MAIN CLIP DURATION
    # --------------------------------------------------------

    clip_duration = (
        main_duration
        / NUMBER_OF_CLIPS
    )

    print(
        f"\nEach of 4 random clips: "
        f"{clip_duration:.3f}s",
        flush=True
    )

    # --------------------------------------------------------
    # TEMP FILES
    # --------------------------------------------------------

    temp_main = os.path.join(
        OUTPUT_DIR,
        "temp_main.mp4"
    )

    temp_4k = os.path.join(
        OUTPUT_DIR,
        "temp_main_4k.mp4"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    for temp_file in [
        temp_main,
        temp_4k,
        output_path
    ]:

        if os.path.exists(temp_file):

            os.remove(
                temp_file
            )

    # ========================================================
    # STEP 1
    # CREATE RANDOM 4-CLIP MAIN VIDEO
    # ========================================================

    filter_parts = []

    for index in range(
        NUMBER_OF_CLIPS
    ):

        filter_parts.append(
            (
                f"[{index}:v]"
                f"trim=duration={clip_duration:.4f},"
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
            f"concat=n={NUMBER_OF_CLIPS}:v=1:a=0,"
            f"trim=duration={main_duration:.4f},"
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
        "\nStep 1/3: Creating random 4-clip main sequence...",
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
            "Main clip rendering failed."
        )

    if not os.path.exists(
        temp_main
    ):

        raise RuntimeError(
            "Temporary main video was not created."
        )

    # ========================================================
    # STEP 2
    # UPSCALE MAIN VIDEO TO 4K
    # ========================================================

    opening_text = (
        f"I MADE\\: ${short_amount} EVERY DAY"
    )

    main_filter = (
        "[0:v]"
        "scale=2160:3840:"
        "flags=lanczos,"
        "unsharp=5:5:0.45:5:5:0,"
        "eq=contrast=1.02:saturation=1.03,"

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
        "enable='between(t,0,5)'"

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
        "\nStep 2/3: Upscaling main video to 4K...",
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
    # STEP 3
    # APPEND FIXED 6-SECOND CTA
    # ========================================================

    print(
        "\nStep 3/3: Appending fixed 6-second CTA...",
        flush=True
    )

    final_command = [
        "ffmpeg",
        "-y",

        "-i",
        temp_4k,

        "-i",
        cta_6sec,

        "-i",
        voice_path,

        "-filter_complex",

        (
            "[0:v]"
            "setpts=PTS-STARTPTS"
            "[main];"

            "[1:v]"
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
        f"{target_final_duration:.3f}",

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

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "Final video was not created."
        )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    final_file_duration = get_media_duration(
        output_path
    )

    file_size_mb = (
        os.path.getsize(
            output_path
        )
        / (1024 * 1024)
    )

    print(
        "\n===== FINAL VIDEO =====",
        flush=True
    )

    print(
        f"Final duration: "
        f"{final_file_duration:.2f}s",
        flush=True
    )

    print(
        f"Target duration: "
        f"{target_final_duration:.2f}s",
        flush=True
    )

    print(
        f"Main footage: "
        f"{main_duration:.2f}s",
        flush=True
    )

    print(
        "CTA: 6.00s",
        flush=True
    )

    print(
        "Random clips: 4",
        flush=True
    )

    print(
        "Red arrow: REMOVED",
        flush=True
    )

    print(
        "CTA position: FINAL 6 SECONDS",
        flush=True
    )

    print(
        "CTA instruction: "
        "Go to channel description → "
        "click Bot Activation button",
        flush=True
    )

    print(
        f"Random test amount: ${short_amount}",
        flush=True
    )

    print(
        f"File size: {file_size_mb:.2f} MB",
        flush=True
    )

    print(
        "Resolution: 2160x3840",
        flush=True
    )

    print(
        "========================",
        flush=True
    )

    # --------------------------------------------------------
    # CLEANUP
    # --------------------------------------------------------

    for temp_file in [
        temp_main,
        temp_4k,
        cta_6sec
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
        "\n===== 4-CLIP + RANDOM 20-25 SEC + 6 SEC CTA SUCCESS =====",
        flush=True
    )

    print(
        f"Final video: {output_path}",
        flush=True
    )

    return output_path
