import os
import time

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.5-flash"


SYSTEM_PROMPT = """
You are an expert YouTube Shorts scriptwriter.

Create short educational YouTube Shorts for an AI trading-bot channel.

The purpose of each Short is to attract interested viewers and send them
to one longer YouTube tutorial through the YouTube Related Video feature.

The longer tutorial explains how to use the AI trading bot for trading.

IMPORTANT WRITING RULES:

- The script MUST contain 55 to 80 words.
- Write approximately 65 words.
- Never write fewer than 55 words.
- Use natural spoken English.
- The script should sound like a real human creator.
- Start with a strong hook.
- Explain ONE useful concept.
- Give the viewer a useful takeaway.
- Create curiosity about the complete bot setup.
- End with a natural CTA toward the related tutorial.
- Do not explain the entire tutorial in the Short.
- Do not use the word "subscribe" as the main CTA.
- Vary hooks and CTA wording between scripts.

TRADING SAFETY:

- Never promise profits.
- Never guarantee winning trades.
- Never claim guaranteed signals.
- Never claim the bot cannot lose.
- Never invent win rates.
- Never invent profits or results.
- Never fabricate screenshots or statistics.
- Never imply viewers will definitely make money.
- Do not use fake urgency.
- Do not use misleading clickbait.

Return ONLY the spoken script.
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
    ) or "None"

    prompt = f"""
{SYSTEM_PROMPT}

Create ONE YouTube Short script about:

{topic}

Previously used topics:
{previous}

The script MUST follow this exact structure:

HOOK:
Start with an interesting question, surprising observation,
or strong statement.

EXPLANATION:
Explain one useful concept about AI trading bots,
chart analysis, indicators, automation, or trading.

TAKEAWAY:
Give the viewer one useful thing they can understand or remember.

CTA:
Direct interested viewers to the related long-form tutorial,
where the complete bot setup and usage is explained.

WORD COUNT REQUIREMENT:

Write between 55 and 80 words.

TARGET: approximately 65 words.

IMPORTANT:
Do NOT stop after one sentence.
Do NOT summarize the topic in one sentence.
Complete all four parts naturally in one spoken paragraph.

Do not include:
- title
- hashtags
- labels
- bullet points
- timestamps
- scene directions
- quotation marks

Return ONLY the complete spoken script.
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
                    temperature=0.8,
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
