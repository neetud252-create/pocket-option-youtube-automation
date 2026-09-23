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

# Exactly 4 random normal clips
NUMBER_OF_CLIPS = 4

# ============================================================
# FIXED SHORT FORMAT
# ============================================================

# Normal random footage = exactly 20 seconds
MAIN_VIDEO_DURATION = 20.0

# CTA = exactly 5 seconds
CTA_DURATION = 5.0

# Final Short = exactly 25 seconds
FINAL_VIDEO_DURATION = 25.0

# 4 clips × 5 seconds = 20 seconds
CLIP_DURATION = 5.0

# Opening text remains for first 5 seconds
OPENING_TEXT_DURATION = 5.0


# ============================================================
# MEDIA DURATION
# ============================================================

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
            f"Could not read media duration: "
            f"{file_path}"
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

def validate_video(
    file_path: str
):

    if not os.path.exists(
        file_path
    ):

        raise FileNotFoundError(
            f"Video not found: "
            f"{file_path}"
        )

    duration = get_media_duration(
        file_path
    )

    if duration <= 0:

        raise RuntimeError(
            f"Invalid video: "
            f"{file_path}"
        )

    print(
        f"Validated: "
        f"{os.path.basename(file_path)} "
        f"({duration:.2f}s)",
        flush=True
    )

    return duration


# ============================================================
# RUN FFMPEG
# ============================================================

def run_ffmpeg(
    command,
    error_title
):

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            f"\n===== {error_title} =====",
            flush=True
        )

        print(
            result.stderr[-20000:],
            flush=True
        )

        raise RuntimeError(
            error_title
        )

    return result


# ============================================================
# CREATE EXACT 5 SECOND CTA
# ============================================================

def create_cta_5sec():

    cta_output = os.path.join(
        OUTPUT_DIR,
        "cta_5sec.mp4"
    )

    if os.path.exists(
        cta_output
    ):

        os.remove(
            cta_output
        )

    command = [
        "ffmpeg",
        "-y",

        # Loop CTA so it is guaranteed
        # to have enough frames
        "-stream_loop",
        "-1",

        "-i",
        CTA_FILE,

        # EXACTLY 5 SECONDS
        "-t",
        "5.000",

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

        "-r",
        "30",

        "-movflags",
        "+faststart",

        cta_output
    ]

    print(
        "\nCreating EXACT 5-second CTA...",
        flush=True
    )

    run_ffmpeg(
        command,
        "CTA FFMPEG ERROR"
    )

    if not os.path.exists(
        cta_output
    ):

        raise RuntimeError(
            "CTA file was not created."
        )

    duration = get_media_duration(
        cta_output
    )

    print(
        f"CTA created: "
        f"{duration:.2f}s",
        flush=True
    )

    # Strict CTA validation
    if abs(
        duration - CTA_DURATION
    ) > 0.10:

        raise RuntimeError(
            f"CTA is not exactly "
            f"{CTA_DURATION:.2f}s. "
            f"Actual: {duration:.3f}s"
        )

    return cta_output


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
    # CHECK CTA
    # ========================================================

    if not os.path.exists(
        CTA_FILE
    ):

        raise FileNotFoundError(
            f"CTA video not found: "
            f"{CTA_FILE}"
        )

    original_cta_duration = (
        get_media_duration(
            CTA_FILE
        )
    )

    print(
        "\n===== CTA INFORMATION =====",
        flush=True
    )

    print(
        "File: activation_cta.mp4",
        flush=True
    )

    print(
        f"Original duration: "
        f"{original_cta_duration:.2f}s",
        flush=True
    )

    print(
        "Final CTA duration: 5.00s",
        flush=True
    )

    print(
        "CTA: Channel description → "
        "Bot Activation button",
        flush=True
    )

    print(
        "===========================",
        flush=True
    )


    # ========================================================
    # FIXED VIDEO DURATION
    # ========================================================

    final_duration = FINAL_VIDEO_DURATION

    main_duration = MAIN_VIDEO_DURATION

    clip_duration = CLIP_DURATION

    print(
        "\n===== FIXED SHORT FORMAT =====",
        flush=True
    )

    print(
        f"Normal footage: "
        f"{main_duration:.3f}s",
        flush=True
    )

    print(
        f"CTA: "
        f"{CTA_DURATION:.3f}s",
        flush=True
    )

    print(
        f"Final Short: "
        f"{final_duration:.3f}s",
        flush=True
    )

    print(
        f"Each random clip: "
        f"{clip_duration:.3f}s",
        flush=True
    )

    print(
        "Formula: "
        "4 × 5s clips + 5s CTA = 25s",
        flush=True
    )

    print(
        "================================",
        flush=True
    )


    # ========================================================
    # FIND NORMAL FOOTAGE
    # ========================================================

    all_clips = []

    for filename in os.listdir(
        FOOTAGE_DIR
    ):

        if not filename.lower().endswith(
            ".mp4"
        ):

            continue

        # Never include CTA in random clips
        if filename.lower() in [
            "activation_cta.mp4",
            "cta_5sec.mp4",
            "cta_6sec.mp4"
        ]:

            continue

        all_clips.append(
            os.path.join(
                FOOTAGE_DIR,
                filename
            )
        )

    all_clips.sort()

    print(
        f"\nFound "
        f"{len(all_clips)} normal MP4 clips.",
        flush=True
    )

    if len(all_clips) < NUMBER_OF_CLIPS:

        raise RuntimeError(
            f"Need at least "
            f"{NUMBER_OF_CLIPS} normal clips. "
            f"Found {len(all_clips)}."
        )


    # ========================================================
    # RANDOM 4 CLIPS
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
    # VOICE INFORMATION
    # ========================================================

    voice_duration = (
        get_media_duration(
            voice_path
        )
    )

    print(
        f"\nVoice duration: "
        f"{voice_duration:.2f}s",
        flush=True
    )

    print(
        "IMPORTANT: Video duration is fixed "
        "at 25 seconds.",
        flush=True
    )

    print(
        "Voice duration will NOT control "
        "the video duration.",
        flush=True
    )


    # ========================================================
    # CREATE EXACT 5 SECOND CTA
    # ========================================================

    cta_5sec = create_cta_5sec()


    # ========================================================
    # TEMP FILES
    # ========================================================

    temp_main = os.path.join(
        OUTPUT_DIR,
        "temp_main.mp4"
    )

    temp_4k = os.path.join(
        OUTPUT_DIR,
        "temp_main_4k.mp4"
    )

    concat_list = os.path.join(
        OUTPUT_DIR,
        "concat_list.txt"
    )

    temp_joined = os.path.join(
        OUTPUT_DIR,
        "temp_joined.mp4"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )


    # Remove old temporary files

    for file_path in [
        temp_main,
        temp_4k,
        concat_list,
        temp_joined,
        output_path
    ]:

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )


    # ========================================================
    # STEP 1
    # CREATE EXACT 20 SECOND MAIN VIDEO
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
                f"fps=30,"
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
            f"setpts=PTS-STARTPTS,"
            f"fps=30,"
            f"format=yuv420p"
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

        # EXACTLY 20 SECONDS
        "-t",
        "20.000",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-movflags",
        "+faststart",

        temp_main
    ])


    print(
        "\nStep 1/4: "
        "Creating EXACT 20-second random footage...",
        flush=True
    )

    run_ffmpeg(
        command,
        "STEP 1 FFMPEG ERROR"
    )


    # ========================================================
    # VALIDATE MAIN VIDEO
    # ========================================================

    main_file_duration = (
        get_media_duration(
            temp_main
        )
    )

    print(
        f"Main video created: "
        f"{main_file_duration:.3f}s",
        flush=True
    )

    if abs(
        main_file_duration - 20.0
    ) > 0.10:

        raise RuntimeError(
            f"Main footage is not "
            f"20 seconds. "
            f"Actual: {main_file_duration:.3f}s"
        )


    # ========================================================
    # STEP 2
    # UPSCALE TO 4K
    # ========================================================

    # KEEP TESTING TEXT EXACTLY AS REQUESTED

    opening_text = (
        f"I MADE\\: ${short_amount} EVERY DAY"
    )


    main_filter = (
        "[0:v]"
        "scale=2160:3840:"
        "flags=lanczos,"
        "unsharp=5:5:0.45:5:5:0,"
        "eq=contrast=1.02:saturation=1.03,"

        # ----------------------------------------------------
        # I MADE: $XXXX EVERY DAY
        # ----------------------------------------------------

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
        # LINK IN BIO
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

        "fps=30,"
        "format=yuv420p"
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

        "-an",

        # Keep exact 20 seconds
        "-t",
        "20.000",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-movflags",
        "+faststart",

        temp_4k
    ]


    print(
        "\nStep 2/4: "
        "Upscaling 20-second main video to 4K...",
        flush=True
    )

    run_ffmpeg(
        command,
        "STEP 2 FFMPEG ERROR"
    )


    # ========================================================
    # VALIDATE 4K MAIN VIDEO
    # ========================================================

    main_4k_duration = (
        get_media_duration(
            temp_4k
        )
    )

    print(
        f"4K main video duration: "
        f"{main_4k_duration:.3f}s",
        flush=True
    )

    if abs(
        main_4k_duration - 20.0
    ) > 0.10:

        raise RuntimeError(
            f"4K main video is not "
            f"20 seconds. "
            f"Actual: {main_4k_duration:.3f}s"
        )


    # ========================================================
    # STEP 3
    # JOIN EXACT 20 SEC MAIN + EXACT 5 SEC CTA
    # ========================================================

    print(
        "\nStep 3/4: "
        "Joining EXACT 20-second main + "
        "EXACT 5-second CTA...",
        flush=True
    )


    # --------------------------------------------------------
    # Verify CTA one more time
    # --------------------------------------------------------

    cta_duration = (
        get_media_duration(
            cta_5sec
        )
    )

    print(
        f"CTA duration before join: "
        f"{cta_duration:.3f}s",
        flush=True
    )

    if abs(
        cta_duration - 5.0
    ) > 0.10:

        raise RuntimeError(
            f"CTA is not 5 seconds "
            f"before joining. "
            f"Actual: {cta_duration:.3f}s"
        )


    # --------------------------------------------------------
    # FFmpeg concat demuxer
    # --------------------------------------------------------

    with open(
        concat_list,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "file '"
            + temp_4k.replace(
                "'",
                "'\\''"
            )
            + "'\n"
        )

        file.write(
            "file '"
            + cta_5sec.replace(
                "'",
                "'\\''"
            )
            + "'\n"
        )


    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        concat_list,

        "-c",
        "copy",

        "-movflags",
        "+faststart",

        temp_joined
    ]


    run_ffmpeg(
        command,
        "STEP 3 CONCAT ERROR"
    )


    # ========================================================
    # VALIDATE JOINED VIDEO
    # ========================================================

    joined_duration = (
        get_media_duration(
            temp_joined
        )
    )

    print(
        f"Joined video duration: "
        f"{joined_duration:.3f}s",
        flush=True
    )

    if abs(
        joined_duration - 25.0
    ) > 0.15:

        raise RuntimeError(
            f"Joined video is not "
            f"25 seconds. "
            f"Actual: {joined_duration:.3f}s"
        )


    # ========================================================
    # STEP 4
    # ADD ELEVENLABS VOICE
    # ========================================================

    print(
        "\nStep 4/4: "
        "Adding ElevenLabs voice WITHOUT "
        "cutting the video...",
        flush=True
    )


    command = [
        "ffmpeg",
        "-y",

        "-i",
        temp_joined,

        "-i",
        voice_path,

        # ----------------------------------------------------
        # VIDEO
        # ----------------------------------------------------

        "-map",
        "0:v:0",

        # ----------------------------------------------------
        # AUDIO
        # ----------------------------------------------------

        "-map",
        "1:a:0",

        # ----------------------------------------------------
        # EXACT FINAL DURATION
        # ----------------------------------------------------

        "-t",
        "25.000",

        # ----------------------------------------------------
        # VIDEO COPY
        # ----------------------------------------------------

        "-c:v",
        "copy",

        # ----------------------------------------------------
        # AUDIO
        # ----------------------------------------------------

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        # IMPORTANT:
        # NO -shortest
        #
        # This prevents ElevenLabs audio from
        # cutting the 5-second CTA off.
        #
        # The video stays exactly 25 seconds.
        # If audio finishes earlier, remaining
        # video time will simply have silence.
        #
        # If audio is longer, it is limited
        # to the 25-second video duration.

        "-movflags",
        "+faststart",

        output_path
    ]


    run_ffmpeg(
        command,
        "STEP 4 AUDIO ERROR"
    )


    # ========================================================
    # FINAL VALIDATION
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
        / (1024 * 1024)
    )


    print(
        "\n===== FINAL VIDEO VALIDATION =====",
        flush=True
    )

    print(
        f"Final duration: "
        f"{final_file_duration:.3f}s",
        flush=True
    )

    print(
        "Expected duration: 25.000s",
        flush=True
    )

    print(
        "Normal footage: 20.000s",
        flush=True
    )

    print(
        "CTA: 5.000s",
        flush=True
    )

    print(
        "Random clips: 4",
        flush=True
    )

    print(
        "Each random clip: 5.000s",
        flush=True
    )

    print(
        "CTA: FULL 5 SECONDS",
        flush=True
    )

    print(
        "Red arrow: REMOVED",
        flush=True
    )

    print(
        "I MADE text: KEPT",
        flush=True
    )

    print(
        "LINK IN BIO: KEPT",
        flush=True
    )

    print(
        "Resolution: 2160x3840",
        flush=True
    )

    print(
        f"Final size: "
        f"{file_size_mb:.2f} MB",
        flush=True
    )

    print(
        "=================================",
        flush=True
    )


    # ========================================================
    # STRICT FINAL DURATION CHECK
    # ========================================================

    if abs(
        final_file_duration - 25.0
    ) > 0.15:

        raise RuntimeError(
            f"FINAL VIDEO DURATION ERROR: "
            f"Expected 25 seconds but got "
            f"{final_file_duration:.3f}s"
        )


    # ========================================================
    # CLEANUP
    # ========================================================

    for file_path in [
        temp_main,
        temp_4k,
        concat_list,
        temp_joined,
        cta_5sec
    ]:

        try:

            if os.path.exists(
                file_path
            ):

                os.remove(
                    file_path
                )

        except Exception:

            pass


    # ========================================================
    # SUCCESS
    # ========================================================

    print(
        "\n===== VIDEO GENERATION SUCCESS =====",
        flush=True
    )

    print(
        "25-second Short created successfully.",
        flush=True
    )

    print(
        "20 seconds random footage + "
        "5 seconds FULL CTA.",
        flush=True
    )

    print(
        f"Output: {output_path}",
        flush=True
    )

    print(
        "====================================",
        flush=True
    )


    return output_path
