import time

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.5-flash"


SYSTEM_PROMPT = """
You are a professional YouTube Shorts scriptwriter.

Create ONE original spoken script for a YouTube Short about an AI
trading bot.

The Short has TWO clearly separated parts.

PART 1 — TRADING BOT

The first half should explain one useful concept about the AI
trading bot.

PART 2 — CTA

The second half should naturally tell interested viewers to open
the YouTube Related Video and watch the complete setup tutorial.

The CTA must communicate this idea:

"Tap the Related Video below the title to watch the complete setup
tutorial."

Naturally change the wording every time.

LENGTH:

42–48 words total.

The BOT section should contain approximately 20–24 words.

The CTA section should contain approximately 20–24 words.

The complete script should normally produce approximately
15–20 seconds of natural narration.

Every script must be substantially different.

Vary:

- hook
- trading concept
- explanation
- sentence structure
- CTA wording

Never:

- promise profits
- guarantee winning trades
- guarantee signals
- claim the bot cannot lose
- invent statistics
- invent profits
- invent trading results
- fabricate screenshots
- fabricate testimonials
- use fake urgency
- use misleading claims

Do not write:

- title
- hashtags
- bullet points
- scene directions
- timestamps

Return ONLY the script using this exact format:

BOT:
[bot explanation]

CTA:
[CTA]
"""


def generate_script(
    topic: str,
    previous_topics=None
):

    api_key = None

    import os

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    client = genai.Client(
        api_key=api_key
    )

    previous = ", ".join(
        previous_topics or []
    )

    if not previous:
        previous = "None"

    prompt = f"""
{SYSTEM_PROMPT}

TOPIC:
{topic}

PREVIOUSLY USED TOPICS:
{previous}

Create a completely new script.

Do not repeat previous wording.

Remember:

42–48 words total.

BOT = approximately first half.

CTA = approximately second half.

The CTA must clearly tell viewers to tap the Related Video below
the title to watch the complete setup tutorial.

Return only:

BOT:
...

CTA:
...
"""

    last_error = None

    for attempt in range(3):

        try:

            print(
                f"Calling Gemini model: {MODEL_NAME}",
                flush=True
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=500,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="minimal"
                    ),
                ),
            )

            if not response.text:
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            raw = response.text.strip()

            print(
                "\n===== GEMINI RESPONSE =====",
                flush=True
            )

            print(
                raw,
                flush=True
            )

            print(
                "==========================",
                flush=True
            )

            if "BOT:" not in raw:
                raise RuntimeError(
                    "Gemini did not return BOT section."
                )

            if "CTA:" not in raw:
                raise RuntimeError(
                    "Gemini did not return CTA section."
                )

            bot_text = raw.split(
                "BOT:",
                1
            )[1].split(
                "CTA:",
                1
            )[0].strip()

            cta_text = raw.split(
                "CTA:",
                1
            )[1].strip()

            full_script = (
                f"{bot_text} {cta_text}"
            )

            word_count = len(
                full_script.split()
            )

            print(
                f"Generated {word_count} words.",
                flush=True
            )

            if word_count < 42:
                raise RuntimeError(
                    f"Script too short: "
                    f"{word_count} words."
                )

            if word_count > 48:
                raise RuntimeError(
                    f"Script too long: "
                    f"{word_count} words."
                )

            return {
                "bot": bot_text,
                "cta": cta_text,
                "full": full_script
            }

        except Exception as e:

            last_error = e

            print(
                f"Gemini attempt "
                f"{attempt + 1}/3 failed: {e}",
                flush=True
            )

            if attempt < 2:

                delay = 5 * (2 ** attempt)

                time.sleep(delay)

    raise RuntimeError(
        f"Gemini failed after 3 attempts: "
        f"{last_error}"
    )
