import os
import base64
import json
import requests


OUTPUT_DIR = "/app/output"

ELEVENLABS_API_URL = (
    "https://api.elevenlabs.io/v1/text-to-speech"
)

VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "JBFqnCBsd6RMkjVDRZzb"
)

MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID",
    "eleven_multilingual_v2"
)


def generate_voice(
    text: str,
    cta_text: str = "",
    output_filename: str = "voice.mp3"
) -> str:

    if not text:
        raise ValueError(
            "Voice text cannot be empty."
        )

    api_key = os.getenv(
        "ELEVENLABS_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not configured."
        )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    metadata_path = os.path.splitext(
        output_path
    )[0] + ".json"

    url = (
        f"{ELEVENLABS_API_URL}/"
        f"{VOICE_ID}/with-timestamps"
    )

    params = {
        "output_format": "mp3_44100_128"
    }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": MODEL_ID,

        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.10,
            "use_speaker_boost": True,
            "speed": 0.92
        }
    }

    print(
        "Generating ElevenLabs professional male voice...",
        flush=True
    )

    print(
        f"Voice ID: {VOICE_ID}",
        flush=True
    )

    print(
        f"Model: {MODEL_ID}",
        flush=True
    )

    try:

        response = requests.post(
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=180
        )

    except requests.RequestException as e:

        raise RuntimeError(
            f"ElevenLabs connection failed: {e}"
        )

    if response.status_code != 200:

        print(
            "===== ELEVENLABS ERROR =====",
            flush=True
        )

        print(
            response.text,
            flush=True
        )

        raise RuntimeError(
            f"ElevenLabs API returned "
            f"HTTP {response.status_code}"
        )

    try:

        data = response.json()

    except Exception:

        raise RuntimeError(
            "ElevenLabs returned invalid JSON."
        )

    if "audio_base64" not in data:

        raise RuntimeError(
            "ElevenLabs response did not "
            "contain audio."
        )

    # ---------------------------------------------------------
    # SAVE AUDIO
    # ---------------------------------------------------------

    try:

        audio_data = base64.b64decode(
            data["audio_base64"]
        )

    except Exception as e:

        raise RuntimeError(
            f"Could not decode ElevenLabs audio: {e}"
        )

    with open(
        output_path,
        "wb"
    ) as audio_file:

        audio_file.write(
            audio_data
        )

    print(
        f"ElevenLabs audio created: "
        f"{output_path}",
        flush=True
    )

    # ---------------------------------------------------------
    # CTA TIMING
    #
    # ElevenLabs returns character-level timestamps.
    # We use them to determine exactly when the CTA begins.
    # ---------------------------------------------------------

    cta_start = None
    cta_end = None

    alignment = data.get(
        "alignment"
    )

    if alignment and cta_text:

        characters = alignment.get(
            "characters",
            []
        )

        start_times = alignment.get(
            "character_start_times_seconds",
            []
        )

        end_times = alignment.get(
            "character_end_times_seconds",
            []
        )

        cta_index = text.find(
            cta_text
        )

        if (
            cta_index >= 0
            and len(characters)
            == len(start_times)
            == len(end_times)
        ):

            start_index = cta_index

            end_index = (
                cta_index
                + len(cta_text)
                - 1
            )

            if end_index < len(
                start_times
            ):

                cta_start = float(
                    start_times[start_index]
                )

                cta_end = float(
                    end_times[end_index]
                )

    # ---------------------------------------------------------
    # SAVE TIMING METADATA
    # ---------------------------------------------------------

    metadata = {
        "voice_id": VOICE_ID,
        "model_id": MODEL_ID,
        "text": text,
        "cta_text": cta_text,
        "cta_start": cta_start,
        "cta_end": cta_end
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as metadata_file:

        json.dump(
            metadata,
            metadata_file,
            indent=2
        )

    print(
        f"CTA start: {cta_start}",
        flush=True
    )

    print(
        f"CTA end: {cta_end}",
        flush=True
    )

    print(
        "ElevenLabs voice generation complete.",
        flush=True
    )

    return output_path
