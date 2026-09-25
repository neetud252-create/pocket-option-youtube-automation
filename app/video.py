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
        f"I MADE: ${short_amount{'}'} EVERY DAY"
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
    voice_duration = validate_voice(
        voice_path
    )

    if abs(
        voice_duration - final_seconds
    ) > 0.20:
        print(
            f"WARNING: voice duration is {voice_duration:.3f}s; "
            f"mux will enforce {final_seconds:.3f} seconds.",
            flush=True,
        )

    run_command(
        [
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
            "-af",
            f"apad=pad_dur=0.05,atrim=duration={final_seconds:.9f}",
            "-movflags",
            "+faststart",
            output_path,
        ],
        "Muxing final voice audio",
    )

    return output_path


# ============================================================
# PUBLIC GENERATOR
# ============================================================

def generate_video(
    script="",
    voice_path=None,
    short_amount=1000,
    output_filename="short.mp4",
):
    metadata_path = os.path.splitext(voice_path or "")[0] + ".json"
    with open(metadata_path, encoding="utf-8") as file:
        timeline = json.load(file)
    final_seconds = float(timeline["final_duration"])
    cta_start = float(timeline["cta_start"])
    if not MIN_VIDEO_DURATION <= final_seconds <= MAX_VIDEO_DURATION:
        raise RuntimeError("Short duration must be between 20 and 26 seconds")
    if abs(final_seconds - cta_start - CTA_DURATION) > 0.001:
        raise RuntimeError("CTA must occupy exactly the final five seconds")

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    if not voice_path:
        raise RuntimeError(
            "voice_path was not provided."
        )

    validate_voice(
        voice_path
    )

    selected_clips = select_random_clips()

    job_id = uuid.uuid4().hex[:12]

    temp_dir = tempfile.mkdtemp(
        prefix=f"video_job_{job_id}_",
        dir=OUTPUT_DIR,
    )

    final_path = (
        output_filename
        if os.path.isabs(
            output_filename
        )
        else os.path.join(
            OUTPUT_DIR,
            output_filename,
        )
    )

    silent_path = os.path.join(
        temp_dir,
        "silent.mp4",
    )
    muxed_path = os.path.join(
        temp_dir,
        "final.mp4",
    )

    try:
        print(
            "\n==================================================",
            flush=True,
        )
        print(
            f"GENERATING HIGH-QUALITY {final_seconds:.3f}-SECOND SHORT",
            flush=True,
        )
        print(
            f"4 RANDOM clips across {cta_start:.3f}s + FIXED CTA x 5s",
            flush=True,
        )
        print(
            "Output: 1080x1920, H.264 High, CRF 17, 30 FPS",
            flush=True,
        )
        print(
            "Overlay: original green earnings headline and yellow LINK IN BIO",
            flush=True,
        )
        print(
            "==================================================",
            flush=True,
        )

        build_silent_video(
            selected_clips,
            short_amount,
            silent_path,
            final_seconds=final_seconds,
            script=script,
        )

        mux_audio(
            silent_path,
            voice_path,
            muxed_path,
            final_seconds=final_seconds,
        )

        validate_final_video(
            muxed_path, final_seconds
        )

        if os.path.exists(
            final_path
        ):
            os.remove(
                final_path
            )

        shutil.copy2(
            muxed_path,
            final_path,
        )

        validate_final_video(
            final_path, final_seconds
        )

        print(
            f"VIDEO GENERATION SUCCESS: {final_path}",
            flush=True,
        )

        return final_path

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )
