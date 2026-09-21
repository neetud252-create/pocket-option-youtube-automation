import os
from google import genai


SYSTEM_PROMPT = """
You create short-form YouTube content for an AI trading-bot channel.

Create educational and demonstration-oriented YouTube Shorts.

Rules:
- 20-35 seconds
- Strong hook in the first sentence
- Simple spoken English
- Explain one topic clearly
- Do not promise guaranteed profits
- Do not claim guaranteed winning signals
- Do not invent trading results
- Do not fabricate screenshots or performance
- End with a short CTA
- Avoid repeating previously used topics
"""


def generate_script(topic: str, previous_topics=None) -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    previous = ", ".join(previous_topics or []) or "None"

    prompt = f"""
{SYSTEM_PROMPT}

Create one YouTube Short script.

Topic:
{topic}

Previously used topics:
{previous}

Return ONLY the spoken script.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text.strip()
