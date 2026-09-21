import os
import wave

from piper import PiperVoice


VOICE_NAME = "en_US-lessac-medium"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VOICE_DIR = os.path.join(BASE_DIR, "voices")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

MODEL_PATH = os.path.join(
    VOICE_DIR,
    f"{VOICE_NAME}.onnx"
)


def generate_voice(text: str, output_filename: str = "voice.wav") -> str:

    if not text:
        raise ValueError("Voice text cannot be empty.")

    os.makedirs(VOICE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Piper downloads the voice model separately.
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Piper voice model not found: {MODEL_PATH}"
        )

    print("Loading Piper voice...", flush=True)

    voice = PiperVoice.load(MODEL_PATH)

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    print("Generating voice...", flush=True)

    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    print(
        f"Voice generated: {output_path}",
        flush=True
    )

    return output_path
