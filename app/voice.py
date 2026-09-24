import base64
import json
import os
import re
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
    "JBFqnCBsd6RMkjVDRZzb",
)

MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID",
    "eleven_multilingual_v2",
)

PIPER_MODEL = os.getenv(
    "PIPER_MODEL_PATH",
    "/app/voices/en_US-lessac-medium.onnx",
)

MAIN_AUDIO_SECONDS = 20.0
CTA_AUDIO_SECONDS = 5.0
FINAL_AUDIO_SECONDS = 25.0
ELEVENLABS_RETRIES = 3

# Retention-first pacing: remove dead air, but never slow the voice down
# just to fill the 20-second narration section.
SILENCE_THRESHOLD_DB = -48
LONG_PAUSE_SECONDS = 0.20
KEPT_PAUSE_SECONDS = 0.06


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

def elevenlabs_tts(text, output_path):
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
            "stability": 0.36,
            "similarity_boost": 0.84,
            "style": 0.30,
            "use_speaker_boost": True,
            # Noticeably faster than the old voice, while staying natural.
            "speed": 1.08,
        },
    }

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


def generate_raw_segment(text, output_path, require_elevenlabs=False):
    try:
        if os.getenv("ELEVENLABS_API_KEY"):
            elevenlabs_tts(text, output_path)
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
        f"stop_silence={KEPT_PAUSE_SECONDS:.2f}"
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
            "libmp3lame",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-ac",
            "1",
            output_path,
        ],
        "Compressing long narration pauses",
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


def fit_audio_without_slowing(
    input_path,
    output_path,
    target_seconds,
):
    """
    Keep ElevenLabs at natural/fast speed.
    If speech is too long, speed it up enough to fit.
    If speech is shorter, NEVER slow it down; pad the remaining section.
    """
    original_duration = validate_audio(input_path)
    usable_seconds = max(0.25, target_seconds - 0.10)

    if original_duration > usable_seconds:
        speed_factor = original_duration / usable_seconds
    else:
        speed_factor = 1.0

    filters = atempo_filters_for_factor(speed_factor)

    # A consistent Shorts-style loudness helps the narration feel more present.
    filters.extend([
        "loudnorm=I=-14:TP=-1.5:LRA=7",
        f"apad=pad_dur={target_seconds:.3f}",
        f"atrim=duration={target_seconds:.3f}",
        "asetpts=N/SR/TB",
    ])

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vn",
            "-af",
            ",".join(filters),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "160k",
            "-ar",
            "44100",
            "-ac",
            "1",
            output_path,
        ],
        f"Fitting voice to {target_seconds:.1f}s without slowing",
    )

    final_duration = validate_audio(output_path)
    if abs(final_duration - target_seconds) > 0.20:
        raise RuntimeError(
            f"Voice timing failed: expected {target_seconds}s, "
            f"got {final_duration:.3f}s"
        )

    return {
        "original_duration": original_duration,
        "final_duration": final_duration,
        "speed_factor": speed_factor,
        "slowed_down": False,
    }


def join_audio(main_path, cta_path, output_path):
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            main_path,
            "-i",
            cta_path,
            "-filter_complex",
            "[0:a][1:a]concat=n=2:v=0:a=1[a]",
            "-map",
            "[a]",
            "-t",
            f"{FINAL_AUDIO_SECONDS:.3f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "160k",
            "-ar",
            "44100",
            "-ac",
            "1",
            output_path,
        ],
        "Joining 20-second narration + 5-second CTA audio",
    )

    duration = validate_audio(output_path)
    if abs(duration - FINAL_AUDIO_SECONDS) > 0.20:
        raise RuntimeError(
            f"Final voice is not 25 seconds: {duration:.3f}s"
        )

    return duration


# ============================================================
# PUBLIC GENERATOR
# ============================================================

def generate_voice(
    text: str,
    cta_text: str = "",
    output_filename: str = "voice.mp3",
    require_elevenlabs: bool = False,
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
    compact_main = os.path.join(work_dir, "main_compact.mp3")
    compact_cta = os.path.join(work_dir, "cta_compact.mp3")
    fit_main = os.path.join(work_dir, "main_20.mp3")
    fit_cta = os.path.join(work_dir, "cta_5.mp3")

    print("\n===== VOICE GENERATION =====", flush=True)
    print(f"Main script: {clean_text}", flush=True)
    print(f"CTA: {clean_cta}", flush=True)
    print(f"Require ElevenLabs: {require_elevenlabs}", flush=True)

    try:
        main_provider = generate_raw_segment(
            clean_text,
            raw_main,
            require_elevenlabs=require_elevenlabs,
        )
        cta_provider = generate_raw_segment(
            clean_cta,
            raw_cta,
            require_elevenlabs=require_elevenlabs,
        )

        compact_silence(raw_main, compact_main)
        compact_silence(raw_cta, compact_cta)

        main_timing = fit_audio_without_slowing(
            compact_main,
            fit_main,
            MAIN_AUDIO_SECONDS,
        )
        cta_timing = fit_audio_without_slowing(
            compact_cta,
            fit_cta,
            CTA_AUDIO_SECONDS,
        )

        final_duration = join_audio(
            fit_main,
            fit_cta,
            output_path,
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
            "cta_start": 20.0,
            "cta_end": 25.0,
            "final_duration": final_duration,
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
            "no artificial slow-down, CTA=20-25s",
            flush=True,
        )

        return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
