import json
import os
import random
import shutil
import subprocess
import tempfile
import uuid


# ============================================================
# CONFIG
# ============================================================

ASSETS_DIR = "/app/assets/footage"
OUTPUT_DIR = "/app/output"
BACKGROUND_MUSIC = "/app/assets/background_music.mp3"
BACKGROUND_MUSIC_VOLUME = 0.10

NUMBER_OF_CLIPS = 4
CTA_DURATION = 5.0
MIN_VIDEO_DURATION = 20.0
MAX_VIDEO_DURATION = 26.0
FPS = 30
OPENING_TEXT_DURATION = 5.0

CTA_SOURCE = os.path.join(
    ASSETS_DIR,
    "activation_cta.mp4",
)

OVERLAY_FONT_FILE = (
    "/usr/share/fonts/truetype/dejavu/"
    "DejaVuSans-Bold.ttf"
)

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
# PROCESS / MEDIA HELPERS
# ============================================================

def run_command(
    command,
    description="FFmpeg command",
    timeout=600,
):
    print(
        f"\nRunning: {description}",
        flush=True,
    )

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{description} timed out after {timeout} seconds."
        ) from exc

    if result.returncode != 0:
        print(
            "\n===== COMMAND FAILED =====",
            flush=True,
        )
        print(
            " ".join(command),
            flush=True,
        )
        print(
            "\nSTDERR:",
            flush=True,
        )
        print(
            result.stderr[-8000:],
            flush=True,
        )
        raise RuntimeError(
            f"{description} failed."
        )

    return result


def probe_file(path):
    if not os.path.exists(path):
        raise RuntimeError(
            f"File does not exist: {path}"
        )

    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            path,
        ],
        f"Checking media: {os.path.basename(path)}",
        timeout=60,
    )

    try:
        return json.loads(
            result.stdout
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not parse ffprobe output for {path}: {exc}"
        ) from exc


def get_duration(path):
    data = probe_file(path)
    duration = data.get(
        "format",
        {},
    ).get(
        "duration"
    )

    if duration is None:
        raise RuntimeError(
            f"Could not determine duration: {path}"
        )

    return float(
        duration
    )


def has_stream(
    path,
    stream_type,
):
    data = probe_file(path)

    return any(
        stream.get("codec_type") == stream_type
        for stream in data.get("streams", [])
    )


def validate_clip(path):
    if not os.path.exists(path):
        raise RuntimeError(
            f"Missing clip: {path}"
        )

    if not has_stream(
        path,
        "video",
    ):
        raise RuntimeError(
            f"File has no video stream: {path}"
        )

    duration = get_duration(
        path
    )

    if duration < 0.5:
        raise RuntimeError(
            f"Video is too short: {path}"
        )

    return duration


def validate_voice(voice_path):
    if (
        not voice_path
        or not os.path.exists(
            voice_path
        )
    ):
        raise RuntimeError(
            f"Voice file does not exist: {voice_path}"
        )

    if os.path.getsize(
        voice_path
    ) <= 0:
        raise RuntimeError(
            "Voice file is empty."
        )

    if not has_stream(
        voice_path,
        "audio",
    ):
        raise RuntimeError(
            "Voice file contains no audio stream."
        )

    duration = get_duration(
        voice_path
    )

    if duration <= 0:
        raise RuntimeError(
            "Voice duration is zero."
        )

    print(
        f"Voice validated: {duration:.3f} seconds",
        flush=True,
    )

    return duration


def validate_final_video(output_path, expected_duration=25.0):
    if not os.path.exists(
        output_path
    ):
        raise RuntimeError(
            "Final video was not created."
        )

    if os.path.getsize(
        output_path
    ) <= 0:
        raise RuntimeError(
            "Final video is empty."
        )

    if not has_stream(
        output_path,
        "video",
    ):
        raise RuntimeError(
            "FINAL VIDEO HAS NO VIDEO STREAM."
        )

    if not has_stream(
        output_path,
        "audio",
    ):
        raise RuntimeError(
            "FINAL VIDEO HAS NO AUDIO STREAM."
        )

    duration = get_duration(
        output_path
    )

    if abs(
        duration - expected_duration
    ) > 0.20:
        raise RuntimeError(
            f"FINAL VIDEO DOES NOT MATCH {expected_duration:.3f}s: "
            f"{duration:.3f}"
        )

    print(
        "FINAL VIDEO VALIDATION PASSED | "
        f"duration={duration:.3f}s | "
        f"size={os.path.getsize(output_path)/(1024*1024):.2f}MB",
        flush=True,
    )

    return True


def escape_drawtext(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def opening_overlay(short_amount):
    amount_text = escape_drawtext(
        f"I MADE: ${short_amount} EVERY DAY"
    )
    link_text = escape_drawtext("LINK IN BIO")
    font_file = escape_drawtext(OVERLAY_FONT_FILE)

    return (
        "[joined]"
        "drawtext="
        f"fontfile='{font_file}':"
        f"text='{amount_text}':"
        "fontcolor=0x7CFC00:"
        "fontsize=54:"
        "borderw=5:"
        "bordercolor=black:"
        "shadowcolor=black@0.85:"
        "shadowx=2:"
        "shadowy=2:"
        "x=(w-text_w)/2:"
        "y=125:"
        "enable='between(t,0,5)',"
        "drawtext="
        f"fontfile='{font_file}':"
        f"text='{link_text}':"
        "fontcolor=0xFFF200:"
        "fontsize=58:"
        "borderw=5:"
        "bordercolor=black:"
        "shadowcolor=black@0.85:"
        "shadowx=2:"
        "shadowy=2:"
        "x=(w-text_w)/2:"
        "y=195:"
        "enable='between(t,0,5)'"
        "[outv]"
    )


# ============================================================
# VIDEO BUILD
# ============================================================

def select_random_clips():
    available = [
        os.path.join(
            ASSETS_DIR,
            filename,
        )
        for filename in RANDOM_VIDEO_FILES
        if os.path.exists(
            os.path.join(
                ASSETS_DIR,
                filename,
            )
        )
    ]

    if len(available) < NUMBER_OF_CLIPS:
        raise RuntimeError(
            f"Not enough normal clips. Found {len(available)}, "
            f"need {NUMBER_OF_CLIPS}. "
            f"Expected directory: {ASSETS_DIR}"
        )

    selected = random.sample(
        available,
        NUMBER_OF_CLIPS,
    )

    random.shuffle(
        selected
    )

    print(
        "\nSelected random clips:",
        flush=True,
    )

    for index, clip in enumerate(
        selected,
        start=1,
    ):
        print(
            f"{index}. {os.path.basename(clip)}",
            flush=True,
        )

    return selected


def quality_filter(
    input_index,
    output_label,
    trim_expression,
):
    return (
        f"[{input_index}:v]"
        f"{trim_expression},"
        "setpts=PTS-STARTPTS,"
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease:"
        "flags=lanczos,"
        "pad=1080:1920:"
        "(ow-iw)/2:(oh-ih)/2,"
        "setsar=1,"
        "fps=30,"
        "unsharp=5:5:0.50:5:5:0.0,"
        "eq=contrast=1.03:saturation=1.04,"
        "format=yuv420p"
        f"[{output_label}]"
    )


def build_silent_video(
    selected_clips,
    short_amount,
    output_path,
    final_seconds=25.0,
    script="",
):
    if not os.path.exists(
        CTA_SOURCE
    ):
        raise RuntimeError(
            f"Missing fixed CTA video: {CTA_SOURCE}"
        )

    validate_clip(
        CTA_SOURCE
    )

    if not os.path.exists(
        OVERLAY_FONT_FILE
    ):
        raise RuntimeError(
            f"Overlay font is missing: {OVERLAY_FONT_FILE}"
        )

    main_frames = round((final_seconds - CTA_DURATION) * FPS)
    clip_frames = [main_frames // NUMBER_OF_CLIPS + (i < main_frames % NUMBER_OF_CLIPS)
                   for i in range(NUMBER_OF_CLIPS)]
    input_args = []
    filters = []

    for index, clip in enumerate(
        selected_clips
    ):
        clip_duration = clip_frames[index] / FPS
        duration = validate_clip(
            clip
        )

        max_start = max(
            0.0,
            duration - clip_duration,
        )

        start = (
            random.uniform(
                0.0,
                max_start,
            )
            if max_start > 0.20
            else 0.0
        )

        input_args.extend(
            [
                "-stream_loop",
                "-1",
                "-i",
                clip,
            ]
        )

        filters.append(
            quality_filter(
                index,
                f"v{index}",
                (
                    f"trim=start={start:.3f},setpts=PTS-STARTPTS,fps=30,"
                    f"trim=end_frame={clip_frames[index]}"
                ),
            )
        )

    # The fixed CTA is always clip 5.
    cta_input_index = NUMBER_OF_CLIPS

    input_args.extend(
        [
            "-stream_loop",
            "-1",
            "-i",
            CTA_SOURCE,
        ]
    )

    filters.append(
        quality_filter(
            cta_input_index,
            "vcta",
            "fps=30,trim=end_frame=150",
        )
    )

    concat_inputs = "".join(
        f"[v{index}]"
        for index in range(
            NUMBER_OF_CLIPS
        )
    ) + "[vcta]"

    filters.append(
        f"{concat_inputs}"
        f"concat=n={NUMBER_OF_CLIPS + 1}:"
        "v=1:a=0[joined]"
    )

    filters.append(opening_overlay(short_amount))

    command = [
        "ffmpeg",
        "-y",
        *input_args,
        "-filter_complex",
        ";".join(
            filters
        ),
        "-map",
        "[outv]",
        "-t",
        f"{final_seconds:.9f}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "17",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-movflags",
        "+faststart",
        output_path,
    ]

    run_command(
        command,
        "Rendering HQ 4 random clips + fixed CTA",
    )

    duration = get_duration(
        output_path
    )

    if abs(
        duration - final_seconds
    ) > 0.20:
        raise RuntimeError(
            "Silent video does not match the speech timeline: "
            f"{duration:.3f}"
        )

    return output_path


def mux_audio(
    video_path,
    voice_path,
    output_path,
    final_seconds=25.0,
):
    voice_duration = validate_voice(voice_path)

    if abs(voice_duration - final_seconds) > 0.20:
        print(
            f"WARNING: voice duration is {voice_duration:.3f}s; "
            f"mux will enforce {final_seconds:.3f} seconds.",
            flush=True,
        )

    if not os.path.exists(BACKGROUND_MUSIC):
        raise RuntimeError(
            f"Background music is missing: {BACKGROUND_MUSIC}"
        )

    if not has_stream(BACKGROUND_MUSIC, "audio"):
        raise RuntimeError("Background music contains no audio stream.")

    fade_start = max(0.0, final_seconds - 1.0)
    audio_filter = (
        f"[1:a]apad=pad_dur=0.05,atrim=duration={final_seconds:.9f},"
        "asetpts=PTS-STARTPTS[voice];"
        f"[2:a]volume={BACKGROUND_MUSIC_VOLUME},"
        f"atrim=duration={final_seconds:.9f},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={fade_start:.3f}:d=1.0[music];"
        "[voice][music]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95[mixed]"
    )

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-i",
            voice_path,
            "-stream_loop",
            "-1",
            "-i",
            BACKGROUND_MUSIC,
            "-filter_complex",
            audio_filter,
            "-map",
            "0:v:0",
            "-map",
            "[mixed]",
            "-t",
            f"{final_seconds:.9f}",
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
            "-movflags",
            "+faststart",
            output_path,
        ],
        "Mixing ElevenLabs voice with low-volume background music",
    )

    print(
        f"BACKGROUND MUSIC MIXED | volume={BACKGROUND_MUSIC_VOLUME:.0%} | "
        f"fade_out=1.0s | duration={final_seconds:.3f}s",
        flush=True,
    )
    return output_path
