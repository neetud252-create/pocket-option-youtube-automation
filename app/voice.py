import base64
import json
import os
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


# ============================================================
# ELEVENLABS
# ============================================================

def elevenlabs_tts(text, output_path):
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured.")

    url = f"{ELEVENLABS_API_URL}/{VOICE_ID}/with-timestamps"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    params = {"output_format": "mp3_44100_128"}

    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.10,
            "use_speaker_boost": True,
            "speed": 0.96,
        },
    }

    last_error = None

    for attempt in range(1, ELEVENLABS_RETRIES + 1):
        print(
            f"ElevenLabs request {attempt}/{ELEVENLABS_RETRIES} | "
            f"voice={VOICE_ID} model={MODEL_ID}",
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
            last_error = RuntimeError(f"ElevenLabs connection failed: {exc}")
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

        # Retry temporary rate/server failures. Quota/auth errors should fail
        # immediately so the scheduler can retry later instead of wasting time.
        if response.status_code in {429, 500, 502, 503, 504} and attempt < ELEVENLABS_RETRIES:
            time.sleep(2 * attempt)
            continue

        raise last_error

    raise last_error or RuntimeError("ElevenLabs voice generation failed.")


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
            input_text=text.strip() + "\n",
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
    """
    Scheduled production Shorts use require_elevenlabs=True, guaranteeing the
    new scheduled videos use the paid ElevenLabs voice. Other/manual jobs may
    still use Piper as a safety fallback.
    """
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
            "Scheduled production requires ElevenLabs, but ElevenLabs is unavailable."
        )

    piper_tts(text, output_path)
    print("Voice provider: Piper fallback", flush=True)
    return "piper"


# ============================================================
# TIMING / ALIGNMENT
# ============================================================

def atempo_filter_for_speed(speed_factor):
    factor = max(1.0, float(speed_factor))
    filters = []

    while factor > 2.0:
        filters.append("atempo=2.0")
        factor /= 2.0

    if factor > 1.001:
        filters.append(f"atempo={factor:.6f}")

    return filters


def fit_audio_to_exact_duration(input_path, output_path, target_seconds):
    original_duration = validate_audio(input_path)
    usable_seconds = max(0.25, target_seconds - 0.08)

    speed_factor = (
        original_duration / usable_seconds
        if original_duration > usable_seconds
        else 1.0
    )

    filters = atempo_filter_for_speed(speed_factor)
    filters.extend([
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
            "128k",
            "-ar",
            "44100",
            "-ac",
            "1",
            output_path,
        ],
        f"Fitting voice to {target_seconds:.1f} seconds",
    )

    final_duration = validate_audio(output_path)
    if abs(final_duration - target_seconds) > 0.15:
        raise RuntimeError(
            f"Voice timing failed: expected {target_seconds}s, "
            f"got {final_duration:.3f}s"
        )

    return {
        "original_duration": original_duration,
        "final_duration": final_duration,
        "speed_factor": speed_factor,
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
            "128k",
            "-ar",
            "44100",
            "-ac",
            "1",
            output_path,
        ],
        "Joining 20-second narration + 5-second CTA audio",
    )

    duration = validate_audio(output_path)
    if abs(duration - FINAL_AUDIO_SECONDS) > 0.15:
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

    clean_text = text.strip()
    clean_cta = (
        cta_text.strip()
        if cta_text and cta_text.strip()
        else "Go to my channel description and click the Bot Activation button."
    )

    output_path = (
        output_filename
        if os.path.isabs(output_filename)
        else os.path.join("/app/output", output_filename)
    )

    output_dir = os.path.dirname(output_path) or "/app/output"
    os.makedirs(output_dir, exist_ok=True)

    metadata_path = os.path.splitext(output_path)[0] + ".json"
    work_dir = tempfile.mkdtemp(prefix="voice_job_", dir=output_dir)

    raw_main = os.path.join(work_dir, "main_raw.mp3")
    raw_cta = os.path.join(work_dir, "cta_raw.mp3")
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

        main_timing = fit_audio_to_exact_duration(
            raw_main,
            fit_main,
            MAIN_AUDIO_SECONDS,
        )
        cta_timing = fit_audio_to_exact_duration(
            raw_cta,
            fit_cta,
            CTA_AUDIO_SECONDS,
        )

        final_duration = join_audio(fit_main, fit_cta, output_path)

        metadata = {
            "main_text": clean_text,
            "cta_text": clean_cta,
            "main_provider": main_provider,
            "cta_provider": cta_provider,
            "main_timing": main_timing,
            "cta_timing": cta_timing,
            "cta_start": 20.0,
            "cta_end": 25.0,
            "final_duration": final_duration,
            "require_elevenlabs": require_elevenlabs,
        }

        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2, ensure_ascii=False)

        print(
            f"Voice complete: narration=0-20s, CTA=20-25s | "
            f"providers={main_provider}/{cta_provider}",
            flush=True,
        )

        return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
