import json
import os
import random
import re
import time
from difflib import SequenceMatcher

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

# Slightly longer scripts keep the first 20 seconds active at normal-fast
# ElevenLabs speed instead of stretching a short script and making it sound slow.
MIN_SCRIPT_WORDS = 50
MAX_SCRIPT_WORDS = 66
MAX_HISTORY = 1000
GEMINI_ATTEMPTS = 6

TITLE_KEYWORDS = [
    "Pocket Option AI Trading Bot",
    "Pocket Option AI Trading",
    "Bot for Pocket Option",
    "Pocket Option Bot",
]

TITLE_SIMILARITY_LIMIT = 0.90
SCRIPT_SIMILARITY_LIMIT = 0.80
SIMILARITY_HISTORY_WINDOW = 180


# ============================================================
# RETENTION-STYLE FALLBACK BUILDING BLOCKS
# ============================================================

FALLBACK_ANGLES = [
    (
        "Fast Momentum Scan",
        "Momentum can flip before the chart looks obvious. "
        "The bot compares recent price speed, candle behavior, and trend direction "
        "so the change is easier to spot while the move is still developing."
    ),
    (
        "Candlestick Pattern Check",
        "Candles tell a story when you read them together. "
        "The bot scans recent candle shapes, direction, and reactions around key areas "
        "to highlight patterns that deserve a closer look."
    ),
    (
        "Support and Resistance Scan",
        "Key levels matter because price often reacts around them. "
        "The bot maps recent support and resistance areas, then compares current movement "
        "to those zones so the chart is easier to read."
    ),
    (
        "Trend Strength Review",
        "A trend can look strong while momentum is already fading. "
        "The bot checks direction, recent swings, and supporting indicators "
        "to show whether the move still has structure behind it."
    ),
    (
        "Price Action Breakdown",
        "Price action changes fast, and tiny shifts can matter. "
        "The bot organizes recent highs, lows, candle reactions, and movement speed "
        "into one quick view for a cleaner chart read."
    ),
    (
        "Signal Confirmation Workflow",
        "One signal alone can be misleading. "
        "The bot compares several pieces of chart information together "
        "so you can see whether momentum, structure, and technical signals "
        "are actually pointing in the same direction."
    ),
    (
        "Volatility Check",
        "Volatility changes the way every setup behaves. "
        "The bot watches how quickly price is moving and how wide recent swings are, "
        "making sudden changes in market speed much easier to notice."
    ),
    (
        "Chart Structure Scan",
        "Watch the recent highs and lows closely. "
        "The bot organizes those swing points and tracks structure changes "
        "so you can quickly see whether the chart is trending, ranging, or shifting."
    ),
    (
        "Moving Average Review",
        "Moving averages are more useful when price action confirms them. "
        "The bot compares average direction with current candles and recent movement "
        "so the broader trend context is easier to understand."
    ),
    (
        "Breakout Setup Check",
        "Not every breakout keeps moving. "
        "The bot reviews the level, the approach into it, and the movement after the break "
        "so the setup can be checked with more context instead of one candle."
    ),
    (
        "Reversal Pattern Scan",
        "A reversal usually needs more than one clue. "
        "The bot compares recent reactions, swing structure, and momentum changes "
        "to organize the signs that the current move may be losing strength."
    ),
    (
        "OTC Chart Review",
        "OTC charts can move differently from regular sessions. "
        "The bot organizes recent price behavior, candle patterns, and momentum changes "
        "so unusual movement is easier to review without relying on one signal."
    ),
    (
        "Indicator Cross Check",
        "Indicators become more useful when they agree with the chart. "
        "The bot compares technical readings with current price action "
        "so conflicting information is easier to notice before you review a setup."
    ),
    (
        "Entry Setup Research",
        "Before looking at an entry, the chart needs context. "
        "The bot organizes trend, structure, momentum, and nearby levels "
        "into one fast workflow so the setup can be reviewed more clearly."
    ),
    (
        "Live Market Monitoring",
        "Charts can change while you are still analyzing the last move. "
        "The bot keeps scanning recent movement and flags meaningful changes "
        "so the analysis stays focused on what the market is doing now."
    ),
    (
        "Multi Signal Analysis",
        "The strongest analysis comes from checking more than one clue. "
        "The bot compares chart structure, momentum, candle behavior, and technical signals "
        "to build one organized view of the current setup."
    ),
]

HOOKS = [
    "Look at this chart for a second.",
    "Here is what the bot checks first.",
    "Watch this setup closely.",
    "This is where the chart gets interesting.",
    "Here is a faster way to read this move.",
    "See what changes before the next move.",
    "This chart has more information than it first shows.",
    "Here is the part most traders should check first.",
]

CLOSERS = [
    "That gives you a cleaner setup to review before making your own decision.",
    "Now the chart is easier to read without depending on one signal alone.",
    "That keeps the analysis fast, clear, and focused on the actual chart.",
    "The result is a quicker research workflow with the final decision still yours.",
    "That makes the important chart information easier to review at a glance.",
    "It is a faster way to organize the chart without treating any signal as guaranteed.",
]

TITLE_SUFFIXES = [
    "",
    "Explained",
    "Fast Breakdown",
    "Quick Chart Check",
    "Setup Review",
    "Live Analysis",
]


# ============================================================
# HISTORY HELPERS
# ============================================================

def ensure_data_directory():
    os.makedirs(
        os.path.dirname(HISTORY_FILE),
        exist_ok=True,
    )


def normalize_text(value):
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_history():
    ensure_data_directory()

    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(
            f"WARNING: Could not load content history: {exc}",
            flush=True,
        )
        return []


def save_history(history):
    ensure_data_directory()
    temporary = HISTORY_FILE + ".tmp"

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            history[-MAX_HISTORY:],
            file,
            indent=2,
            ensure_ascii=False,
        )

    os.replace(
        temporary,
        HISTORY_FILE,
    )


def similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


def content_is_too_similar(
    title,
    script,
    history,
):
    recent = [
        item
        for item in history[-SIMILARITY_HISTORY_WINDOW:]
        if isinstance(item, dict)
    ]

    normalized_title = normalize_text(title)
    normalized_script = normalize_text(script)

    for item in recent:
        old_title = item.get("title", "")
        old_script = item.get("script", "")

        if normalized_title == normalize_text(old_title):
            return True, "exact duplicate title"

        if normalized_script == normalize_text(old_script):
            return True, "exact duplicate script"

        title_score = similarity(
            title,
            old_title,
        )
        if title_score >= TITLE_SIMILARITY_LIMIT:
            return (
                True,
                f"title too similar to history ({title_score:.2f})",
            )

        script_score = similarity(
            script,
            old_script,
        )
        if script_score >= SCRIPT_SIMILARITY_LIMIT:
            return (
                True,
                f"script too similar to history ({script_score:.2f})",
            )

    return False, "OK"


def keyword_usage_count(
    history,
    keyword,
):
    count = 0
    keyword_lower = keyword.lower()

    for item in history:
        if not isinstance(item, dict):
            continue

        title = str(
            item.get("title", "")
        ).strip().lower()

        if title.startswith(keyword_lower):
            count += 1

    return count


def choose_title_keyword(history):
    counts = {
        keyword: keyword_usage_count(
            history,
            keyword,
        )
        for keyword in TITLE_KEYWORDS
    }

    minimum = min(
        counts.values()
    ) if counts else 0

    choices = [
        keyword
        for keyword, count in counts.items()
        if count == minimum
    ]

    return random.choice(
        choices or TITLE_KEYWORDS
    )


# ============================================================
# VALIDATION
# ============================================================

def word_count(text):
    return len(
        re.findall(
            r"\b[\w'-]+\b",
            text,
        )
    )


def clean_json_text(text):
    text = str(text or "").strip()
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^```\s*",
        "",
        text,
    )
    text = re.sub(
        r"\s*```$",
        "",
        text,
    )
    return text.strip()


def has_requested_title_keyword(title):
    title_lower = title.lower()
    return any(
        keyword.lower() in title_lower
        for keyword in TITLE_KEYWORDS
    )


def validate_content(
    title,
    script,
    required_keyword=None,
):
    if not title or not script:
        return False, "Title or script is empty."

    title = title.strip()
    script = script.strip()

    if not has_requested_title_keyword(title):
        return (
            False,
            "Title does not contain an approved Pocket Option keyword.",
        )

    if (
        required_keyword
        and not title.lower().startswith(
            required_keyword.lower()
        )
    ):
        return (
            False,
            f"Title must start with '{required_keyword}'.",
        )

    if len(title) > 100:
        return False, "Title is longer than 100 characters."

    words = word_count(script)

    if words < MIN_SCRIPT_WORDS:
        return (
            False,
            f"Script is too short: {words} words.",
        )

    if words > MAX_SCRIPT_WORDS:
        return (
            False,
            f"Script is too long: {words} words.",
        )

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

    combined = (
        f"{title.lower()} "
        f"{script.lower()}"
    )

    for phrase in forbidden_phrases:
        if phrase in combined:
            return (
                False,
                f"Forbidden phrase detected: {phrase}",
            )

    # Retention scripts should stay punchy rather than becoming one long paragraph.
    sentences = [
        item.strip()
        for item in re.split(
            r"[.!?]+",
            script,
        )
        if item.strip()
    ]

    if len(sentences) < 3:
        return False, "Script needs at least 3 short spoken sentences."

    if len(sentences) > 6:
        return False, "Script has too many sentences for a 20-second Short."

    return True, "OK"


# ============================================================
# GEMINI
# ============================================================

def extract_final_text(data):
    try:
        candidate = data["candidates"][0]
    except Exception as exc:
        raise RuntimeError(
            f"Gemini response has no candidate: {str(data)[:1000]}"
        ) from exc

    if candidate.get("finishReason") == "MAX_TOKENS":
        raise RuntimeError(
            "Gemini hit MAX_TOKENS before finishing the response."
        )

    parts = candidate.get(
        "content",
        {},
    ).get(
        "parts",
        [],
    )

    final_parts = []

    for part in parts:
        if (
            not isinstance(part, dict)
            or part.get("thought") is True
        ):
            continue

        if part.get("text"):
            final_parts.append(
                part["text"]
            )

    if not final_parts:
        raise RuntimeError(
            "Gemini response did not contain final generated text."
        )

    return "".join(
        final_parts
    ).strip()


def generate_with_gemini(
    history,
    target_keyword,
):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    recent_titles = [
        item.get("title", "")
        for item in history[-60:]
        if (
            isinstance(item, dict)
            and item.get("title")
        )
    ]

    recent_scripts = [
        item.get("script", "")
        for item in history[-50:]
        if (
            isinstance(item, dict)
            and item.get("script")
        )
    ]

    prompt = f"""
Create ONE high-retention YouTube Short title and ONE spoken script about Pocket Option trading automation.

SEO TITLE RULES:
- The title MUST START with exactly this target keyword phrase: {target_keyword}
- Make the rest specific, natural, clickable, and different from recent titles.
- Keep the title under 100 characters.

VOICE SCRIPT RULES:
- Write 52 to 62 words.
- Make the delivery energetic, confident, and fast-moving, but truthful.
- The FIRST sentence must be a short hook that grabs attention immediately.
- Use 3 to 5 short spoken sentences.
- Avoid long academic explanations and filler.
- Focus on ONE concrete chart idea: momentum, price action, market structure,
  candlesticks, support/resistance, indicators, volatility, signals,
  bot workflow, trend strength, breakouts, reversals, or automated monitoring.
- Make the script genuinely different from recent scripts.
- Do not reuse the same sentence structure with a few words changed.
- Do not promise profit, income, accuracy, win rate, or guaranteed results.
- Do not invent statistics.
- Do not include any CTA.
- Do not mention link in bio, channel description, activation button, or related video.
- Do not use fake urgency or guaranteed-money language.

RECENT TITLES TO AVOID:
{chr(10).join("- " + title for title in recent_titles) or "None"}

RECENT SCRIPTS TO AVOID:
{chr(10).join("- " + script for script in recent_scripts) or "None"}

Return only JSON with keys title and script.
"""

    # Use the broadly supported generateContent JSON configuration.
    # This also fixes the responseFormat/mimeType 400 seen in Railway logs.
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
            "temperature": 1.05,
            "topP": 0.95,
            "maxOutputTokens": 500,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "title": {
                        "type": "STRING",
                    },
                    "script": {
                        "type": "STRING",
                    },
                },
                "required": [
                    "title",
                    "script",
                ],
            },
        },
    }

    response = requests.post(
        GEMINI_URL,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API error {response.status_code}: "
            f"{response.text[:1500]}"
        )

    generated_text = clean_json_text(
        extract_final_text(
            response.json()
        )
    )

    try:
        result = json.loads(
            generated_text
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid JSON: "
            f"{generated_text[:1500]}"
        ) from exc

    return (
        str(
            result.get(
                "title",
                "",
            )
        ).strip(),
        str(
            result.get(
                "script",
                "",
            )
        ).strip(),
    )


# ============================================================
# FALLBACK
# ============================================================

def get_unique_fallback(
    history,
    target_keyword,
):
    combinations = []

    for angle, body in FALLBACK_ANGLES:
        for hook in HOOKS:
            for closer in CLOSERS:
                combinations.append(
                    (
                        angle,
                        hook,
                        body,
                        closer,
                    )
                )

    random.shuffle(
        combinations
    )

    for angle, hook, body, closer in combinations:
        for suffix in TITLE_SUFFIXES:
            title_angle = (
                angle
                if not suffix
                else f"{angle} {suffix}"
            )

            title = (
                f"{target_keyword}: "
                f"{title_angle}"
            )

            script = " ".join(
                [
                    hook,
                    body,
                    closer,
                ]
            )

            valid, _ = validate_content(
                title,
                script,
                target_keyword,
            )

            if not valid:
                continue

            too_similar, _ = content_is_too_similar(
                title,
                script,
                history,
            )

            if not too_similar:
                return (
                    title,
                    script,
                )

    raise RuntimeError(
        "Could not create a unique high-retention fallback script."
    )


# ============================================================
# SAVE / PUBLIC GENERATOR
# ============================================================

def save_new_content(
    title,
    script,
    history,
):
    history.append(
        {
            "title": title.strip(),
            "script": script.strip(),
            "timestamp": int(
                time.time()
            ),
        }
    )

    save_history(
        history
    )

    print(
        f"FINAL TITLE: {title}",
        flush=True,
    )
    print(
        f"FINAL SCRIPT: {script}",
        flush=True,
    )
    print(
        f"SCRIPT WORDS: {word_count(script)}",
        flush=True,
    )

    return (
        title.strip(),
        script.strip(),
    )


def generate_content():
    print(
        "\n==========================================",
        flush=True,
    )
    print(
        "GENERATING UNIQUE HIGH-RETENTION CONTENT",
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

    target_keyword = choose_title_keyword(
        history
    )

    print(
        f"Target title keyword: {target_keyword}",
        flush=True,
    )

    for attempt in range(
        1,
        GEMINI_ATTEMPTS + 1,
    ):
        try:
            print(
                f"Gemini attempt {attempt}/{GEMINI_ATTEMPTS}",
                flush=True,
            )

            title, script = generate_with_gemini(
                history,
                target_keyword,
            )

            valid, reason = validate_content(
                title,
                script,
                target_keyword,
            )

            if not valid:
                print(
                    f"Rejected: {reason}",
                    flush=True,
                )
                continue

            too_similar, similarity_reason = (
                content_is_too_similar(
                    title,
                    script,
                    history,
                )
            )

            if too_similar:
                print(
                    f"Rejected: {similarity_reason}",
                    flush=True,
                )
                continue

            print(
                "NEW UNIQUE ENERGETIC TITLE + SCRIPT ACCEPTED",
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
        "Gemini unavailable or duplicate-prone; "
        "using high-retention unique fallback.",
        flush=True,
    )

    title, script = get_unique_fallback(
        history,
        target_keyword,
    )

    valid, reason = validate_content(
        title,
        script,
        target_keyword,
    )

    if not valid:
        raise RuntimeError(
            f"Fallback content failed validation: {reason}"
        )

    too_similar, similarity_reason = (
        content_is_too_similar(
            title,
            script,
            history,
        )
    )

    if too_similar:
        raise RuntimeError(
            "Fallback content is not unique enough: "
            f"{similarity_reason}"
        )

    return save_new_content(
        title,
        script,
        history,
    )
