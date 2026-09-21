import os
import time

from google import genai
from google.genai import types


SYSTEM_PROMPT = """
You create short-form YouTube content for an AI trading-bot channel.

Create educational and demonstration-oriented YouTube Shorts.

Rules:
- Script should be approximately 20-35 seconds when spoken naturally.
- Target approximately 55-80 words.
- Start with a strong hook.
- Use simple, natural spoken English.
- Explain ONE clear topic per Short.
- Make the script engaging without using fake claims.
- Do not promise guaranteed profits.
- Do not claim guaranteed winning signals.
- Do not invent trading results.
- Do not fabricate screenshots, statistics, or performance.
- Do not imply that viewers will definitely make money.
- Keep trading explanations educational.
- End with a short natural CTA.
- Avoid repeating previously used topics.
- Return only the spoken script.
"""


def generate_script(topic: str, previous_topics=None) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in Railway."
        )

    client = genai.Client(api_key=api_key)

    previous = ", ".join(previous_topics or []) or "None"

    prompt = f"""
{SYSTEM_PROMPT}

Create one YouTube Short script.

Topic:
{topic}

Previously used topics:
{previous}

The script must be approximately 55-80 words.

Important:
- Do not reuse the same hook, explanation, or CTA from previous topics.
- Do not include a title.
- Do not include hashtags.
- Do not include scene directions.
- Do not include timestamps.
- Do not include quotation marks.
- Do not include labels.

Return ONLY the spoken script.
"""

    last_error = None

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=180,
                    candidate_count=1,
                ),
            )

            if not response.text:
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            script = response.text.strip()

            word_count = len(script.split())

            print(
                f"Gemini generated {word_count} words.",
                flush=True,
            )

            if word_count < 35:
                raise RuntimeError(
                    f"Gemini returned only {word_count} words. "
                    "Expected at least 35 words."
                )

            return script

        except Exception as e:

            last_error = e

            print(
                f"Gemini attempt {attempt + 1}/3 failed: {e}",
                flush=True,
            )

            if attempt < 2:

                delay = 5 * (2 ** attempt)

                print(
                    f"Retrying Gemini in {delay} seconds...",
                    flush=True,
                )

                time.sleep(delay)

    raise RuntimeError(
        f"Gemini failed after 3 attempts: {last_error}"
    )
