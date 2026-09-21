import os
import time

from google import genai
from google.genai import types


# Gemini model recommended by the error returned from your API
MODEL_NAME = "gemini-3.5-flash"


SYSTEM_PROMPT = """
You create short-form YouTube content for an AI trading-bot channel.

The main purpose of every Short is to attract genuinely interested viewers
and send them to ONE longer YouTube tutorial on the same channel.

The longer tutorial explains how to use the AI trading bot for trading.
The Short should create curiosity about the tutorial without making false
claims or promising financial results.

CONTENT RULES:

- Write approximately 55-80 spoken words.
- Target around 20-35 seconds when spoken naturally.
- Start with a strong hook in the first sentence.
- Focus on ONE clear topic.
- Explain something useful about AI-assisted trading, chart analysis,
  indicators, trading psychology, automation, or how the bot works.
- Make the Short valuable by itself.
- Create curiosity about the complete bot setup and workflow.
- Do not explain the entire tutorial inside the Short.
- Give viewers a natural reason to watch the related tutorial.
- Use simple, natural spoken English.
- Sound like a human creator, not a robotic advertisement.
- Vary sentence structure, hooks, explanations, and CTA wording.

TRADING SAFETY:

- Never promise profits.
- Never guarantee winning trades.
- Never claim the bot cannot lose.
- Never claim a specific win rate unless verified information is provided.
- Never invent trading results.
- Never fabricate screenshots, statistics, earnings, testimonials,
  or performance data.
- Never imply viewers will definitely make money.
- Do not use fake urgency.
- Do not use misleading clickbait.

CTA:

The final sentence should naturally direct interested viewers toward
the related long-form tutorial.

The CTA should NOT make "subscribe" the main action.

Use varied CTA styles such as:

- "I've explained the complete setup in the related video."
- "Want to see the full process? Check the related tutorial."
- "The complete bot setup is explained in the related video."
- "If you want to see how this works step by step, open the related video."
- "I've covered the full setup in the tutorial linked to this Short."

Do not repeat the same CTA every time.

FUNNEL:

SHORT
→ viewer becomes interested
→ viewer opens the YouTube Related Video
→ viewer watches the longer tutorial
→ tutorial explains how to use the bot

The Short must NOT falsely claim that the tutorial guarantees profits
or successful trades.

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

Create ONE YouTube Short script.

TOPIC:
{topic}

PREVIOUSLY USED TOPICS:
{previous}

STRUCTURE:

1. HOOK
Immediately give the viewer a reason to keep watching.

2. EXPLANATION
Explain one useful and interesting concept related to the topic.

3. CURIOSITY
Create natural curiosity about how the complete bot setup or workflow
works.

4. CTA
Direct interested viewers to the related long-form tutorial.

The related tutorial explains how to use the AI trading bot for trading.

The CTA should feel like a natural continuation of the Short,
not an advertisement.

IMPORTANT:

- Do not repeat previous topics.
- Do not use the same opening sentence repeatedly.
- Do not use the same CTA wording repeatedly.
- Do not mention "this video will make you money".
- Do not mention guaranteed profits.
- Do not invent numbers or results.
- Do not include a title.
- Do not include hashtags.
- Do not include scene directions.
- Do not include timestamps.
- Do not include quotation marks around the script.
- Do not include labels such as Hook, Explanation, or CTA.
- Do not use bullet points.

Write approximately 55-80 words.

Return ONLY the spoken script.
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
                    max_output_tokens=300
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

            if word_count < 35:
                raise RuntimeError(
                    f"Gemini returned only {word_count} words. "
                    "Expected at least 35 words."
                )

            if word_count > 100:
                raise RuntimeError(
                    f"Gemini returned {word_count} words. "
                    "Expected approximately 55-80 words."
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
