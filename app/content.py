import os
import json
import random

from google import genai

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
)


DATA_DIR = "/app/data"

HISTORY_FILE = os.path.join(
    DATA_DIR,
    "content_history.json"
)


# ============================================================
# FALLBACK CONTENT
# ============================================================

FALLBACK_CONTENT = [

    {
        "title": "Pocket Option AI Bot: How Does It Work?",
        "script": (
            "What happens when an AI trading bot studies "
            "market information instead of relying only on guesswork? "
            "It can organize chart data, identify patterns, "
            "and help you follow a defined trading strategy."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Explained",
        "script": (
            "An AI trading bot can help organize market information "
            "and analyze chart patterns in a structured way. "
            "Instead of manually checking every detail, "
            "the system can process information and present "
            "it in a more organized trading workflow."
        )
    },

    {
        "title": "Pocket Option AI Bot: What Does It Analyze?",
        "script": (
            "How can an AI bot analyze a trading chart? "
            "It can process market information, study patterns, "
            "and organize signals into a structured workflow. "
            "The goal is to make analysis more systematic "
            "rather than relying entirely on emotions."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot: Quick Breakdown",
        "script": (
            "Pocket Option AI trading bots can be used to organize "
            "chart analysis and market information. "
            "They can examine patterns and help structure "
            "a trading workflow, while risk management "
            "still remains an important part of trading."
        )
    },

    {
        "title": "Pocket Option AI Bot: How AI Helps Trading",
        "script": (
            "AI can process large amounts of market information "
            "and organize it into a structured analysis. "
            "A Pocket Option AI bot can use these tools "
            "to help study charts and patterns while keeping "
            "the trading process more systematic."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot: See How It Works",
        "script": (
            "Instead of manually studying every chart detail, "
            "an AI trading bot can help organize market data "
            "and identify patterns. This can make the analysis "
            "process more structured, although trading still "
            "involves risk."
        )
    },

]


# ============================================================
# LOAD HISTORY
# ============================================================

def load_history():

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    if not os.path.exists(
        HISTORY_FILE
    ):
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception as e:

        print(
            f"Could not load content history: {e}",
            flush=True
        )

        return []


# ============================================================
# SAVE HISTORY
# ============================================================

def save_history(history):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    return " ".join(
        str(text)
        .strip()
        .split()
    )


# ============================================================
# VALIDATE GENERATED CONTENT
# ============================================================

def validate_content(title, script):

    title = normalize_text(title)
    script = normalize_text(script)

    if not title:
        return False

    if not script:
        return False

    # Required title wording
    title_lower = title.lower()

    if (
        "pocket option ai bot" not in title_lower
        and
        "pocket option ai trading bot" not in title_lower
    ):
        return False

    # Never allow unwanted CTA wording
    forbidden_phrases = [
        "related video",
        "tap the related",
        "click the related",
        "below the title",
        "link in bio",
        "bot activation button",
        "channel description",
    ]

    script_lower = script.lower()

    for phrase in forbidden_phrases:

        if phrase in script_lower:
            return False

    # Keep scripts short enough for Shorts
    words = script.split()

    if len(words) < 30:
        return False

    if len(words) > 60:
        return False

    return True


# ============================================================
# FALLBACK
# ============================================================

def get_fallback_content(history):

    used_titles = {
        item.get("title", "").strip().lower()
        for item in history
        if isinstance(item, dict)
    }

    available = [
        item
        for item in FALLBACK_CONTENT
        if item["title"].strip().lower()
        not in used_titles
    ]

    if not available:
        available = FALLBACK_CONTENT

    selected = random.choice(
        available
    )

    return {
        "title": selected["title"],
        "script": selected["script"]
    }


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_with_gemini(history):

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    recent_titles = []

    for item in history[-20:]:

        if isinstance(item, dict):

            title = item.get(
                "title"
            )

            if title:
                recent_titles.append(
                    title
                )

    previous_titles_text = "\n".join(
        f"- {title}"
        for title in recent_titles
    )

    prompt = f"""
Create ONE YouTube Shorts script about the Pocket Option AI Bot.

IMPORTANT RULES:

1. The title MUST contain either:
   "Pocket Option AI Bot"
   OR
   "Pocket Option AI Trading Bot"

2. Script must be 30 to 55 words.

3. Make the script educational and natural.

4. Explain AI trading bot functionality, chart analysis,
   market information, patterns, or structured trading workflows.

5. Do NOT make guaranteed profit claims.

6. Do NOT claim guaranteed accuracy.

7. Do NOT mention earnings as guaranteed results.

8. Do NOT include a CTA.

9. Do NOT mention:
   - Related Video
   - video below the title
   - link in bio
   - channel description
   - Bot Activation button

10. Do NOT use emojis.

11. Return ONLY valid JSON.

Required JSON format:

{{
  "title": "Pocket Option AI Bot: Example Title",
  "script": "30 to 55 word educational script here."
}}

Previously used titles:
{previous_titles_text}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    text = response.text.strip()

    # Remove markdown fences if Gemini adds them
    if text.startswith("```"):

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()

    data = json.loads(
        text
    )

    title = data.get(
        "title",
        ""
    )

    script = data.get(
        "script",
        ""
    )

    if not validate_content(
        title,
        script
    ):

        raise RuntimeError(
            "Gemini generated invalid content."
        )

    return {
        "title": normalize_text(title),
        "script": normalize_text(script)
    }


# ============================================================
# MAIN CONTENT FUNCTION
# ============================================================

def generate_content():

    history = load_history()

    print(
        "\n===== CONTENT GENERATION =====",
        flush=True
    )

    print(
        f"Model: {GEMINI_MODEL}",
        flush=True
    )

    try:

        result = generate_with_gemini(
            history
        )

        print(
            "Gemini generation successful.",
            flush=True
        )

    except Exception as e:

        print(
            "\n===== GEMINI GENERATION ERROR =====",
            flush=True
        )

        print(
            str(e),
            flush=True
        )

        print(
            "Using fallback content.",
            flush=True
        )

        result = get_fallback_content(
            history
        )

    # --------------------------------------------------------
    # FINAL SAFETY CHECK
    # --------------------------------------------------------

    if not validate_content(
        result["title"],
        result["script"]
    ):

        print(
            "Generated content failed validation.",
            flush=True
        )

        print(
            "Using fallback content.",
            flush=True
        )

        result = get_fallback_content(
            history
        )

    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    history.append(
        {
            "title": result["title"],
            "script": result["script"]
        }
    )

    # Keep history manageable
    if len(history) > 100:
        history = history[-100:]

    save_history(
        history
    )

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60,
        flush=True
    )

    print(
        "NEW SHORT CONTENT",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    print(
        f"Model: {GEMINI_MODEL}",
        flush=True
    )

    print(
        "\nTITLE:",
        flush=True
    )

    print(
        result["title"],
        flush=True
    )

    print(
        "\nSCRIPT:",
        flush=True
    )

    print(
        result["script"],
        flush=True
    )

    print(
        f"\nScript words: "
        f"{len(result['script'].split())}",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    return result
