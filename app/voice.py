import os
import base64
import json
import requests


# ============================================================
# CONFIG
# ============================================================

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


# ============================================================
# GENERATE VOICE
# ============================================================

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

    metadata_path = (
        os.path.splitext(
            output_path
        )[0]
        + ".json"
    )

    # ========================================================
    # BUILD COMPLETE SPOKEN SCRIPT
    # ========================================================

    clean_text = text.strip()

    clean_cta = (
        cta_text.strip()
        if cta_text
        else ""
    )

    if clean_cta:

        full_text = (
            clean_text
            + " "
            + clean_cta
        )

    else:

        full_text = clean_text

    print(
        "\n===== ELEVENLABS VOICE =====",
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

    print(
        "\nMain script:",
        flush=True
    )

    print(
        clean_text,
        flush=True
    )

    print(
        "\nCTA:",
        flush=True
    )

    print(
        clean_cta,
        flush=True
    )

    print(
        "\nFull spoken text:",
        flush=True
    )

    print(
        full_text,
        flush=True
    )

    print(
        "============================",
        flush=True
    )


    # ========================================================
    # ELEVENLABS API
    # ========================================================

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

        "text": full_text,

        "model_id": MODEL_ID,

        "voice_settings": {

            "stability": 0.50,

            "similarity_boost": 0.85,

            "style": 0.10,

            "use_speaker_boost": True,

            "speed": 0.92
        }
    }


    # ========================================================
    # REQUEST
    # ========================================================

    print(
        "\nGenerating ElevenLabs voice...",
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


    # ========================================================
    # API ERROR
    # ========================================================

    if response.status_code != 200:

        print(
            "\n===== ELEVENLABS ERROR =====",
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


    # ========================================================
    # JSON RESPONSE
    # ========================================================

    try:

        data = response.json()

    except Exception:

        raise RuntimeError(
            "ElevenLabs returned invalid JSON."
        )


    # ========================================================
    # CHECK AUDIO
    # ========================================================

    if "audio_base64" not in data:

        raise RuntimeError(
            "ElevenLabs response did not "
            "contain audio."
        )


    # ========================================================
    # DECODE AUDIO
    # ========================================================

    try:

        audio_data = base64.b64decode(
            data["audio_base64"]
        )

    except Exception as e:

        raise RuntimeError(
            f"Could not decode ElevenLabs "
            f"audio: {e}"
        )


    if not audio_data:

        raise RuntimeError(
            "ElevenLabs returned empty audio."
        )


    # ========================================================
    # SAVE AUDIO
    # ========================================================

    with open(
        output_path,
        "wb"
    ) as audio_file:

        audio_file.write(
            audio_data
        )


    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "Voice file was not created."
        )


    file_size = (
        os.path.getsize(
            output_path
        )
    )


    if file_size <= 0:

        raise RuntimeError(
            "Voice file is empty."
        )


    print(
        f"\nElevenLabs audio created:",
        flush=True
    )

    print(
        output_path,
        flush=True
    )

    print(
        f"Audio size: "
        f"{file_size / 1024:.2f} KB",
        flush=True
    )


    # ========================================================
    # CTA TIMING
    #
    # ElevenLabs returns character-level
    # timestamps.
    # ========================================================

    cta_start = None
    cta_end = None

    alignment = data.get(
        "alignment"
    )


    if (
        alignment
        and clean_cta
    ):

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


        # Find CTA inside the complete
        # spoken text.

        cta_index = full_text.find(
            clean_cta
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
                + len(clean_cta)
                - 1
            )


            if (
                start_index
                < len(start_times)
                and
                end_index
                < len(end_times)
            ):

                cta_start = float(
                    start_times[
                        start_index
                    ]
                )

                cta_end = float(
                    end_times[
                        end_index
                    ]
                )


    # ========================================================
    # SAVE METADATA
    # ========================================================

    metadata = {

        "voice_id":
            VOICE_ID,

        "model_id":
            MODEL_ID,

        "main_text":
            clean_text,

        "cta_text":
            clean_cta,

        "full_text":
            full_text,

        "cta_start":
            cta_start,

        "cta_end":
            cta_end
    }


    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as metadata_file:

        json.dump(
            metadata,
            metadata_file,
            indent=2,
            ensure_ascii=False
        )


    print(
        f"\nCTA start: "
        f"{cta_start}",
        flush=True
    )

    print(
        f"CTA end: "
        f"{cta_end}",
        flush=True
    )

    print(
        "\nElevenLabs voice generation "
        "complete.",
        flush=True
    )

    return output_path
