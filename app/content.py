import os
import json
import random
import re

from google import genai

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL
)


# ============================================================
# STORAGE
# ============================================================

DATA_DIR = "/app/data"

HISTORY_FILE = os.path.join(
    DATA_DIR,
    "content_history.json"
)


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

        return {
            "scripts": [],
            "titles": []
        }

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return {
            "scripts": data.get(
                "scripts",
                []
            ),
            "titles": data.get(
                "titles",
                []
            )
        }

    except Exception as e:

        print(
            f"History load error: {e}",
            flush=True
        )

        return {
            "scripts": [],
            "titles": []
        }


# ============================================================
# SAVE HISTORY
# ============================================================

def save_history(
    history
):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    history["scripts"] = (
        history["scripts"][-200:]
    )

    history["titles"] = (
        history["titles"][-200:]
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
# FALLBACK CONTENT
# ============================================================

FALLBACK_CONTENT = [

    (
        "What happens when an AI trading bot studies "
        "the market instead of relying only on guesswork? "
        "It can organize chart information, identify "
        "patterns, and help you follow a defined strategy. "
        "Want to see the complete setup? Tap the Related "
        "Video below the title.",
        "Pocket Option AI Bot: How Does It Actually Work?"
    ),

    (
        "Reading a trading chart manually can take time. "
        "An AI trading bot can analyze price movement "
        "and organize the information into a clearer "
        "trading setup. The important part is using signals "
        "with proper risk management. See the full setup "
        "in the Related Video.",
        "Pocket Option AI Trading Bot Explained"
    ),

    (
        "Can AI help organize a Pocket Option trading setup? "
        "An AI bot can analyze chart data, look for patterns, "
        "and present information in a structured way. "
        "It does not remove trading risk, so risk management "
        "still matters. Watch the Related Video for the "
        "complete setup.",
        "Pocket Option AI Bot Trading Setup"
    ),

    (
        "Instead of watching every candle manually, an AI "
        "trading system can help analyze price movement "
        "and chart patterns in a structured process. "
        "The goal is consistency, not guessing. "
        "Tap the Related Video below the title to see "
        "the complete bot setup.",
        "Pocket Option AI Trading Bot: Complete Setup"
    ),

    (
        "One interesting use of AI in trading is automated "
        "chart analysis. The system can examine price "
        "movement and patterns and organize the information "
        "for a trader. Always consider risk before trading. "
        "Watch the Related Video to see how the setup works.",
        "Pocket Option AI Bot: AI Chart Analysis"
    ),

    (
        "AI trading tools can help turn large amounts of "
        "chart information into a more structured process. "
        "A Pocket Option AI bot can analyze patterns and "
        "price movement, while the trader still controls "
        "risk and execution. Watch the Related Video for "
        "the complete setup.",
        "Pocket Option AI Trading Bot: Market Analysis"
    ),

    (
        "Why are traders exploring AI for chart analysis? "
        "An AI trading bot can process price movement and "
        "patterns quickly and organize them into signals "
        "or trading information. AI does not eliminate risk. "
        "See the complete setup in the Related Video.",
        "Pocket Option AI Bot: AI Market Analysis"
    ),

    (
        "A trading bot is not just about automation. "
        "It can also organize chart analysis into a repeatable "
        "process. With a Pocket Option AI bot, market data "
        "and patterns can be analyzed systematically. "
        "Watch the Related Video to see the setup.",
        "Pocket Option AI Trading Bot: How It Analyzes Charts"
    ),

    (
        "Candlestick charts contain a lot of information. "
        "An AI trading bot can help analyze price movement "
        "and recognize patterns in a structured way. "
        "Risk management is still essential when trading. "
        "Tap the Related Video for the full tutorial.",
        "Pocket Option AI Bot: Candlestick Analysis"
    ),

    (
        "What can an AI trading bot actually analyze? "
        "It can process chart data, price movement, and "
        "technical patterns to organize information for "
        "a trading setup. It cannot guarantee a result. "
        "See the complete Pocket Option setup in the "
        "Related Video.",
        "Pocket Option AI Trading Bot: What It Analyzes"
    )

]


# ============================================================
# CLEAN GEMINI RESPONSE
# ============================================================

def clean_response(
    text
):

    text = text.strip()

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    return text.strip()


# ============================================================
# GEMINI GENERATOR
# ============================================================

def generate_with_gemini(
    history
):

    if not GEMINI_API_KEY:

        print(
            "GEMINI_API_KEY not configured.",
            flush=True
        )

        return None

    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        previous_titles = "\n".join(
            history["titles"][-30:]
        )

        previous_scripts = "\n".join(
            history["scripts"][-20:]
        )

        prompt = f"""
Create ONE completely original YouTube Shorts script
about Pocket Option AI Bot or Pocket Option AI Trading Bot.

This is for an educational short-form channel.

IMPORTANT:
- Make this script substantially different from all
  previous scripts.
- Do not reuse previous wording.
- Use a different hook.
- Use a different explanation angle.
- Use different sentence structure.
- Do not repeat previous titles.

Do NOT:
- guarantee profits
- guarantee accurate signals
- claim guaranteed winning trades
- invent earnings
- fabricate trading results
- claim AI removes trading risk

The script should be approximately 35-55 words.

The script should contain:
1. A strong curiosity-based opening.
2. Useful information about the AI trading bot.
3. A natural explanation.
4. A short CTA to the full tutorial.

The title MUST naturally contain one of these:
- Pocket Option AI Bot
- Pocket Option AI Trading Bot

Return ONLY valid JSON:

{{
  "title": "unique title here",
  "script": "unique script here"
}}

PREVIOUS TITLES:
{previous_titles}

PREVIOUS SCRIPTS:
{previous_scripts}
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        raw = response.text

        if not raw:

            return None

        raw = clean_response(
            raw
        )

        data = json.loads(
            raw
        )

        title = str(
            data.get(
                "title",
                ""
            )
        ).strip()

        script = str(
            data.get(
                "script",
                ""
            )
        ).strip()

        if not title:

            return None

        if not script:

            return None

        # ----------------------------------------------------
        # CHECK TITLE
        # ----------------------------------------------------

        existing_titles = [
            x.lower().strip()
            for x in history["titles"]
        ]

        if title.lower().strip() in existing_titles:

            print(
                "Gemini returned a duplicate title.",
                flush=True
            )

            return None

        # ----------------------------------------------------
        # CHECK SCRIPT
        # ----------------------------------------------------

        existing_scripts = [
            x.lower().strip()
            for x in history["scripts"]
        ]

        if script.lower().strip() in existing_scripts:

            print(
                "Gemini returned a duplicate script.",
                flush=True
            )

            return None

        return {
            "title": title,
            "script": script
        }

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

        return None


# ============================================================
# MAIN CONTENT GENERATOR
# ============================================================

def generate_content():

    history = load_history()

    # --------------------------------------------------------
    # TRY GEMINI
    # --------------------------------------------------------

    generated = generate_with_gemini(
        history
    )

    if generated:

        title = generated[
            "title"
        ]

        script = generated[
            "script"
        ]

        print(
            "\nUsing NEW Gemini-generated content.",
            flush=True
        )

    else:

        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------

        used_titles = [
            x.lower().strip()
            for x in history["titles"]
        ]

        available = [

            item
            for item in FALLBACK_CONTENT

            if item[1].lower().strip()
            not in used_titles
        ]

        if not available:

            available = (
                FALLBACK_CONTENT
            )

        script, title = random.choice(
            available
        )

        print(
            "\nUsing unique fallback content.",
            flush=True
        )

    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    history["scripts"].append(
        script
    )

    history["titles"].append(
        title
    )

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
        f"TITLE:\n{title}",
        flush=True
    )

    print(
        f"\nSCRIPT:\n{script}",
        flush=True
    )

    print(
        f"\nScript words: "
        f"{len(script.split())}",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    return {
        "title": title,
        "script": script
    }
