import base64
import json
import os
import re
import random
import math
import shutil
import subprocess
import tempfile
import time

import requests


# ============================================================
# CONFIG
# ============================================================

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "nPczCjzI2devNBz1zQrb",
)

MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID",
    "eleven_multilingual_v2",
)

PIPER_MODEL = os.getenv(
    "PIPER_MODEL_PATH",
    "/app/voices/en_US-lessac-medium.onnx",
)

CTA_AUDIO_SECONDS = 5.0
FPS = 30
MIN_MAIN_FRAMES = 15 * FPS
MAX_MAIN_FRAMES = 21 * FPS
ELEVENLABS_RETRIES = 3

# Retention-first pacing: remove dead air, but never slow the voice down
# just to fill the 20-second narration section.
SILENCE_THRESHOLD_DB = -45
LONG_PAUSE_SECONDS = 0.12
KEPT_PAUSE_SECONDS = 0.025


# ============================================================
# PROCESS HELPERS
# ============================================================

def run_command(command, description, input_text=None, timeout=240):
    print(f"Running: {description}", flush=True)

    try:
        result = subprocess.run(
            command,
            input=input_text,
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
        print(f"{description} failed.", flush=True)
        print(result.stderr[-4000:], flush=True)
        raise RuntimeError(f"{description} failed.")

    return result


def audio_duration(path):
    if not os.path.exists(path):
        raise RuntimeError(f"Audio file does not exist: {path}")

    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        f"Checking audio duration: {os.path.basename(path)}",
    )

    try:
        return float(result.stdout.strip())
    except Exception as exc:
        raise RuntimeError(
            f"Could not read audio duration for {path}"
        ) from exc


def validate_audio(path):
    if not os.path.exists(path):
        raise RuntimeError(f"Audio was not created: {path}")

    if os.path.getsize(path) <= 0:
        raise RuntimeError(f"Audio file is empty: {path}")

    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            path,
        ],
        f"Checking audio stream: {os.path.basename(path)}",
    )

    if "audio" not in result.stdout.lower():
        raise RuntimeError(f"No audio stream found in {path}")

    duration = audio_duration(path)
    if duration <= 0:
        raise RuntimeError(f"Audio duration is zero: {path}")

    return duration


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def clean_spoken_text(text):
    value = str(text or "")
    value = value.replace("…", ".").replace("...", ".")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.!?])", r"\1", value)
    return value.strip()


# ============================================================
# ELEVENLABS
# ============================================================

def elevenlabs_tts(text, output_path, previous_text=None, next_text=None):
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured.")

    clean_text = clean_spoken_text(text)
    if not clean_text:
        raise RuntimeError("ElevenLabs text is empty.")

    url = f"{ELEVENLABS_API_URL}/{VOICE_ID}/with-timestamps"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    params = {"output_format": "mp3_44100_128"}

    payload = {
        "text": clean_text,
        "model_id": MODEL_ID,
        "voice_settings": {
            # More expressive, energetic delivery without sounding unstable.
            "stability": 0.40,
            "similarity_boost": 0.84,
            "style": 0.18,
            "use_speaker_boost": True,
            # Noticeably faster than the old voice, while staying natural.
            "speed": 1.08,
        },
    }

    if previous_text:
        payload["previous_text"] = previous_text
    if next_text:
        payload["next_text"] = next_text

    last_error = None

    for attempt in range(1, ELEVENLABS_RETRIES + 1):
        print(
            f"ElevenLabs request {attempt}/{ELEVENLABS_RETRIES} | "
            f"voice={VOICE_ID} model={MODEL_ID} speed=1.08",
            flush=True,
        )

        try:
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=120,
            )
        except requests.RequestException as exc:
            last_error = RuntimeError(
                f"ElevenLabs connection failed: {exc}"
            )
            if attempt < ELEVENLABS_RETRIES:
                time.sleep(2 * attempt)
                continue
            raise last_error from exc

        if response.status_code == 200:
            try:
                data = response.json()
                audio_b64 = data.get("audio_base64")
                if not audio_b64:
                    raise ValueError("audio_base64 missing")
                audio_data = base64.b64decode(audio_b64)
            except Exception as exc:
                raise RuntimeError(
                    "ElevenLabs response did not contain valid audio."
                ) from exc

            with open(output_path, "wb") as file:
                file.write(audio_data)

            validate_audio(output_path)
            return output_path

        provider_message = response.text[:1500]
        last_error = RuntimeError(
            f"ElevenLabs HTTP {response.status_code}: {provider_message}"
        )

        if (
            response.status_code in {429, 500, 502, 503, 504}
            and attempt < ELEVENLABS_RETRIES
        ):
            time.sleep(2 * attempt)
            continue

        raise last_error

    raise last_error or RuntimeError(
        "ElevenLabs voice generation failed."
    )


# ============================================================
# LOCAL PIPER FALLBACK
# ============================================================

def piper_tts(text, output_path):
    if shutil.which("piper") is None:
        raise RuntimeError("Piper executable is not installed.")

    if not os.path.exists(PIPER_MODEL):
        raise RuntimeError(f"Piper model is missing: {PIPER_MODEL}")

    wav_path = os.path.splitext(output_path)[0] + "_piper.wav"

    try:
        run_command(
            [
                "piper",
                "--model",
                PIPER_MODEL,
                "--output_file",
                wav_path,
            ],
            "Generating local Piper voice",
            input_text=clean_spoken_text(text) + "\n",
            timeout=180,
        )

        validate_audio(wav_path)

        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                wav_path,
                "-vn",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-ac",
                "1",
                output_path,
            ],
            "Converting Piper voice to MP3",
        )

        validate_audio(output_path)
        return output_path

    finally:
        safe_remove(wav_path)


def generate_raw_segment(text, output_path, require_elevenlabs=False, **context):
    try:
        if os.getenv("ELEVENLABS_API_KEY"):
            elevenlabs_tts(text, output_path, **context)
            print("Voice provider: ElevenLabs", flush=True)
            return "elevenlabs"
    except Exception as exc:
        print(f"ElevenLabs generation error: {exc}", flush=True)
        safe_remove(output_path)
        if require_elevenlabs:
            raise

    if require_elevenlabs:
        raise RuntimeError(
            "Scheduled production requires ElevenLabs, "
            "but ElevenLabs is unavailable."
        )

    piper_tts(text, output_path)
    print("Voice provider: Piper fallback", flush=True)
    return "piper"


# ============================================================
# TIMING / ALIGNMENT
# ============================================================

def compact_silence(input_path, output_path):
    """Reduce long sentence pauses to a quick, natural beat."""
    validate_audio(input_path)

    silence_filter = (
        "silenceremove="
        f"start_periods=1:start_duration=0.02:"
        f"start_threshold={SILENCE_THRESHOLD_DB}dB:"
        f"stop_periods=-1:stop_duration={LONG_PAUSE_SECONDS:.2f}:"
        f"stop_threshold={SILENCE_THRESHOLD_DB}dB:"
        f"stop_silence={KEPT_PAUSE_SECONDS:.3f},"
        "areverse,silenceremove=start_periods=1:start_duration=0:"
        f"start_threshold={SILENCE_THRESHOLD_DB}dB,areverse"
    )

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vn",
            "-af",
            silence_filter,
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "1",
            output_path,
        ],
        "Removing dead air and trimming speech edges",
    )

    validate_audio(output_path)
    return output_path


def atempo_filters_for_factor(speed_factor):
    factor = max(0.10, float(speed_factor))
    filters = []

    while factor > 2.0:
        filters.append("atempo=2.0")
        factor /= 2.0

    while factor < 0.5:
        filters.append("atempo=0.5")
        factor /= 0.5

    if abs(factor - 1.0) > 0.001:
        filters.append(f"atempo={factor:.6f}")

    return filters


def choose_main_duration(raw_seconds):
    """Random frame-aligned length, with no slowdown or excessive rushing."""
    low = max(MIN_MAIN_FRAMES, math.ceil(raw_seconds / 1.30 * FPS))
    high = min(MAX_MAIN_FRAMES, math.floor(raw_seconds * FPS))
    if low > high:
        raise RuntimeError(
            f"Narration length {raw_seconds:.2f}s cannot fit a 20-26s Short "
            "at natural-to-fast speed. Regenerate the script."
        )
    return random.randint(low, high) / FPS


def fit_audio(input_path, output_path, target_seconds, allow_slowdown=True):
    """Fit speech to its entire slot, never add a long silence before CTA."""
    original_duration = validate_audio(input_path)
    factor = original_duration / target_seconds
    filters = atempo_filters_for_factor(factor)
    filters += [
        "aresample=44100",
        "loudnorm=I=-14:TP=-1.5:LRA=7",
        "aresample=44100",
        # Only compensates for atempo's few milliseconds of rounding.
        "apad=pad_dur=0.05",
        f"atrim=end_sample={round(target_seconds * 44100)}",
        "asetpts=N/SR/TB",
    ]
    run_command([
        "ffmpeg", "-y", "-i", input_path, "-vn", "-af", ",".join(filters),
        "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "1", output_path,
    ], f"Fitting continuous speech to {target_seconds:.3f}s")
    duration = validate_audio(output_path)
    if abs(duration - target_seconds) > 0.04:
        raise RuntimeError(f"Speech timing mismatch: {duration} vs {target_seconds}")
    return {"original_duration": original_duration, "final_duration": duration,
            "speed_factor": factor, "slowed_down": factor < 0.999}


def verify_cta_join(path, cta_start):
    result = run_command([
        "ffmpeg", "-hide_banner", "-i", path, "-af",
        "silencedetect=noise=-45dB:d=0.12", "-f", "null", "-",
    ], "Checking narration-to-CTA transition for dead air")
    starts = re.findall(r"silence_start: ([0-9.]+)", result.stderr)
    ends = re.findall(r"silence_end: ([0-9.]+)", result.stderr)
    for start, end in zip(starts, ends):
        if float(start) < cta_start + 0.06 and float(end) > cta_start - 0.06:
            raise RuntimeError(f"Dead air at CTA transition: {start}-{end}s")
    print(f"CTA JOIN VERIFIED | start={cta_start:.3f}s | no gap >=120ms", flush=True)


def join_audio(main_path, cta_path, output_path, final_seconds, cta_start):
    run_command([
        "ffmpeg", "-y", "-i", main_path, "-i", cta_path,
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]",
        "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "192k",
        "-ar", "44100", "-ac", "1", output_path,
    ], "Joining narration directly into the fixed 5-second CTA")
    duration = validate_audio(output_path)
    if abs(duration - final_seconds) > 0.10:
        raise RuntimeError(f"Final audio timing mismatch: {duration} vs {final_seconds}")
    verify_cta_join(output_path, cta_start)
    return duration


# ============================================================
# PUBLIC GENERATOR
# ============================================================

def generate_voice(
    text: str,
    cta_text: str = "",
    output_filename: str = "voice.mp3",
    require_elevenlabs: bool = True,
) -> str:
    if not text or not text.strip():
        raise ValueError("Voice text cannot be empty.")

    clean_text = clean_spoken_text(text)
    clean_cta = clean_spoken_text(
        cta_text
        if cta_text and cta_text.strip()
        else (
            "Go to my channel description and click "
            "the Bot Activation button."
        )
    )

    output_path = (
        output_filename
        if os.path.isabs(output_filename)
        else os.path.join("/app/output", output_filename)
    )

    output_dir = os.path.dirname(output_path) or "/app/output"
    os.makedirs(output_dir, exist_ok=True)

    metadata_path = os.path.splitext(output_path)[0] + ".json"
    work_dir = tempfile.mkdtemp(
        prefix="voice_job_",
        dir=output_dir,
    )

    raw_main = os.path.join(work_dir, "main_raw.mp3")
    raw_cta = os.path.join(work_dir, "cta_raw.mp3")
    compact_main = os.path.join(work_dir, "main_compact.wav")
    compact_cta = os.path.join(work_dir, "cta_compact.wav")
    fit_main = os.path.join(work_dir, "main_fitted.wav")
    fit_cta = os.path.join(work_dir, "cta_fitted.wav")

    print("\n===== VOICE GENERATION =====", flush=True)
    print(f"Main script: {clean_text}", flush=True)
    print(f"CTA: {clean_cta}", flush=True)
    print(f"Require ElevenLabs: {require_elevenlabs}", flush=True)

    try:
        main_provider = generate_raw_segment(
            clean_text,
            raw_main,
            require_elevenlabs=require_elevenlabs,
            next_text=clean_cta,
        )
        cta_provider = generate_raw_segment(
            clean_cta,
            raw_cta,
            require_elevenlabs=require_elevenlabs,
            previous_text=clean_text,
        )

        compact_silence(raw_main, compact_main)
        compact_silence(raw_cta, compact_cta)

        main_seconds = choose_main_duration(audio_duration(compact_main))
        final_seconds = main_seconds + CTA_AUDIO_SECONDS
        print(f"RANDOM TIMELINE | total={final_seconds:.3f}s | main={main_seconds:.3f}s | CTA=5.000s", flush=True)
        main_timing = fit_audio(
            compact_main,
            fit_main,
            main_seconds,
        )
        cta_timing = fit_audio(
            compact_cta,
            fit_cta,
            CTA_AUDIO_SECONDS,
        )

        final_duration = join_audio(
            fit_main,
            fit_cta,
            output_path,
            final_seconds,
            main_seconds,
        )

        metadata = {
            "main_text": clean_text,
            "cta_text": clean_cta,
            "main_provider": main_provider,
            "cta_provider": cta_provider,
            "main_timing": main_timing,
            "cta_timing": cta_timing,
            "elevenlabs_speed": 1.08,
            "pause_compaction": {
                "threshold_db": SILENCE_THRESHOLD_DB,
                "long_pause_seconds": LONG_PAUSE_SECONDS,
                "kept_pause_seconds": KEPT_PAUSE_SECONDS,
            },
            "cta_start": main_seconds,
            "cta_end": final_seconds,
            "final_duration": final_seconds,
            "encoded_audio_duration": final_duration,
            "voice_id": VOICE_ID,
            "require_elevenlabs": require_elevenlabs,
        }

        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(
                metadata,
                file,
                indent=2,
                ensure_ascii=False,
            )

        print(
            "Voice complete: energetic ElevenLabs pacing, "
            f"continuous speech, natural-speed CTA={main_seconds:.3f}-{final_seconds:.3f}s",
            flush=True,
        )

        return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

