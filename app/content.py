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

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

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
            "The Pocket Option AI Bot is designed to analyze "
            "market information and identify possible trading "
            "setups. Instead of manually watching charts all "
            "day, the bot helps organize the analysis into a "
            "simpler workflow for traders."
        )
    },

    {
        "title": "How Pocket Option AI Trading Bot Analyzes Markets",
        "script": (
            "A Pocket Option AI Trading Bot can process market "
            "information and look for patterns that may be useful "
            "during analysis. The idea is to reduce repetitive "
            "chart watching and provide a more structured way "
            "to review potential trading opportunities."
        )
    },

    {
        "title": "Pocket Option AI Bot Trading Workflow",
        "script": (
            "Here is a simple look at the Pocket Option AI Bot "
            "workflow. Market information is analyzed first, "
            "possible setups are identified, and the results can "
            "then be reviewed before making any trading decision. "
            "It is designed to simplify repetitive analysis."
        )
    },

    {
        "title": "Pocket Option AI Bot Market Analysis",
        "script": (
            "The Pocket Option AI Bot focuses on market analysis "
            "rather than simply guessing the next price movement. "
            "It can examine chart information and patterns to "
            "help organize the research process before a trader "
            "decides what to do."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Chart Analysis",
        "script": (
            "Watching charts manually can take a lot of time. "
            "A Pocket Option AI Trading Bot can help analyze "
            "chart information and organize potential setups. "
            "The goal is to make the research process more "
            "structured while keeping the final decision with "
            "the trader."
        )
    },

    {
        "title": "Pocket Option AI Bot Signal Analysis",
        "script": (
            "The Pocket Option AI Bot can be used as an analysis "
            "tool for reviewing market signals and chart patterns. "
            "It helps bring different pieces of market information "
            "together so traders can spend less time on repetitive "
            "manual observation."
        )
    },

    {
        "title": "Pocket Option AI Bot for Beginners",
        "script": (
            "If you are new to automated trading tools, the "
            "Pocket Option AI Bot is worth understanding before "
            "using it. The system focuses on analyzing market "
            "information and presenting potential setups in a "
            "more organized workflow."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Technology",
        "script": (
            "The technology behind a Pocket Option AI Trading Bot "
            "can combine market data, chart patterns, and automated "
            "analysis. This type of system is built to handle "
            "repetitive research tasks and help traders review "
            "market conditions more efficiently."
        )
    },

    {
        "title": "Pocket Option AI Bot and Candlestick Patterns",
        "script": (
            "Candlestick patterns are an important part of chart "
            "analysis. A Pocket Option AI Bot can examine this "
            "type of market information together with other signals "
            "to identify areas that may deserve closer attention "
            "during a trading session."
        )
    },

    {
        "title": "Pocket Option AI Bot Real Time Market Analysis",
        "script": (
            "Market conditions can change quickly, which makes "
            "constant chart monitoring difficult. The Pocket Option "
            "AI Bot is designed to assist with market analysis by "
            "processing available information and highlighting "
            "patterns that may need further review."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Setup Guide",
        "script": (
            "Before using a Pocket Option AI Trading Bot, it helps "
            "to understand the basic workflow. The system analyzes "
            "market information, identifies potential setups, and "
            "provides information that can be reviewed before any "
            "trading action is considered."
        )
    },

    {
        "title": "Pocket Option AI Bot Market Signals",
        "script": (
            "Market signals can contain useful information, but "
            "they still need proper analysis. The Pocket Option AI "
            "Bot helps organize this process by examining market "
            "data and identifying patterns that traders can review "
            "before deciding whether a setup is worth considering."
        )
    },

    {
        "title": "Pocket Option AI Bot Chart Scanner",
        "script": (
            "A chart scanner can save time when there are many "
            "market movements to review. The Pocket Option AI Bot "
            "uses automated analysis to examine chart information "
            "and organize possible setups, giving traders another "
            "way to structure their market research."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Explained",
        "script": (
            "What exactly does a Pocket Option AI Trading Bot do? "
            "It is designed to automate parts of the market analysis "
            "process by examining available information and looking "
            "for patterns. The results can then be reviewed before "
            "making an independent trading decision."
        )
    },

    {
        "title": "Pocket Option AI Bot Automated Analysis",
        "script": (
            "Automated analysis can make repetitive chart research "
            "less time consuming. The Pocket Option AI Bot is built "
            "around this idea, processing market information and "
            "helping identify areas that could require additional "
            "attention during a trading session."
        )
    },

    {
        "title": "Pocket Option AI Bot Trading Signals Explained",
        "script": (
            "Trading signals are only one part of a larger analysis "
            "process. The Pocket Option AI Bot can examine signals "
            "alongside chart information and market patterns, helping "
            "create a more organized workflow for reviewing possible "
            "trading setups."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Market Scanner",
        "script": (
            "A Pocket Option AI Trading Bot can act like an automated "
            "market scanner by processing chart information and "
            "looking for patterns. This can reduce some repetitive "
            "manual monitoring and make it easier to organize the "
            "information needed for further analysis."
        )
    },

    {
        "title": "Pocket Option AI Bot Pattern Detection",
        "script": (
            "Pattern detection is one area where automated tools "
            "can assist traders. The Pocket Option AI Bot examines "
            "market information for recognizable patterns and "
            "possible setups, giving users another source of "
            "information to consider during their own analysis."
        )
    },

    {
        "title": "Pocket Option AI Bot Trading Setup Analysis",
        "script": (
            "Finding a trading setup requires looking at several "
            "pieces of market information. The Pocket Option AI Bot "
            "can help organize that process by analyzing charts, "
            "patterns, and signals so traders can review the setup "
            "before taking any action."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Market Patterns",
        "script": (
            "Market patterns can appear in different forms across "
            "a chart. A Pocket Option AI Trading Bot can process "
            "market information and look for patterns that match "
            "its analysis rules, helping users structure their "
            "research before making an independent decision."
        )
    },

    {
        "title": "Pocket Option AI Bot Indicator Analysis",
        "script": (
            "Technical indicators can provide additional information "
            "when reviewing a chart. The Pocket Option AI Bot can "
            "combine indicator information with other market data "
            "to create a more structured analysis process and help "
            "users review potential setups."
        )
    },

    {
        "title": "Pocket Option AI Bot Automated Chart Review",
        "script": (
            "Instead of manually checking every chart movement, "
            "the Pocket Option AI Bot can assist with automated "
            "chart review. It processes available market information "
            "and highlights patterns or setups that may deserve "
            "closer attention from the trader."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Signal Scanner",
        "script": (
            "A signal scanner can help organize information from "
            "market charts. The Pocket Option AI Trading Bot is "
            "designed to process this information and identify "
            "potential signals, while the trader remains responsible "
            "for reviewing the results and deciding what to do."
        )
    },

    {
        "title": "Pocket Option AI Bot Trading Dashboard",
        "script": (
            "A trading dashboard can make market information easier "
            "to review in one place. The Pocket Option AI Bot uses "
            "automated analysis to organize important information "
            "and potential setups so users can spend more time "
            "reviewing the actual market conditions."
        )
    },

    {
        "title": "Pocket Option AI Bot Market Monitoring",
        "script": (
            "Continuous market monitoring can be difficult when "
            "done manually. The Pocket Option AI Bot is designed "
            "to assist by analyzing market information and watching "
            "for patterns that match its analysis process, giving "
            "traders another tool for market research."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Technical Analysis",
        "script": (
            "Technical analysis involves studying price movement, "
            "patterns, and indicators. A Pocket Option AI Trading "
            "Bot can automate parts of this research by processing "
            "market information and presenting potential setups "
            "for further human review."
        )
    },

    {
        "title": "Pocket Option AI Bot Price Movement Analysis",
        "script": (
            "Price movement can change rapidly during a trading "
            "session. The Pocket Option AI Bot helps analyze those "
            "movements by processing chart information and looking "
            "for patterns. The results are intended to support "
            "research rather than guarantee a specific outcome."
        )
    },

    {
        "title": "Pocket Option AI Bot Trading Research Tool",
        "script": (
            "Think of the Pocket Option AI Bot as a trading research "
            "tool. It can process market information, examine chart "
            "patterns, and organize possible setups. This can help "
            "reduce repetitive research while keeping the final "
            "trading decision with the user."
        )
    },

    {
        "title": "Pocket Option AI Trading Bot Chart Signals",
        "script": (
            "Chart signals can be useful when combined with broader "
            "market analysis. The Pocket Option AI Trading Bot can "
            "process chart information and identify potential signals "
            "for review, giving traders a structured starting point "
            "for examining a market."
        )
    },

    {
        "title": "Pocket Option AI Bot Trading Analysis System",
        "script": (
            "The Pocket Option AI Bot is built around automated "
            "market analysis. It can process information from charts "
            "and identify patterns according to its analysis rules. "
            "Users can then review the information and consider "
            "whether a setup makes sense."
        )
    }
]


# ============================================================
# HISTORY HELPERS
# ============================================================

def ensure_data_directory():

    directory = os.path.dirname(
        HISTORY_FILE
    )

    if directory:

        os.makedirs(
            directory,
            exist_ok=True
        )


def normalize_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    value = value.strip()

    return value


def load_history():

    ensure_data_directory()

    if not os.path.exists(
        HISTORY_FILE
    ):

        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(
            data,
            list
        ):

            return []

        return data

    except Exception as e:

        print(
            f"WARNING: Could not load "
            f"content history: {e}",
            flush=True
        )

        return []


def save_history(history):

    ensure_data_directory()

    temporary_file = (
        HISTORY_FILE
        + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temporary_file,
        HISTORY_FILE
    )


# ============================================================
# HISTORY SETS
# ============================================================

def get_used_titles(history):

    return {
        normalize_text(
            item.get("title", "")
        )
        for item in history
        if isinstance(item, dict)
    }


def get_used_scripts(history):

    return {
        normalize_text(
            item.get("script", "")
        )
        for item in history
        if isinstance(item, dict)
    }


def is_duplicate(
    title,
    script,
    history
):

    normalized_title = normalize_text(
        title
    )

    normalized_script = normalize_text(
        script
    )

    used_titles = get_used_titles(
        history
    )

    used_scripts = get_used_scripts(
        history
    )

    if normalized_title in used_titles:

        return True

    if normalized_script in used_scripts:

        return True

    return False


# ============================================================
# WORD COUNT
# ============================================================

def word_count(text):

    return len(
        re.findall(
            r"\b[\w'-]+\b",
            text
        )
    )


# ============================================================
# CLEAN GEMINI RESPONSE
# ============================================================

def clean_json_text(text):

    if not text:

        return ""

    text = text.strip()

    # Remove markdown code fences.

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


# ============================================================
# VALIDATION
# ============================================================

def validate_content(
    title,
    script
):

    if not title or not script:

        return False, (
            "Title or script is empty."
        )


    title = title.strip()
    script = script.strip()


    # --------------------------------------------------------
    # TITLE KEYWORD
    # --------------------------------------------------------

    title_lower = title.lower()

    if (
        "pocket option ai bot"
        not in title_lower
        and
        "pocket option ai trading bot"
        not in title_lower
    ):

        return False, (
            "Title must contain "
            "'Pocket Option AI Bot' "
            "or "
            "'Pocket Option AI Trading Bot'."
        )


    # --------------------------------------------------------
    # SCRIPT LENGTH
    # --------------------------------------------------------

    words = word_count(
        script
    )

    if words < MIN_SCRIPT_WORDS:

        return False, (
            f"Script is too short: "
            f"{words} words."
        )

    if words > MAX_SCRIPT_WORDS:

        return False, (
            f"Script is too long: "
            f"{words} words."
        )


    # --------------------------------------------------------
    # FORBIDDEN PHRASES
    # --------------------------------------------------------

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

        "get rich quick"
    ]


    combined = (
        title_lower
        + " "
        + script.lower()
    )


    for phrase in forbidden_phrases:

        if phrase in combined:

            return False, (
                f"Forbidden phrase detected: "
                f"{phrase}"
            )


    # --------------------------------------------------------
    # SCRIPT MUST NOT LOOK LIKE A CTA
    # --------------------------------------------------------

    if script.strip().lower().startswith(
        (
            "go to",
            "click",
            "visit",
            "check the link"
        )
    ):

        return False, (
            "Script starts with CTA wording."
        )


    return True, "OK"


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_with_gemini(
    history
):

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )


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
        f"- {title}"
        for title in used_titles
        if title
    )

    recent_scripts_text = "\n".join(
        f"- {script}"
        for script in used_scripts
        if script
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

The script must be natural spoken English.

The script should explain ONE specific topic related to:
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

The script must stand alone as educational/explanatory content.

MOST IMPORTANT:
The title and script MUST be different from every previous
title and script listed below.

PREVIOUS TITLES:
{recent_titles_text}

PREVIOUS SCRIPTS:
{recent_scripts_text}

Return ONLY valid JSON.

Required format:

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
                        "text": prompt
                    }

                ]
            }

        ],

        "generationConfig": {

            "temperature": 1.15,

            "topP": 0.95,

            "topK": 40,

            "maxOutputTokens": 300
        }
    }


    headers = {

        "Content-Type":
            "application/json",

        "x-goog-api-key":
            GEMINI_API_KEY
    }


    response = requests.post(

        GEMINI_URL,

        headers=headers,

        json=payload,

        timeout=90
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
            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        )

    except Exception:

        raise RuntimeError(
            "Gemini response did not "
            "contain generated text."
        )


    generated_text = clean_json_text(
        generated_text
    )


    try:

        result = json.loads(
            generated_text
        )

    except json.JSONDecodeError:

        # Try extracting the first JSON
        # object if Gemini wrapped it.

        match = re.search(
            r"\{.*\}",
            generated_text,
            flags=re.DOTALL
        )

        if not match:

            raise RuntimeError(
                "Gemini returned invalid JSON: "
                f"{generated_text}"
            )

        result = json.loads(
            match.group(0)
        )


    title = str(
        result.get(
            "title",
            ""
        )
    ).strip()

    script = str(
        result.get(
            "script",
            ""
        )
    ).strip()


    return title, script


# ============================================================
# FALLBACK SELECTION
# ============================================================

def get_unused_fallback(
    history
):

    used_titles = get_used_titles(
        history
    )

    used_scripts = get_used_scripts(
        history
    )


    unused = []

    for item in FALLBACK_CONTENT:

        title = normalize_text(
            item["title"]
        )

        script = normalize_text(
            item["script"]
        )

        if (
            title not in used_titles
            and
            script not in used_scripts
        ):

            unused.append(
                item
            )


    if not unused:

        return None


    return random.choice(
        unused
    )


# ============================================================
# UNIQUE FALLBACK VARIANT
# ============================================================

def create_unique_fallback_variant(
    history
):

    used_titles = get_used_titles(
        history
    )

    used_scripts = get_used_scripts(
        history
    )


    base_topics = [

        (
            "Pocket Option AI Bot "
            "Chart Monitoring",
            "The Pocket Option AI Bot can "
            "assist with chart monitoring by "
            "processing market information and "
            "highlighting patterns for review. "
            "Instead of manually watching every "
            "price movement, traders can use "
            "automated analysis as one part of "
            "their research workflow."
        ),

        (
            "Pocket Option AI Trading Bot "
            "Market Research",
            "Market research involves studying "
            "price movement, signals, and "
            "patterns before making decisions. "
            "The Pocket Option AI Trading Bot "
            "can help organize this information "
            "through automated analysis, giving "
            "users another way to review market "
            "conditions."
        ),

        (
            "Pocket Option AI Bot "
            "Trading Technology",
            "Modern trading technology can "
            "automate repetitive parts of market "
            "research. The Pocket Option AI Bot "
            "is designed to process available "
            "market information and identify "
            "patterns, helping users structure "
            "their analysis before considering "
            "a trading setup."
        ),

        (
            "Pocket Option AI Trading Bot "
            "Pattern Scanner",
            "Pattern scanning can help traders "
            "review large amounts of chart "
            "information more efficiently. The "
            "Pocket Option AI Trading Bot can "
            "analyze market data and identify "
            "patterns for further review, while "
            "the user remains responsible for "
            "evaluating the information."
        ),

        (
            "Pocket Option AI Bot "
            "Price Analysis",
            "Price analysis becomes more "
            "structured when market information "
            "is reviewed consistently. The "
            "Pocket Option AI Bot can assist "
            "with this process by examining "
            "price movements and chart patterns "
            "and organizing possible areas of "
            "interest for additional research."
        )
    ]


    # First try untouched variants.

    for title, script in base_topics:

        if (
            normalize_text(title)
            not in used_titles
            and
            normalize_text(script)
            not in used_scripts
        ):

            return title, script


    # If all base variants were used,
    # append a unique topic number.

    for number in range(
        1,
        10001
    ):

        title = (
            "Pocket Option AI Bot "
            f"Analysis Topic {number}"
        )

        script = (
            "This Pocket Option AI Bot topic "
            f"focuses on automated market analysis "
            f"and trading research, variation {number}. "
            "The system can process chart information "
            "and identify patterns that users may "
            "review before making an independent "
            "trading decision."
        )

        if (
            normalize_text(title)
            not in used_titles
            and
            normalize_text(script)
            not in used_scripts
        ):

            return title, script


    raise RuntimeError(
        "Could not create a unique fallback."
    )


# ============================================================
# MAIN CONTENT GENERATOR
# ============================================================

def generate_content():

    print(
        "\n"
        "==========================================",
        flush=True
    )

    print(
        "GENERATING UNIQUE CONTENT",
        flush=True
    )

    print(
        "==========================================",
        flush=True
    )


    history = load_history()


    print(
        f"Existing content history: "
        f"{len(history)} items",
        flush=True
    )


    # ========================================================
    # GEMINI ATTEMPTS
    # ========================================================

    for attempt in range(
        1,
        GEMINI_ATTEMPTS + 1
    ):

        try:

            print(
                f"\nGemini attempt "
                f"{attempt}/{GEMINI_ATTEMPTS}",
                flush=True
            )


            title, script = (
                generate_with_gemini(
                    history
                )
            )


            print(
                f"Generated title: {title}",
                flush=True
            )

            print(
                f"Script words: "
                f"{word_count(script)}",
                flush=True
            )


            valid, reason = (
                validate_content(
                    title,
                    script
                )
            )


            if not valid:

                print(
                    f"Rejected: {reason}",
                    flush=True
                )

                continue


            if is_duplicate(
                title,
                script,
                history
            ):

                print(
                    "Rejected: duplicate "
                    "title or script.",
                    flush=True
                )

                continue


            print(
                "\nNEW UNIQUE CONTENT ACCEPTED",
                flush=True
            )

            return save_new_content(
                title,
                script,
                history
            )


        except Exception as e:

            print(
                f"Gemini attempt failed: {e}",
                flush=True
            )

            # Small delay before retry.

            if attempt < GEMINI_ATTEMPTS:

                time.sleep(2)


    # ========================================================
    # FALLBACK
    # ========================================================

    print(
        "\nGemini could not produce "
        "valid unique content.",
        flush=True
    )

    fallback = get_unused_fallback(
        history
    )


    if fallback:

        title = fallback["title"]

        script = fallback["script"]

    else:

        title, script = (
            create_unique_fallback_variant(
                history
            )
        )


    valid, reason = (
        validate_content(
            title,
            script
        )
    )


    if not valid:

        raise RuntimeError(
            "Fallback content failed "
            f"validation: {reason}"
        )


    if is_duplicate(
        title,
        script,
        history
    ):

        raise RuntimeError(
            "Fallback content is "
            "still duplicated."
        )


    print(
        "\nUNIQUE FALLBACK ACCEPTED",
        flush=True
    )

    print(
        f"Title: {title}",
        flush=True
    )

    print(
        f"Words: {word_count(script)}",
        flush=True
    )


    return save_new_content(
        title,
        script,
        history
    )


# ============================================================
# SAVE NEW CONTENT
# ============================================================

def save_new_content(
    title,
    script,
    history
):

    history.append({

        "title":
            title.strip(),

        "script":
            script.strip(),

        "timestamp":
            int(time.time())
    })


    # Keep a large history so old titles/scripts
    # don't start repeating.

    if len(history) > MAX_HISTORY:

        history = history[
            -MAX_HISTORY:
        ]


    save_history(
        history
    )


    print(
        "\nSaved to content history:",
        flush=True
    )

    print(
        HISTORY_FILE,
        flush=True
    )


    print(
        "\nFINAL TITLE:",
        flush=True
    )

    print(
        title,
        flush=True
    )

    print(
        "\nFINAL SCRIPT:",
        flush=True
    )

    print(
        script,
        flush=True
    )


    return (
        title.strip(),
        script.strip()
    )
