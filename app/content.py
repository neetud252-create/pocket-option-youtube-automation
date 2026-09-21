import os
import time

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.5-flash"


SYSTEM_PROMPT = """
You are a professional YouTube Shorts scriptwriter.

Write a COMPLETE spoken script for an educational YouTube Short about
an AI trading bot.

The Short is designed to send interested viewers to ONE longer tutorial
through YouTube's Related Video feature.

The longer tutorial explains how to use the AI trading bot for trading.

STRICT LENGTH:
The final script MUST contain 55 to 80 words.
Target approximately 65 words.

Write ONE natural paragraph.

The script must contain:

1. A strong hook.
2. A useful explanation of ONE concept.
3. A practical takeaway.
4. A natural transition toward the related tutorial.

The final sentence should encourage interested viewers to open the
related tutorial.

Use natural spoken English.

Vary the hook and CTA between scripts.

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
- use misleading clickbait
- make financial guarantees

Do not write a title.
Do not write hashtags.
Do not write bullet points.
Do not write labels.
Do not write scene directions.
Do not write timestamps.
Do not put the script inside quotation marks.

Return ONLY the complete spoken script.
"""


def generate_script(topic: str, previous_topics=None) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in Railway."
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

Now write the complete Short.

IMPORTANT:
Do not give me an outline.
Do not give me a summary.
Do not give me instructions about writing.

I need the FINAL spoken script itself.

The final answer must be between 55 and 80 words.
Target approximately 65 words.

Write the complete script now.
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
                    max_output_tokens=1000,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="minimal"
                    ),
                ),
            )

            if not response.text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            script = response.text.strip()

            word_count = len(
                script.split()
            )

            print(
                f"Gemini generated {word_count} words.",
                flush=True
            )

            print(
                f"Gemini script: {script}",
                flush=True
            )

            if word_count < 55:

                raise RuntimeError(
                    f"Gemini returned only {word_count} words. "
                    "Expected 55-80 words."
                )

            if word_count > 80:

                raise RuntimeError(
                    f"Gemini returned {word_count} words. "
                    "Expected 55-80 words."
                )

            return script

        except Exception as e:

            last_error = e

            print(
                f"Gemini attempt {attempt + 1}/3 failed: {e}",
                flush=True
            )

            if attempt < 2:

                delay = 5 * (2 ** attempt)

                print(
                    f"Retrying Gemini in {delay} seconds...",
                    flush=True
                )

                time.sleep(delay)

    raise RuntimeError(
        f"Gemini failed after 3 attempts: {last_error}"
    )
