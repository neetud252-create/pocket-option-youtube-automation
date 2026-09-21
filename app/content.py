import os
import time

from google import genai
from google.genai import types


SYSTEM_PROMPT = """
You create short-form YouTube content for an AI trading-bot channel.

Create educational and demonstration-oriented YouTube Shorts.

Rules:
- Script length: approximately 20-35 seconds when spoken naturally.
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

    # Get the API key securely from Railway Variables.
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in Railway."
        )

    # Create Gemini client.
    client = genai.Client(api_key=api_key)

    previous = ", ".join(previous_topics or []) or "None"

    prompt = f"""
{SYSTEM_PROMPT}

Create one YouTube Short script.

Topic:
{topic}

Previously used topics:
{previous}

Important:
Do not reuse the same hook, explanation, or CTA from the previous topics.

Return ONLY the spoken script.
Do not include:
- title
- hashtags
- scene directions
- timestamps
- quotation marks
- labels
"""

    last_error = None

    # Retry temporary Gemini errors.
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

            if len(script) < 30:
                raise RuntimeError(
                    "Gemini returned a script that is too short."
                )

            return script

        except Exception as e:

            last_error = e

            print(
                f"Gemini attempt {attempt + 1}/3 failed: {e}",
                flush=True,
            )

            # Exponential backoff:
            # attempt 1 -> 5 seconds
            # attempt 2 -> 10 seconds
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
