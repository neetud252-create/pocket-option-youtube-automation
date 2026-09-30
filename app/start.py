"""Production app entrypoint with resilient voice fallback.

ElevenLabs remains the preferred provider. If its quota/API is unavailable,
`generate_voice()` is allowed to fall back to the bundled Piper voice so the
scheduler can keep creating Shorts instead of dropping required slots.
"""

from app import voice

# generate_voice(text, cta_text="", output_filename="voice.mp3",
#                require_elevenlabs=True)
# Keep ElevenLabs first, but allow Piper when ElevenLabs is unavailable.
voice.generate_voice.__defaults__ = ("", "voice.mp3", False)

from app.main import app  # noqa: E402

print(
    "Production voice mode: ElevenLabs preferred, Piper fallback enabled.",
    flush=True,
)
