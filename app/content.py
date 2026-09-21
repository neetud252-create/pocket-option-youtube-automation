import os
from openai import OpenAI


SYSTEM_PROMPT = """
You create short-form YouTube content for an AI trading-bot channel.

Create educational/demo-oriented YouTube Shorts.

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


def generate_script(topic: str, previous_topics: list[str] | None = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)

    previous = ", ".join(previous_topics or []) or "None"

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        instructions=SYSTEM_PROMPT,
        input=f"""
Create one YouTube Short script.

Topic:
{topic}

Previously used topics:
{previous}

Return only the spoken script.
""",
    )

    return response.output_text.strip()
