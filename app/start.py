"""Production app entrypoint with resilient voice fallback.

ElevenLabs remains the preferred provider. If its quota/API is unavailable,
`generate_voice()` is allowed to fall back to the bundled Piper voice so the
scheduler can keep creating Shorts instead of dropping required slots.

The production OAuth grant also includes youtube.force-ssl so one-time
scheduled-video replacements can unschedule old uploads safely.
"""

from app import voice, youtube

# generate_voice(text, cta_text="", output_filename="voice.mp3",
#                require_elevenlabs=True)
# Keep ElevenLabs first, but allow Piper when ElevenLabs is unavailable.
voice.generate_voice.__defaults__ = ("", "voice.mp3", False)

YOUTUBE_FORCE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
if YOUTUBE_FORCE_SSL_SCOPE not in youtube.SCOPES:
    youtube.SCOPES.append(YOUTUBE_FORCE_SSL_SCOPE)

from app import main  # noqa: E402

if YOUTUBE_FORCE_SSL_SCOPE not in main.SCOPES:
    main.SCOPES.append(YOUTUBE_FORCE_SSL_SCOPE)

app = main.app

print(
    "Production voice mode: ElevenLabs preferred, Piper fallback enabled.",
    flush=True,
)
print(
    "YouTube OAuth mode: upload + readonly + force-ssl.",
    flush=True,
)
