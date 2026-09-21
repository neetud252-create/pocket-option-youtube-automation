import os
import wave
import subprocess

from piper import PiperVoice


VOICE_NAME = "en_US-lessac-medium"

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

VOICE_DIR = os.path.join(
    BASE_DIR,
    "voices"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

MODEL_PATH = os.path.join(
    VOICE_DIR,
    f"{VOICE_NAME}.onnx"
)


def generate_voice(
    text: str,
    output_filename: str = "voice.wav"
) -> str:

    if not text:
        raise ValueError(
            "Voice text cannot be empty."
        )

    os.makedirs(
        VOICE_DIR,
        exist_ok=True
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Piper voice model not found: {MODEL_PATH}"
        )

    print(
        "Loading Piper male voice...",
        flush=True
    )

    voice = PiperVoice.load(
        MODEL_PATH
    )

    raw_output = os.path.join(
        OUTPUT_DIR,
        "raw_voice.wav"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    print(
        "Generating slower male voice...",
        flush=True
    )

    with wave.open(
        raw_output,
        "wb"
    ) as wav_file:

        voice.synthesize_wav(
            text,
            wav_file
        )

    # --------------------------------
    # DEEPER + SLOWER VOICE
    # --------------------------------

    # Lower pitch slightly while preserving
    # natural speech timing, then slow speech.
    command = [
        "ffmpeg",
        "-y",

        "-i",
        raw_output,

        "-af",
        (
            "asetrate=22050*0.94,"
            "aresample=22050,"
            "atempo=0.92"
        ),

        "-ar",
        "22050",

        "-ac",
        "1",

        output_path,
    ]

    print(
        "Applying deep and slow voice processing...",
        flush=True
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            result.stderr,
            flush=True
        )

        raise RuntimeError(
            "FFmpeg voice processing failed."
        )

    if not os.path.exists(
        output_path
    ):
        raise RuntimeError(
            "Processed voice was not created."
        )

    print(
        f"Voice generated: {output_path}",
        flush=True
    )

    return output_path
