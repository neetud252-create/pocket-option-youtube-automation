import json
import os
import random
import re
import time

import requests


# ============================================================
# CONFIG
# ============================================================

HISTORY_FILE = "/app/data/content_history.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

MIN_SCRIPT_WORDS = 30
MAX_SCRIPT_WORDS = 60
MAX_HISTORY = 1000
GEMINI_ATTEMPTS = 4


# ============================================================
# FALLBACK CONTENT
# ============================================================

FALLBACK_CONTENT = [
    {
        "title": "Pocket Option AI Bot Chart Analysis Explained",
        "script": (
            "The Pocket Option AI Bot can review chart movement and organize market "
            "information into a clearer analysis workflow. It looks for patterns and "
            "possible setups automatically, while the user still reviews the market "
            "conditions before making an independent trading decision."
        ),
    },
    {
        "title": "Pocket Option AI Trading Bot Market Scanner",
        "script": (
            "A Pocket Option AI Trading Bot can work like a market scanner by checking "
            "chart data for patterns and signals. This reduces repetitive monitoring "
            "and gives users a structured set of observations they can review as part "
            "of their own market research."
        ),
    },
    {
        "title": "Pocket Option AI Bot Candlestick Analysis",
        "script": (
            "Candlestick patterns can provide useful context when studying price action. "
            "The Pocket Option AI Bot can process those patterns alongside other market "
            "information, helping users organize their analysis and identify areas that "
            "may deserve a closer review."
        ),
    },
    {
        "title": "Pocket Option AI Trading Bot Signal Review",
        "script": (
            "Trading signals are more useful when they are reviewed with broader market "
            "context. The Pocket Option AI Trading Bot can organize signal information, "
            "chart movement, and patterns so users have a more structured starting point "
            "for their own analysis."
        ),
    },
    {
        "title": "Pocket Option AI Bot Technical Indicator Workflow",
        "script": (
            "Technical indicators can add context to a chart, but they still need careful "
            "interpretation. The Pocket Option AI Bot can process indicator information "
            "alongside price movement and patterns, helping users review a potential setup "
            "in a more organized way."
        ),
    },
    {
        "title": "Pocket Option AI Bot Automated Market Monitoring",
        "script": (
            "Continuous chart monitoring can become repetitive during an active market. "
            "The Pocket Option AI Bot can automate part of that work by processing market "
            "information and highlighting patterns for review, while the final trading "
            "decision remains with the user."
        ),
    },
    {
        "title": "Pocket Option AI Trading Bot Pattern Detection",
        "script": (
            "Pattern detection is one task that automated tools can handle consistently. "
            "A Pocket Option AI Trading Bot can scan chart information for recognizable "
            "structures and possible setups, giving users another source of information "
            "to compare with their own analysis."
        ),
    },
    {
        "title": "Pocket Option AI Bot Price Action Research",
        "script": (
            "Price action can change quickly, which makes manual monitoring difficult. "
            "The Pocket Option AI Bot can process chart movement and organize possible "
            "patterns into a research workflow, helping users review market conditions "
            "without relying on a single signal alone."
        ),
    },
    {
        "title": "Pocket Option AI Trading Bot Analysis Workflow",
        "script": (
            "A structured workflow can make market research easier to follow. The Pocket "
            "Option AI Trading Bot can examine chart data, identify patterns, and organize "
            "possible setups so users can review the information before deciding whether "
            "any trade idea is worth considering."
        ),
    },
    {
        "title": "Pocket Option AI Bot Market Data Review",
        "script": (
            "Market data contains many small changes that can be difficult to follow "
            "manually. The Pocket Option AI Bot can process that information and highlight "
            "patterns for further review, giving users a more organized way to study "
            "current chart conditions."
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
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

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
    temp_file = HISTORY_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            history,
            file,
            indent=2,
            ensure_ascii=False,
        )

    os.replace(temp_file, HISTORY_FILE)


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

def extract_final_text(data):
    try:
        candidate = data["candidates"][0]
    except Exception as exc:
        raise RuntimeError(
            f"Gemini response has no candidate: {str(data)[:1000]}"
        ) from exc

    finish_reason = candidate.get("finishReason")

    if finish_reason == "MAX_TOKENS":
        raise RuntimeError(
            "Gemini hit MAX_TOKENS before finishing the response."
        )

    parts = candidate.get("content", {}).get("parts", [])

    final_parts = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("thought") is True:
            continue
        text = part.get("text")
        if text:
            final_parts.append(text)

    if not final_parts:
        raise RuntimeError(
            "Gemini response did not contain final generated text."
        )

    return "".join(final_parts).strip()


def generate_with_gemini(history):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    # Keep the prompt compact. Full duplicate protection still uses all
    # stored history after generation.
    recent_titles = [
        item.get("title", "")
        for item in history[-30:]
        if isinstance(item, dict) and item.get("title")
    ]

    recent_scripts = [
        item.get("script", "")
        for item in history[-20:]
        if isinstance(item, dict) and item.get("script")
    ]

    recent_titles_text = "\n".join(
        f"- {title}" for title in recent_titles
    )
    recent_scripts_text = "\n".join(
        f"- {script}" for script in recent_scripts
    )

    prompt = f"""
Create ONE new YouTube Short title and ONE new spoken script about a
Pocket Option AI Bot.

RULES:
- The title must naturally contain exactly one of these keyword phrases:
  "Pocket Option AI Bot" or "Pocket Option AI Trading Bot".
- The title should be useful, specific, and different from prior titles.
- The spoken script must be 30 to 55 words.
- Use simple, natural spoken English.
- Focus on one educational topic such as chart analysis, market analysis,
  signals, candlestick patterns, technical indicators, automated analysis,
  market monitoring, trading technology, or bot workflow.
- Do not promise profits, guaranteed outcomes, accuracy, win rates, or income.
- Do not invent statistics.
- Do not include any call to action.
- Do not mention a link, bio, channel description, activation button, or
  related video.
- Make the title and script genuinely different from the recent content.

RECENT TITLES TO AVOID:
{recent_titles_text or "None"}

RECENT SCRIPTS TO AVOID:
{recent_scripts_text or "None"}
"""

    # Gemini 3.x thinking tokens count toward maxOutputTokens. A larger cap
    # plus low thinking prevents the truncated JSON seen with a 300-token cap.
    # Structured output makes the final response valid JSON by contract.
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "thinkingConfig": {
                "thinkingLevel": "low"
            },
            "responseFormat": {
                "text": {
                    "mimeType": "application/json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Unique YouTube Short title"
                            },
                            "script": {
                                "type": "string",
                                "description": "30 to 55 word spoken script"
                            }
                        },
                        "required": ["title", "script"]
                    }
                }
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    print(
        f"Using Gemini model: {GEMINI_MODEL}",
        flush=True,
    )

    try:
        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=90,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Gemini connection failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            "Gemini API error "
            f"{response.status_code}: "
            f"{response.text[:1500]}"
        )

    data = response.json()
    generated_text = clean_json_text(extract_final_text(data))

    try:
        result = json.loads(generated_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid structured JSON: "
            f"{generated_text[:1500]}"
        ) from exc

    title = str(result.get("title", "")).strip()
    script = str(result.get("script", "")).strip()

    return title, script


# ============================================================
# FALLBACK SELECTION
# ============================================================

def get_unused_fallback(history):
    used_titles = get_used_titles(history)
    used_scripts = get_used_scripts(history)

    unused = [
        item
        for item in FALLBACK_CONTENT
        if normalize_text(item["title"]) not in used_titles
        and normalize_text(item["script"]) not in used_scripts
    ]

    if not unused:
        return None

    return random.choice(unused)


def create_unique_fallback_variant(history):
    used_titles = get_used_titles(history)
    used_scripts = get_used_scripts(history)

    topics = [
        ("Chart Monitoring", "chart monitoring and price movement"),
        ("Market Research", "market research and structured chart review"),
        ("Pattern Scanner", "pattern scanning and technical chart information"),
        ("Indicator Review", "technical indicators and market context"),
        ("Signal Analysis", "signal analysis and broader chart conditions"),
        ("Price Action", "price action and automated market review"),
        ("Trend Review", "trend review and changing market conditions"),
        ("Data Analysis", "market data and automated chart analysis"),
    ]

    angles = [
        "Workflow",
        "Explained",
        "Research Guide",
        "Analysis Method",
        "Review Process",
        "Technology Overview",
    ]

    combinations = [
        (topic_name, topic_description, angle)
        for topic_name, topic_description in topics
        for angle in angles
    ]
    random.shuffle(combinations)

    for topic_name, topic_description, angle in combinations:
        title = f"Pocket Option AI Bot {topic_name} {angle}"
        script = (
            f"This Pocket Option AI Bot workflow focuses on {topic_description}. "
            "It can process chart information and organize patterns automatically, "
            "giving users a clearer set of observations to review as part of their "
            "own research before making an independent trading decision."
        )

        if (
            normalize_text(title) not in used_titles
            and normalize_text(script) not in used_scripts
        ):
            return title, script

    # Last-resort uniqueness if all natural combinations have been used.
    for number in range(1, 10001):
        title = f"Pocket Option AI Bot Market Review #{number}"
        script = (
            f"This Pocket Option AI Bot market review looks at automated chart "
            f"analysis from research angle {number}. The system organizes market "
            "information and patterns for review, helping users compare observations "
            "before making their own independent trading decisions."
        )

        if (
            normalize_text(title) not in used_titles
            and normalize_text(script) not in used_scripts
        ):
            return title, script

    raise RuntimeError("Could not create a unique fallback.")


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

    print(f"\nSaved to content history:\n{HISTORY_FILE}", flush=True)
    print(f"\nFINAL TITLE:\n{title}", flush=True)
    print(f"\nFINAL SCRIPT:\n{script}", flush=True)

    return title.strip(), script.strip()


# ============================================================
# MAIN CONTENT GENERATOR
# ============================================================

def generate_content():
    print("\n==========================================", flush=True)
    print("GENERATING UNIQUE CONTENT", flush=True)
    print("==========================================", flush=True)

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

            print(f"Generated title: {title}", flush=True)
            print(f"Script words: {word_count(script)}", flush=True)

            valid, reason = validate_content(title, script)

            if not valid:
                print(f"Rejected: {reason}", flush=True)
                continue

            if is_duplicate(title, script, history):
                print(
                    "Rejected: duplicate title or script.",
                    flush=True,
                )
                continue

            print("\nNEW UNIQUE CONTENT ACCEPTED", flush=True)
            return save_new_content(title, script, history)

        except Exception as exc:
            print(
                f"Gemini attempt failed: {exc}",
                flush=True,
            )

            if attempt < GEMINI_ATTEMPTS:
                time.sleep(2)

    print(
        "\nGemini could not produce valid unique content; using fallback.",
        flush=True,
    )

    fallback = get_unused_fallback(history)

    if fallback:
        title = fallback["title"]
        script = fallback["script"]
    else:
        title, script = create_unique_fallback_variant(history)

    valid, reason = validate_content(title, script)

    if not valid:
        raise RuntimeError(
            f"Fallback content failed validation: {reason}"
        )

    if is_duplicate(title, script, history):
        raise RuntimeError("Fallback content is still duplicated.")

    print("\nUNIQUE FALLBACK ACCEPTED", flush=True)
    print(f"Title: {title}", flush=True)
    print(f"Words: {word_count(script)}", flush=True)

    return save_new_content(title, script, history)
