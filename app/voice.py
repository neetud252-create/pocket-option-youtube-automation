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
        "Generating natural male voice...",
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

    # ---------------------------------------------------------
    # PROFESSIONAL VOICE PROCESSING
    #
    # 1. Slightly lower pitch
    # 2. Slow the voice naturally
    # 3. Remove unnecessary low rumble
    # 4. Add controlled low-mid warmth
    # 5. Improve vocal clarity
    # 6. Compress the voice
    # 7. Dynamically normalize volume
    # 8. Final loudness normalization
    # ---------------------------------------------------------

    audio_filter = (
        "asetrate=22050*0.96,"
        "aresample=44100,"
        "atempo=0.94,"
        "highpass=f=70,"
        "equalizer=f=120:t=q:w=0.9:g=2,"
        "equalizer=f=250:t=q:w=1.0:g=1.5,"
        "equalizer=f=3200:t=q:w=1.0:g=2,"
        "equalizer=f=6500:t=q:w=1.0:g=-1,"
        "acompressor="
        "threshold=-18dB:"
        "ratio=2.5:"
        "attack=8:"
        "release=100:"
        "makeup=2,"
        "dynaudnorm="
        "f=150:"
        "g=7:"
        "p=0.92,"
        "loudnorm="
        "I=-14:"
        "LRA=7:"
        "TP=-1.5"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        raw_output,
        "-af",
        audio_filter,
        "-ar",
        "44100",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        output_path,
    ]

    print(
        "Applying professional voice enhancement...",
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
            "FFmpeg voice enhancement failed."
        )

    if not os.path.exists(output_path):

        raise RuntimeError(
            "Enhanced voice was not created."
        )

    print(
        f"Enhanced voice created: {output_path}",
        flush=True
    )

    return output_path
