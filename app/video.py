import os
import random
import shutil
import subprocess
import uuid
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

ASSETS_DIR = "/app/assets"
OUTPUT_DIR = "/app/output"

NUMBER_OF_CLIPS = 4

CLIP_DURATION = 5.0

MAIN_VIDEO_DURATION = 20.0

CTA_DURATION = 5.0

FINAL_VIDEO_DURATION = 25.0

OPENING_TEXT_DURATION = 5.0


# ============================================================
# FIXED CTA FILE
# ============================================================

CTA_SOURCE = os.path.join(
    ASSETS_DIR,
    "activation_cta.mp4"
)


# ============================================================
# RANDOM VIDEO POOL
# ============================================================

RANDOM_VIDEO_FILES = [
    "01_chart_overview.mp4",
    "02_candlestick_chart.mp4",
    "03_chart_zoom_in.mp4",
    "04_price_movement.mp4",
    "05_ai_bot_dashboard.mp4",
    "06_ai_bot_analyzing.mp4",
    "07_ai_pattern_detection.mp4",
    "08_trade_setup.mp4",
    "09_indicator_analysis.mp4",
    "10_dashboard_scroll.mp4",
    "11_market_signal.mp4",
    "12_ai_market_analysis.mp4",
    "13_trading_signal_screen.mp4",
    "14_market_data_analysis.mp4",
    "15_ai_trade_monitoring.mp4",
]


# ============================================================
# HELPERS
# ============================================================

def run_command(
    command,
    description="FFmpeg command"
):
    print(
        f"\nRunning: {description}",
        flush=True
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        print(
            "\n===== COMMAND FAILED =====",
            flush=True
        )

        print(
            " ".join(command),
            flush=True
        )

        print(
            "\nSTDOUT:",
            flush=True
        )

        print(
            result.stdout,
            flush=True
        )

        print(
            "\nSTDERR:",
            flush=True
        )

        print(
            result.stderr,
            flush=True
        )

        raise RuntimeError(
            f"{description} failed."
        )

    return result


# ============================================================
# FFPROBE
# ============================================================

def probe_file(path):

    if not os.path.exists(path):

        raise RuntimeError(
            f"File does not exist: {path}"
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        path
    ]

    result = run_command(
        command,
        f"Checking media: {os.path.basename(path)}"
    )

    try:
        import json

        return json.loads(
            result.stdout
        )

    except Exception as e:

        raise RuntimeError(
            f"Could not parse ffprobe output "
            f"for {path}: {e}"
        )


# ============================================================
# GET VIDEO DURATION
# ============================================================

def get_duration(path):

    data = probe_file(path)

    duration = (
        data
        .get("format", {})
        .get("duration")
    )

    if duration is None:

        raise RuntimeError(
            f"Could not determine duration: "
            f"{path}"
        )

    return float(duration)


# ============================================================
# CHECK VIDEO STREAM
# ============================================================

def has_video_stream(path):

    data = probe_file(path)

    for stream in data.get(
        "streams",
        []
    ):

        if stream.get(
            "codec_type"
        ) == "video":

            return True

    return False


# ============================================================
# CHECK AUDIO STREAM
# ============================================================

def has_audio_stream(path):

    data = probe_file(path)

    for stream in data.get(
        "streams",
        []
    ):

        if stream.get(
            "codec_type"
        ) == "audio":

            return True

    return False


# ============================================================
# VALIDATE INPUT CLIP
# ============================================================

def validate_clip(path):

    if not os.path.exists(path):

        raise RuntimeError(
            f"Missing clip: {path}"
        )

    if not has_video_stream(path):

        raise RuntimeError(
            f"File has no video stream: "
            f"{path}"
        )

    duration = get_duration(path)

    if duration < 0.5:

        raise RuntimeError(
            f"Video is too short: "
            f"{path}"
        )

    return duration


# ============================================================
# VALIDATE VOICE
# ============================================================

def validate_voice(voice_path):

    print(
        "\n===== CHECKING VOICE =====",
        flush=True
    )

    if not os.path.exists(
        voice_path
    ):

        raise RuntimeError(
            f"Voice file does not exist: "
            f"{voice_path}"
        )

    file_size = os.path.getsize(
        voice_path
    )

    if file_size <= 0:

        raise RuntimeError(
            "Voice file is empty."
        )

    print(
        f"Voice file size: "
        f"{file_size / 1024:.2f} KB",
        flush=True
    )

    if not has_audio_stream(
        voice_path
    ):

        raise RuntimeError(
            "CRITICAL: ElevenLabs voice "
            "file contains NO AUDIO STREAM."
        )

    duration = get_duration(
        voice_path
    )

    if duration <= 0:

        raise RuntimeError(
            "Voice duration is zero."
        )

    print(
        f"Voice duration: "
        f"{duration:.2f} seconds",
        flush=True
    )

    print(
        "Audio stream detected: YES",
        flush=True
    )

    return duration


# ============================================================
# CREATE 5 SECOND CTA
# ============================================================

def create_cta_5sec(
    output_path
):

    print(
        "\n===== CTA VIDEO =====",
        flush=True
    )

    if not os.path.exists(
        CTA_SOURCE
    ):

        raise RuntimeError(
            "Missing CTA source video: "
            f"{CTA_SOURCE}"
        )

    validate_clip(
        CTA_SOURCE
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        CTA_SOURCE,

        "-t",
        "5.000",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:"
            "(oh-ih)/2,"
            "setsar=1"
        ),

        "-r",
        "30",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        output_path
    ]

    run_command(
        command,
        "Creating fixed 5-second CTA"
    )

    duration = get_duration(
        output_path
    )

    print(
        f"CTA duration: "
        f"{duration:.3f}s",
        flush=True
    )

    if abs(
        duration - CTA_DURATION
    ) > 0.10:

        raise RuntimeError(
            f"CTA duration is not 5 seconds: "
            f"{duration}"
        )

    return output_path


# ============================================================
# CREATE ONE NORMAL 5 SECOND CLIP
# ============================================================

def prepare_normal_clip(
    source_path,
    output_path
):

    validate_clip(
        source_path
    )

    command = [
        "ffmpeg",
        "-y",

        "-stream_loop",
        "-1",

        "-i",
        source_path,

        "-t",
        f"{CLIP_DURATION:.3f}",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:"
            "(oh-ih)/2,"
            "setsar=1"
        ),

        "-r",
        "30",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        output_path
    ]

    run_command(
        command,
        f"Preparing clip "
        f"{os.path.basename(source_path)}"
    )

    duration = get_duration(
        output_path
    )

    if abs(
        duration - CLIP_DURATION
    ) > 0.10:

        raise RuntimeError(
            f"Prepared clip is not "
            f"5 seconds: {duration}"
        )

    return output_path


# ============================================================
# CREATE MAIN 20 SECOND VIDEO
# ============================================================

def create_main_video(
    prepared_clips,
    output_path
):

    if len(
        prepared_clips
    ) != NUMBER_OF_CLIPS:

        raise RuntimeError(
            "Exactly 4 prepared clips "
            "are required."
        )

    concat_file = (
        output_path
        + ".txt"
    )

    try:

        with open(
            concat_file,
            "w",
            encoding="utf-8"
        ) as f:

            for clip in prepared_clips:

                absolute_path = os.path.abspath(
                    clip
                )

                f.write(
                    "file '"
                    + absolute_path.replace(
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
            concat_file,

            "-t",
            f"{MAIN_VIDEO_DURATION:.3f}",

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-r",
            "30",

            "-an",

            "-movflags",
            "+faststart",

            output_path
        ]

        run_command(
            command,
            "Creating 20-second main video"
        )

    finally:

        if os.path.exists(
            concat_file
        ):

            os.remove(
                concat_file
            )


    duration = get_duration(
        output_path
    )

    print(
        f"Main video duration: "
        f"{duration:.3f}s",
        flush=True
    )

    if abs(
        duration - MAIN_VIDEO_DURATION
    ) > 0.10:

        raise RuntimeError(
            f"Main video is not "
            f"20 seconds: {duration}"
        )

    return output_path


# ============================================================
# ADD TEXT TO FIRST 5 SECONDS
# ============================================================

def add_opening_text(
    input_path,
    output_path,
    short_amount
):

    # Escape characters for FFmpeg drawtext.

    amount_text = (
        f"I MADE: ${short_amount} EVERY DAY"
    )

    safe_amount = (
        amount_text
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )

    safe_link = (
        "LINK IN BIO"
        .replace(":", "\\:")
        .replace("'", "\\'")
    )

    filter_text = (
        "drawtext="
        "fontcolor=white:"
        "fontsize=62:"
        "fontweight=bold:"
        "borderw=4:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=180:"
        f"text='{safe_amount}':"
        f"enable='between(t,0,5)'"
        ","
        "drawtext="
        "fontcolor=white:"
        "fontsize=55:"
        "fontweight=bold:"
        "borderw=4:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=270:"
        f"text='{safe_link}':"
        f"enable='between(t,0,5)'"
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        input_path,

        "-vf",
        filter_text,

        "-t",
        f"{MAIN_VIDEO_DURATION:.3f}",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-an",

        "-movflags",
        "+faststart",

        output_path
    ]

    run_command(
        command,
        "Adding opening text"
    )

    duration = get_duration(
        output_path
    )

    if abs(
        duration - MAIN_VIDEO_DURATION
    ) > 0.10:

        raise RuntimeError(
            "Opening-text video is not "
            "20 seconds."
        )

    return output_path


# ============================================================
# JOIN MAIN + CTA
# ============================================================

def join_main_and_cta(
    main_path,
    cta_path,
    output_path
):

    concat_file = (
        output_path
        + ".txt"
    )

    try:

        with open(
            concat_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "file '"
                + os.path.abspath(
                    main_path
                )
                + "'\n"
            )

            f.write(
                "file '"
                + os.path.abspath(
                    cta_path
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
            concat_file,

            "-t",
            f"{FINAL_VIDEO_DURATION:.3f}",

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-r",
            "30",

            "-an",

            "-movflags",
            "+faststart",

            output_path
        ]

        run_command(
            command,
            "Joining main video + CTA"
        )

    finally:

        if os.path.exists(
            concat_file
        ):

            os.remove(
                concat_file
            )


    duration = get_duration(
        output_path
    )

    print(
        f"Video + CTA duration: "
        f"{duration:.3f}s",
        flush=True
    )

    if abs(
        duration - FINAL_VIDEO_DURATION
    ) > 0.10:

        raise RuntimeError(
            f"Video is not exactly "
            f"25 seconds: {duration}"
        )

    return output_path


# ============================================================
# MUX ELEVENLABS AUDIO
# ============================================================

def mux_audio(
    video_path,
    voice_path,
    output_path
):

    print(
        "\n===== ADDING ELEVENLABS AUDIO =====",
        flush=True
    )

    # --------------------------------------------------------
    # Validate voice before attempting mux.
    # --------------------------------------------------------

    voice_duration = validate_voice(
        voice_path
    )

    print(
        f"Voice duration before mux: "
        f"{voice_duration:.3f}s",
        flush=True
    )

    # --------------------------------------------------------
    # The voice must be allowed to continue up to the end
    # of the 25-second Short.
    #
    # If ElevenLabs voice is slightly shorter than 25 sec,
    # the remaining video is kept silent.
    #
    # If the voice is longer than 25 sec, it is trimmed at
    # exactly 25 sec so the final Short stays 25 sec.
    # --------------------------------------------------------

    command = [
        "ffmpeg",
        "-y",

        "-i",
        video_path,

        "-i",
        voice_path,

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-t",
        f"{FINAL_VIDEO_DURATION:.3f}",

        "-c:v",
        "copy",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "44100",

        "-ac",
        "2",

        "-af",
        (
            "apad=pad_dur=25,"
            "atrim=duration=25"
        ),

        "-movflags",
        "+faststart",

        "-shortest",

        output_path
    ]

    run_command(
        command,
        "Muxing ElevenLabs audio"
    )

    return output_path


# ============================================================
# FINAL VALIDATION
# ============================================================

def validate_final_video(
    output_path
):

    print(
        "\n===== FINAL VIDEO VALIDATION =====",
        flush=True
    )

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "Final video was not created."
        )

    file_size = os.path.getsize(
        output_path
    )

    if file_size <= 0:

        raise RuntimeError(
            "Final video is empty."
        )

    print(
        f"Final file size: "
        f"{file_size / (1024 * 1024):.2f} MB",
        flush=True
    )


    # --------------------------------------------------------
    # VIDEO STREAM
    # --------------------------------------------------------

    if not has_video_stream(
        output_path
    ):

        raise RuntimeError(
            "FINAL VIDEO HAS NO VIDEO STREAM."
        )


    # --------------------------------------------------------
    # AUDIO STREAM
    # --------------------------------------------------------

    if not has_audio_stream(
        output_path
    ):

        raise RuntimeError(
            "FINAL VIDEO HAS NO AUDIO STREAM."
        )


    # --------------------------------------------------------
    # DURATION
    # --------------------------------------------------------

    duration = get_duration(
        output_path
    )

    print(
        f"Final duration: "
        f"{duration:.3f}s",
        flush=True
    )

    print(
        "Video stream: YES",
        flush=True
    )

    print(
        "Audio stream: YES",
        flush=True
    )


    if abs(
        duration - FINAL_VIDEO_DURATION
    ) > 0.10:

        raise RuntimeError(
            f"FINAL VIDEO IS NOT "
            f"25 SECONDS: {duration}"
        )


    print(
        "\nFINAL VIDEO VALIDATION PASSED",
        flush=True
    )

    return True


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_video(
    script="",
    voice_path=None,
    short_amount=1000,
    output_filename="short.mp4"
):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Unique temporary working directory
    # --------------------------------------------------------

    job_id = uuid.uuid4().hex[:12]

    temp_dir = os.path.join(
        OUTPUT_DIR,
        f"video_job_{job_id}"
    )

    os.makedirs(
        temp_dir,
        exist_ok=True
    )


    final_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )


    try:

        print(
            "\n"
            "==================================================",
            flush=True
        )

        print(
            "GENERATING 25-SECOND SHORT",
            flush=True
        )

        print(
            "==================================================",
            flush=True
        )


        # ====================================================
        # VALIDATE CTA
        # ====================================================

        if not os.path.exists(
            CTA_SOURCE
        ):

            raise RuntimeError(
                "activation_cta.mp4 is missing "
                f"from {ASSETS_DIR}"
            )


        # ====================================================
        # VALIDATE VOICE
        # ====================================================

        if not voice_path:

            raise RuntimeError(
                "voice_path was not provided."
            )

        validate_voice(
            voice_path
        )


        # ====================================================
        # SELECT 4 RANDOM CLIPS
        # ====================================================

        available_clips = []

        for filename in RANDOM_VIDEO_FILES:

            path = os.path.join(
                ASSETS_DIR,
                filename
            )

            if os.path.exists(
                path
            ):

                available_clips.append(
                    path
                )

            else:

                print(
                    f"WARNING: Missing clip "
                    f"{filename}",
                    flush=True
                )


        if len(
            available_clips
        ) < NUMBER_OF_CLIPS:

            raise RuntimeError(
                "Not enough normal clips. "
                f"Found {len(available_clips)}, "
                f"need {NUMBER_OF_CLIPS}."
            )


        selected_clips = random.sample(
            available_clips,
            NUMBER_OF_CLIPS
        )

        random.shuffle(
            selected_clips
        )


        print(
            "\nSelected random clips:",
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


        # ====================================================
        # PREPARE FOUR 5-SECOND CLIPS
        # ====================================================

        prepared_clips = []

        for index, source in enumerate(
            selected_clips,
            start=1
        ):

            prepared_path = os.path.join(
                temp_dir,
                f"clip_{index}.mp4"
            )

            prepare_normal_clip(
                source,
                prepared_path
            )

            prepared_clips.append(
                prepared_path
            )


        # ====================================================
        # CREATE 20 SECOND MAIN
        # ====================================================

        main_raw = os.path.join(
            temp_dir,
            "main_raw.mp4"
        )

        create_main_video(
            prepared_clips,
            main_raw
        )


        # ====================================================
        # ADD OPENING TEXT
        # ====================================================

        main_with_text = os.path.join(
            temp_dir,
            "main_with_text.mp4"
        )

        add_opening_text(
            main_raw,
            main_with_text,
            short_amount
        )


        # ====================================================
        # CREATE FIXED 5 SECOND CTA
        # ====================================================

        cta_path = os.path.join(
            temp_dir,
            "cta_5sec.mp4"
        )

        create_cta_5sec(
            cta_path
        )


        # ====================================================
        # JOIN 20 SEC + 5 SEC
        # ====================================================

        silent_25sec = os.path.join(
            temp_dir,
            "silent_25sec.mp4"
        )

        join_main_and_cta(
            main_with_text,
            cta_path,
            silent_25sec
        )


        # ====================================================
        # ADD ELEVENLABS AUDIO
        # ====================================================

        temp_final = os.path.join(
            temp_dir,
            "final_with_audio.mp4"
        )

        mux_audio(
            silent_25sec,
            voice_path,
            temp_final
        )


        # ====================================================
        # FINAL VALIDATION
        # ====================================================

        validate_final_video(
            temp_final
        )


        # ====================================================
        # MOVE TO FINAL OUTPUT
        # ====================================================

        if os.path.exists(
            final_path
        ):

            os.remove(
                final_path
            )


        shutil.copy2(
            temp_final,
            final_path
        )


        # Validate the actual final output
        # after copying.

        validate_final_video(
            final_path
        )


        print(
            "\n"
            "==================================================",
            flush=True
        )

        print(
            "VIDEO GENERATION SUCCESS",
            flush=True
        )

        print(
            f"Output: {final_path}",
            flush=True
        )

        print(
            "Duration: 25 seconds",
            flush=True
        )

        print(
            "Audio: YES",
            flush=True
        )

        print(
            "CTA: 5 seconds",
            flush=True
        )

        print(
            "==================================================",
            flush=True
        )


        return final_path


    finally:

        # ====================================================
        # CLEANUP TEMP FILES
        # ====================================================

        try:

            if os.path.exists(
                temp_dir
            ):

                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True
                )

        except Exception as e:

            print(
                f"Cleanup warning: {e}",
                flush=True
            )
