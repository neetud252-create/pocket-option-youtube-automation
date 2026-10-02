import os
import json
import re
import threading
import requests

from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_ADMIN_CHAT_ID = os.getenv(
    "TELEGRAM_ADMIN_CHAT_ID"
)

TELEGRAM_WEBHOOK_SECRET = os.getenv(
    "TELEGRAM_WEBHOOK_SECRET",
    "pocket-option-telegram-secure"
)

BASE_URL = (
    "https://api.telegram.org/bot"
    + (TELEGRAM_BOT_TOKEN or "")
)

from app.channels import DATA_DIR

BUFFER_FILE = os.path.join(
    DATA_DIR,
    "buffer_queue.json"
)

AUTOMATION_STATE_FILE = os.path.join(
    DATA_DIR,
    "automation_state.json"
)

USER_ACCESS_FILE = os.path.join(
    DATA_DIR,
    "telegram_user_access.json"
)

ACCOUNT_REGISTRATION_URL = os.getenv(
    "ACCOUNT_REGISTRATION_URL",
    ""
).strip()

UID_VERIFY_URL = os.getenv(
    "UID_VERIFY_URL",
    ""
).strip()

DEPOSIT_VERIFY_URL = os.getenv(
    "DEPOSIT_VERIFY_URL",
    ""
).strip()

AFFILIATE_API_KEY = os.getenv(
    "AFFILIATE_API_KEY",
    ""
).strip()

TRADING_ACCESS_URL = os.getenv(
    "TRADING_ACCESS_URL",
    ""
).strip()

SUPPORT_USERNAME = os.getenv(
    "SUPPORT_USERNAME",
    ""
).strip().lstrip("@")

try:
    REQUIRED_DEPOSIT_AMOUNT = float(
        os.getenv("REQUIRED_DEPOSIT_AMOUNT", "0") or 0
    )
except ValueError:
    REQUIRED_DEPOSIT_AMOUNT = 0.0

DEPOSIT_CURRENCY = os.getenv(
    "DEPOSIT_CURRENCY",
    "USD"
).strip().upper() or "USD"

TIMEZONE = ZoneInfo(
    "Asia/Kolkata"
)

AUTOMATION_LOCK = threading.Lock()
USER_ACCESS_LOCK = threading.RLock()


# ============================================================
# VALIDATION
# ============================================================

def telegram_configured():

    return bool(
        TELEGRAM_BOT_TOKEN
        and TELEGRAM_ADMIN_CHAT_ID
    )


def is_admin(
    chat_id
):

    if not TELEGRAM_ADMIN_CHAT_ID:
        return False

    return str(
        chat_id
    ) == str(
        TELEGRAM_ADMIN_CHAT_ID
    )


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_request(
    method,
    payload=None
):

    if not TELEGRAM_BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    url = (
        BASE_URL
        + "/"
        + method
    )

    response = requests.post(
        url,
        json=payload or {},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):

        raise RuntimeError(
            f"Telegram API error: "
            f"{data}"
        )

    return data


# ============================================================
# SEND MESSAGE
# ============================================================

def send_message(
    chat_id,
    text,
    reply_markup=None
):

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    if reply_markup:

        payload[
            "reply_markup"
        ] = reply_markup

    return telegram_request(
        "sendMessage",
        payload
    )


def send_document(chat_id, document, caption=None, reply_markup=None):
    """Send a Telegram-hosted document by reusable file_id."""
    payload = {
        "chat_id": chat_id,
        "document": document,
    }
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return telegram_request("sendDocument", payload)


# ============================================================
# USER ACCESS STORAGE
# ============================================================

def _empty_user_access_data():
    return {
        "users": {},
        "gift": {},
    }


def load_user_access_data():
    with USER_ACCESS_LOCK:
        if not os.path.exists(USER_ACCESS_FILE):
            return _empty_user_access_data()
        try:
            with open(USER_ACCESS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                return _empty_user_access_data()
            if not isinstance(data.get("users"), dict):
                data["users"] = {}
            if not isinstance(data.get("gift"), dict):
                data["gift"] = {}
            return data
        except Exception as error:
            print(f"User access data read error: {error}", flush=True)
            return _empty_user_access_data()


def save_user_access_data(data):
    with USER_ACCESS_LOCK:
        os.makedirs(DATA_DIR, exist_ok=True)
        temporary = USER_ACCESS_FILE + ".tmp"
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(temporary, USER_ACCESS_FILE)


def get_user_record(user_id, profile=None):
    user_key = str(user_id)
    with USER_ACCESS_LOCK:
        data = load_user_access_data()
        user = data["users"].get(user_key)
        if not isinstance(user, dict):
            user = {
                "telegram_user_id": user_id,
                "state": "NEW",
                "created_at": datetime.now(TIMEZONE).isoformat(),
            }
        if profile:
            user["username"] = profile.get("username")
            user["first_name"] = profile.get("first_name")
            user["last_name"] = profile.get("last_name")
        user["updated_at"] = datetime.now(TIMEZONE).isoformat()
        data["users"][user_key] = user
        save_user_access_data(data)
        return dict(user)


def update_user_record(user_id, **changes):
    user_key = str(user_id)
    with USER_ACCESS_LOCK:
        data = load_user_access_data()
        user = data["users"].get(user_key, {
            "telegram_user_id": user_id,
            "state": "NEW",
            "created_at": datetime.now(TIMEZONE).isoformat(),
        })
        user.update(changes)
        user["updated_at"] = datetime.now(TIMEZONE).isoformat()
        data["users"][user_key] = user
        save_user_access_data(data)
        return dict(user)


def uid_owner(uid, excluding_user_id=None):
    normalized = str(uid).strip().upper()
    data = load_user_access_data()
    for user_key, user in data.get("users", {}).items():
        if excluding_user_id is not None and user_key == str(excluding_user_id):
            continue
        if str(user.get("broker_uid", "")).strip().upper() == normalized:
            return user_key
    return None


def set_gift_document(document, admin_user_id):
    data = load_user_access_data()
    data["gift"] = {
        "file_id": document["file_id"],
        "file_unique_id": document.get("file_unique_id"),
        "file_name": document.get("file_name", "Apex_Trader_Money_Management.xlsx"),
        "mime_type": document.get("mime_type"),
        "version": datetime.now(TIMEZONE).strftime("%Y%m%d-%H%M%S"),
        "uploaded_by": admin_user_id,
        "uploaded_at": datetime.now(TIMEZONE).isoformat(),
    }
    save_user_access_data(data)
    return dict(data["gift"])


def get_gift_document():
    return dict(load_user_access_data().get("gift", {}))


def affiliate_request(url, payload):
    headers = {"Accept": "application/json"}
    if AFFILIATE_API_KEY:
        headers["Authorization"] = f"Bearer {AFFILIATE_API_KEY}"
        headers["X-API-Key"] = AFFILIATE_API_KEY
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("Affiliate API returned an invalid response.")
    return result


def verify_uid_with_provider(uid, user_id):
    if not UID_VERIFY_URL:
        return {"status": "manual_review"}
    result = affiliate_request(UID_VERIFY_URL, {
        "uid": uid,
        "telegram_user_id": user_id,
    })
    status = str(result.get("status", "")).lower()
    verified = bool(
        result.get("verified")
        or result.get("account_verified")
        or status in {"verified", "approved", "success"}
    )
    return {
        "status": "verified" if verified else (status or "not_verified"),
        "reference": result.get("reference") or result.get("id"),
    }


def verify_deposit_with_provider(uid, user_id):
    if not DEPOSIT_VERIFY_URL:
        return {"status": "manual_review", "amount": 0.0}
    result = affiliate_request(DEPOSIT_VERIFY_URL, {
        "uid": uid,
        "telegram_user_id": user_id,
        "required_amount": REQUIRED_DEPOSIT_AMOUNT,
        "currency": DEPOSIT_CURRENCY,
    })
    raw_amount = (
        result.get("deposit_amount")
        if result.get("deposit_amount") is not None
        else result.get("total_deposit", result.get("amount", 0))
    )
    try:
        amount = float(raw_amount or 0)
    except (TypeError, ValueError):
        amount = 0.0
    status = str(result.get("status", "")).lower()
    verified = bool(
        result.get("verified")
        or result.get("deposit_verified")
        or status in {"verified", "approved", "success"}
        or (REQUIRED_DEPOSIT_AMOUNT > 0 and amount >= REQUIRED_DEPOSIT_AMOUNT)
    )
    return {
        "status": "verified" if verified else (status or "not_verified"),
        "amount": amount,
        "reference": result.get("reference") or result.get("id"),
    }


# ============================================================
# ANSWER CALLBACK
# ============================================================

def answer_callback(
    callback_query_id,
    text=None
):

    payload = {
        "callback_query_id":
            callback_query_id
    }

    if text:

        payload[
            "text"
        ] = text

    try:

        telegram_request(
            "answerCallbackQuery",
            payload
        )

    except Exception as e:

        print(
            f"Telegram callback error: {e}",
            flush=True
        )


# ============================================================
# EDIT MESSAGE
# ============================================================

def edit_message(
    chat_id,
    message_id,
    text,
    reply_markup=None
):

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    if reply_markup:

        payload[
            "reply_markup"
        ] = reply_markup

    return telegram_request(
        "editMessageText",
        payload
    )


# ============================================================
# KEYBOARD
# ============================================================

def dashboard_keyboard():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "▶️ START AUTOMATION",
                    "callback_data": "start"
                },

                {
                    "text": "⏹ STOP AUTOMATION",
                    "callback_data": "stop"
                }
            ],

            [
                {
                    "text": "📊 DASHBOARD",
                    "callback_data": "dashboard"
                },

                {
                    "text": "📦 BUFFER",
                    "callback_data": "buffer"
                }
            ],

            [
                {
                    "text": "📅 SCHEDULE",
                    "callback_data": "schedule"
                },

                {
                    "text": "🎬 TODAY",
                    "callback_data": "today"
                }
            ],

            [
                {
                    "text": "❌ ERRORS",
                    "callback_data": "errors"
                },

                {
                    "text": "📋 LOGS",
                    "callback_data": "logs"
                }
            ],

            [
                {
                    "text": "🧪 TEST",
                    "callback_data": "test"
                },

                {
                    "text": "🔄 REFRESH",
                    "callback_data": "refresh"
                }
            ],

            [
                {
                    "text": "👥 USERS",
                    "callback_data": "users"
                },

                {
                    "text": "🎁 GIFT SETUP",
                    "callback_data": "gift_setup"
                }
            ]
        ]
    }


def user_home_keyboard():
    rows = []
    if ACCOUNT_REGISTRATION_URL:
        rows.append([{
            "text": "📝 Create Trading Account",
            "url": ACCOUNT_REGISTRATION_URL,
        }])
    rows.append([{
        "text": "✅ I Created My Account",
        "callback_data": "user:submit_uid",
    }])
    rows.append([{
        "text": "📊 Check My Status",
        "callback_data": "user:status",
    }])
    return {"inline_keyboard": rows}


def claim_gift_keyboard():
    return {"inline_keyboard": [[{
        "text": "🎁 Claim Free Money Management Sheet",
        "callback_data": "user:claim_gift",
    }]]}


def gift_received_keyboard():
    return {"inline_keyboard": [[{
        "text": "✅ I Downloaded My Gift",
        "callback_data": "user:gift_received",
    }]]}


def start_trading_keyboard():
    return {"inline_keyboard": [[{
        "text": "🚀 Start Trading",
        "callback_data": "user:start_trading",
    }]]}


def deposit_pending_keyboard():
    rows = []
    if ACCOUNT_REGISTRATION_URL:
        rows.append([{
            "text": "💳 Deposit Now",
            "url": ACCOUNT_REGISTRATION_URL,
        }])
    rows.append([{
        "text": "🔄 Check Deposit Again",
        "callback_data": "user:check_deposit",
    }])
    if SUPPORT_USERNAME:
        rows.append([{
            "text": "💬 Contact Support",
            "url": f"https://t.me/{SUPPORT_USERNAME}",
        }])
    return {"inline_keyboard": rows}


def access_keyboard():
    if not TRADING_ACCESS_URL:
        return None
    return {"inline_keyboard": [[{
        "text": "📈 Open Trading Access",
        "url": TRADING_ACCESS_URL,
    }]]}


def admin_review_keyboard(kind, user_id):
    return {"inline_keyboard": [[
        {
            "text": "✅ Approve",
            "callback_data": f"admin:{kind}:approve:{user_id}",
        },
        {
            "text": "❌ Reject",
            "callback_data": f"admin:{kind}:reject:{user_id}",
        },
    ]]}


def user_welcome_text(first_name=None):
    greeting = f"Hi {first_name}!" if first_name else "Welcome!"
    return (
        f"👋 {greeting}\n\n"
        "Create your trading account using our registration link, then "
        "verify your UID to unlock a free Apex Trader Money Management Sheet.\n\n"
        "After receiving the gift, verify the required deposit to unlock "
        "trading access."
    )


def user_status_text(user):
    state = user.get("state", "NEW")
    labels = {
        "NEW": "Account registration not verified",
        "AWAITING_UID": "Waiting for your UID",
        "UID_PENDING": "UID is awaiting verification",
        "UID_VERIFIED": "UID verified — gift available",
        "GIFT_SENT": "Gift delivered — confirm download",
        "GIFT_ACKNOWLEDGED": "Gift confirmed — start trading",
        "DEPOSIT_PENDING": "Waiting for the required deposit",
        "DEPOSIT_VERIFIED": "Deposit verified",
        "ACCESS_GRANTED": "Trading access granted",
        "MANUAL_REVIEW": "Waiting for admin review",
        "REJECTED": "Verification rejected",
    }
    return "📊 YOUR STATUS\n\n" + labels.get(state, state)


def notify_admin_review(kind, user):
    uid = user.get("broker_uid", "Unknown")
    name = user.get("first_name") or user.get("username") or "Unknown"
    heading = "UID VERIFICATION" if kind == "uid" else "DEPOSIT VERIFICATION"
    extra = ""
    if kind == "deposit":
        extra = (
            f"\nRequired: {REQUIRED_DEPOSIT_AMOUNT:g} {DEPOSIT_CURRENCY}"
        )
    send_message(
        TELEGRAM_ADMIN_CHAT_ID,
        f"🛡 {heading} REVIEW\n\n"
        f"User: {name}\n"
        f"Telegram ID: {user['telegram_user_id']}\n"
        f"UID: {uid}{extra}",
        admin_review_keyboard(kind, user["telegram_user_id"]),
    )


def grant_access(user_id):
    user = update_user_record(
        user_id,
        state="ACCESS_GRANTED",
        access_granted_at=datetime.now(TIMEZONE).isoformat(),
    )
    text = (
        "✅ DEPOSIT VERIFIED\n\n"
        "Your trading access is now active."
    )
    if not TRADING_ACCESS_URL:
        text += "\n\nAn administrator will send your private access link."
    send_message(user_id, text, access_keyboard())
    return user


def deliver_gift(user_id):
    gift = get_gift_document()
    file_id = gift.get("file_id")
    if not file_id:
        send_message(
            user_id,
            "Your account is verified, but the gift is being updated. "
            "Please try again shortly.",
            claim_gift_keyboard(),
        )
        return False
    result = send_document(
        user_id,
        file_id,
        caption=(
            "🎁 Apex Trader Money Management Sheet\n\n"
            "Use this sheet to plan risk, position size, daily limits, "
            "and trading targets."
        ),
        reply_markup=gift_received_keyboard(),
    )
    message_id = result.get("result", {}).get("message_id")
    update_user_record(
        user_id,
        state="GIFT_SENT",
        gift_version=gift.get("version"),
        gift_message_id=message_id,
        gift_sent_at=datetime.now(TIMEZONE).isoformat(),
    )
    return True


# ============================================================
# AUTOMATION STATE
# ============================================================

def load_automation_state():

    if not os.path.exists(
        AUTOMATION_STATE_FILE
    ):

        return {
            "enabled": True,
            "last_error": None,
            "last_error_time": None,
            "last_update": None
        }

    try:

        with open(
            AUTOMATION_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict
        ):

            return {
                "enabled": True,
                "last_error": None,
                "last_error_time": None,
                "last_update": None
            }

        return data

    except Exception as e:

        print(
            f"Automation state read error: {e}",
            flush=True
        )

        return {
            "enabled": True,
            "last_error": None,
            "last_error_time": None,
            "last_update": None
        }


def save_automation_state(
    state
):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    state[
        "last_update"
    ] = datetime.now(
        TIMEZONE
    ).isoformat()

    temp_file = (
        AUTOMATION_STATE_FILE
        + ".tmp"
    )

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            state,
            file,
            indent=2
        )

    os.replace(
        temp_file,
        AUTOMATION_STATE_FILE
    )


def set_automation_enabled(
    enabled
):

    with AUTOMATION_LOCK:

        state = (
            load_automation_state()
        )

        state[
            "enabled"
        ] = bool(
            enabled
        )

        save_automation_state(
            state
        )

        return state


# ============================================================
# BUFFER
# ============================================================

def load_buffer():

    if not os.path.exists(
        BUFFER_FILE
    ):

        return {
            "slots": []
        }

    try:

        with open(
            BUFFER_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(
                file
            )

    except Exception:

        return {
            "slots": []
        }


# ============================================================
# BUFFER SUMMARY
# ============================================================

def get_buffer_summary():

    data = load_buffer()

    slots = data.get(
        "slots",
        []
    )

    now = datetime.now(
        TIMEZONE
    )

    future_slots = []

    for slot in slots:

        publish_at_string = (
            slot.get(
                "publish_at"
            )
        )

        if not publish_at_string:
            continue

        try:

            publish_at = (
                datetime.fromisoformat(
                    publish_at_string
                )
            )

        except Exception:

            continue

        if publish_at >= now:

            future_slots.append(
                slot
            )

    future_slots.sort(
        key=lambda x:
            x.get(
                "publish_at",
                ""
            )
    )

    return future_slots


# ============================================================
# FORMAT DASHBOARD
# ============================================================

def dashboard_text():

    state = (
        load_automation_state()
    )

    slots = (
        get_buffer_summary()
    )

    status = (
        "🟢 LIVE"
        if state.get(
            "enabled",
            True
        )
        else
        "🔴 PAUSED"
    )

    text = (
        "🤖 POCKET OPTION AUTOMATION\n"
        "\n"
        f"⚙️ STATUS: {status}\n"
        "\n"
        "📦 BUFFER\n"
        f"{len(slots)} future video(s) scheduled\n"
        "\n"
        "📅 UPCOMING\n"
    )

    if not slots:

        text += (
            "No future Shorts found.\n"
        )

    else:

        for index, slot in enumerate(
            slots[:5],
            start=1
        ):

            publish_at = (
                slot.get(
                    "publish_at",
                    "Unknown"
                )
            )

            title = (
                slot.get(
                    "title",
                    "Untitled"
                )
            )

            video_id = (
                slot.get(
                    "video_id",
                    "Unknown"
                )
            )

            text += (
                f"\n{index}. "
                f"{publish_at}\n"
                f"📺 {slot.get('channel', 'default')}\n"
            f"🎬 {title}\n"
                f"🆔 {video_id}\n"
            )

    text += (
        "\n"
        "🟢 Telegram: Connected\n"
        "🟢 Buffer: Active\n"
        "🟢 YouTube: Connected\n"
    )

    if state.get(
        "last_error"
    ):

        text += (
            "\n"
            "❌ LAST ERROR\n"
            f"{state['last_error']}\n"
        )

    else:

        text += (
            "\n"
            "❌ ERRORS: None"
        )

    return text


# ============================================================
# BUFFER TEXT
# ============================================================

def buffer_text():

    slots = (
        get_buffer_summary()
    )

    text = (
        "📦 1-DAY BUFFER\n"
        "\n"
        f"Future scheduled Shorts: "
        f"{len(slots)}\n"
        "\n"
    )

    if not slots:

        text += (
            "❌ No scheduled Shorts."
        )

        return text

    for index, slot in enumerate(
        slots,
        start=1
    ):

        text += (
            f"{index}. [{slot.get('channel', 'default')}] "
            f"{slot.get('publish_at', 'Unknown')}\n"
        )

        text += (
            f"🎬 "
            f"{slot.get('title', 'Untitled')}\n"
        )

        text += (
            f"🆔 "
            f"{slot.get('video_id', 'Unknown')}\n"
        )

        text += (
            f"📊 "
            f"{slot.get('status', 'unknown').upper()}\n\n"
        )

    return text


# ============================================================
# SCHEDULE TEXT
# ============================================================

def schedule_text():

    slots = (
        get_buffer_summary()
    )

    text = (
        "📅 UPCOMING SCHEDULE\n"
        "\n"
    )

    if not slots:

        return (
            text
            + "No scheduled videos."
        )

    for slot in slots:

        publish_at = (
            slot.get(
                "publish_at",
                "Unknown"
            )
        )

        title = (
            slot.get(
                "title",
                "Untitled"
            )
        )

        text += (
            f"🕐 {publish_at}\n"
            f"📺 {slot.get('channel', 'default')}\n"
            f"🎬 {title}\n"
            f"🟢 {slot.get('status', 'unknown').upper()}\n\n"
        )

    return text


# ============================================================
# TODAY TEXT
# ============================================================

def today_text():

    today = datetime.now(
        TIMEZONE
    ).date()

    data = load_buffer()

    slots = data.get(
        "slots",
        []
    )

    today_slots = []

    for slot in slots:

        publish_at_string = (
            slot.get(
                "publish_at"
            )
        )

        if not publish_at_string:
            continue

        try:

            publish_at = (
                datetime.fromisoformat(
                    publish_at_string
                )
            )

        except Exception:

            continue

        if publish_at.date() == today:

            today_slots.append(
                slot
            )

    text = (
        "🎬 TODAY\n"
        "\n"
    )

    if not today_slots:

        text += (
            "No buffer videos for today."
        )

        return text

    for slot in today_slots:

        text += (
            f"🕐 {slot.get('publish_at', 'Unknown')}\n"
            f"🎬 {slot.get('title', 'Untitled')}\n"
            f"🆔 {slot.get('video_id', 'Unknown')}\n"
            f"📊 {slot.get('status', 'unknown').upper()}\n\n"
        )

    return text


# ============================================================
# ERROR TEXT
# ============================================================

def error_text():

    state = (
        load_automation_state()
    )

    error = (
        state.get(
            "last_error"
        )
    )

    error_time = (
        state.get(
            "last_error_time"
        )
    )

    if not error:

        return (
            "❌ ERRORS\n"
            "\n"
            "✅ No errors recorded."
        )

    return (
        "❌ LAST ERROR\n"
        "\n"
        f"Time: {error_time}\n"
        "\n"
        f"{error}"
    )


# ============================================================
# LOG TEXT
# ============================================================

def log_text():

    state = (
        load_automation_state()
    )

    return (
        "📋 SYSTEM LOG\n"
        "\n"
        f"Status: "
        f"{'LIVE' if state.get('enabled', True) else 'PAUSED'}\n"
        "\n"
        f"Last update:\n"
        f"{state.get('last_update', 'Unknown')}\n"
        "\n"
        "Buffer file:\n"
        f"{BUFFER_FILE}"
    )


# ============================================================
# START / STOP ACTIONS
# ============================================================

def handle_start():

    state = (
        set_automation_enabled(
            True
        )
    )

    return (
        "▶️ AUTOMATION STARTED\n"
        "\n"
        "Status: 🟢 LIVE\n"
        "\n"
        "The automation is enabled again."
    )


def handle_stop():

    state = (
        set_automation_enabled(
            False
        )
    )

    return (
        "⏹ AUTOMATION PAUSED\n"
        "\n"
        "Status: 🔴 PAUSED\n"
        "\n"
        "New automatic Shorts will not be created "
        "while automation is paused.\n"
        "\n"
        "Already scheduled YouTube videos are "
        "not cancelled."
    )


# ============================================================
# TEST ACTION
# ============================================================

def start_test():

    try:

        from app.main import (
            run_short_background
        )

        run_short_background(
            "TELEGRAM TEST"
        )

        return (
            "🧪 TEST STARTED\n"
            "\n"
            "A manual test Short has started "
            "in the background.\n"
            "\n"
            "Test uploads remain UNLISTED."
        )

    except Exception as e:

        record_error(
            e
        )

        return (
            "❌ TEST FAILED TO START\n"
            "\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# RECORD ERROR
# ============================================================

def record_error(
    error
):

    try:

        state = (
            load_automation_state()
        )

        state[
            "last_error"
        ] = (
            f"{type(error).__name__}: "
            f"{str(error)}"
        )

        state[
            "last_error_time"
        ] = datetime.now(
            TIMEZONE
        ).isoformat()

        save_automation_state(
            state
        )

    except Exception as e:

        print(
            f"Could not save Telegram error: {e}",
            flush=True
        )


# ============================================================
# HANDLE CALLBACK
# ============================================================

def handle_user_callback(callback_id, user_id, profile, data):
    user = get_user_record(user_id, profile)

    if data == "user:submit_uid":
        if user.get("state") in {
            "UID_VERIFIED", "GIFT_SENT", "GIFT_ACKNOWLEDGED",
            "DEPOSIT_PENDING", "DEPOSIT_VERIFIED", "ACCESS_GRANTED",
        }:
            answer_callback(callback_id, "Your UID is already verified.")
            send_message(user_id, user_status_text(user))
            return
        update_user_record(user_id, state="AWAITING_UID")
        answer_callback(callback_id)
        send_message(
            user_id,
            "Send your trading account UID now.\n\n"
            "Only send the UID — never send your password, OTP, or payment details.",
        )
        return

    if data == "user:status":
        answer_callback(callback_id)
        send_message(user_id, user_status_text(user), user_home_keyboard())
        return

    if data == "user:claim_gift":
        if user.get("state") != "UID_VERIFIED":
            if user.get("state") in {
                "GIFT_SENT", "GIFT_ACKNOWLEDGED", "DEPOSIT_PENDING",
                "DEPOSIT_VERIFIED", "ACCESS_GRANTED",
            }:
                answer_callback(callback_id, "Your gift was already delivered.")
                return
            answer_callback(callback_id, "Verify your UID first.")
            return
        answer_callback(callback_id, "Preparing your gift…")
        deliver_gift(user_id)
        return

    if data == "user:gift_received":
        if user.get("state") != "GIFT_SENT":
            if user.get("state") in {
                "GIFT_ACKNOWLEDGED", "DEPOSIT_PENDING",
                "DEPOSIT_VERIFIED", "ACCESS_GRANTED",
            }:
                answer_callback(callback_id, "Gift already confirmed.")
                return
            answer_callback(callback_id, "Claim the gift first.")
            return
        update_user_record(
            user_id,
            state="GIFT_ACKNOWLEDGED",
            gift_acknowledged_at=datetime.now(TIMEZONE).isoformat(),
        )
        answer_callback(callback_id, "Gift confirmed!")
        send_message(
            user_id,
            "✅ Gift confirmed.\n\n"
            "When you are ready, tap Start Trading. We will verify your "
            "deposit before granting access.",
            start_trading_keyboard(),
        )
        return

    if data in {"user:start_trading", "user:check_deposit"}:
        if user.get("state") not in {
            "GIFT_ACKNOWLEDGED", "DEPOSIT_PENDING",
            "DEPOSIT_VERIFIED", "ACCESS_GRANTED",
        }:
            answer_callback(callback_id, "Download and confirm the gift first.")
            return
        if user.get("state") == "ACCESS_GRANTED":
            answer_callback(callback_id, "Access is already active.")
            send_message(
                user_id,
                "✅ Your trading access is already active.",
                access_keyboard(),
            )
            return
        answer_callback(callback_id, "Checking your deposit…")
        try:
            verification = verify_deposit_with_provider(
                user.get("broker_uid"), user_id
            )
        except Exception as error:
            record_error(error)
            send_message(
                user_id,
                "Deposit verification is temporarily unavailable. "
                "Please try again shortly.",
                deposit_pending_keyboard(),
            )
            return
        if verification["status"] == "verified":
            update_user_record(
                user_id,
                deposit_amount=verification.get("amount", 0),
                deposit_reference=verification.get("reference"),
                deposit_verified_at=datetime.now(TIMEZONE).isoformat(),
            )
            grant_access(user_id)
            return
        update_user_record(
            user_id,
            state="DEPOSIT_PENDING",
            deposit_amount=verification.get("amount", 0),
            deposit_checked_at=datetime.now(TIMEZONE).isoformat(),
        )
        if verification["status"] == "manual_review":
            notify_admin_review("deposit", get_user_record(user_id))
            send_message(
                user_id,
                "Your deposit was submitted for verification. "
                "We will notify you after review.",
                deposit_pending_keyboard(),
            )
            return
        amount = verification.get("amount", 0)
        send_message(
            user_id,
            "⏳ DEPOSIT NOT VERIFIED YET\n\n"
            f"Required: {REQUIRED_DEPOSIT_AMOUNT:g} {DEPOSIT_CURRENCY}\n"
            f"Confirmed: {amount:g} {DEPOSIT_CURRENCY}\n\n"
            "Complete the required deposit, then check again.",
            deposit_pending_keyboard(),
        )
        return

    answer_callback(callback_id, "Unknown action")


def handle_admin_review_callback(callback_id, admin_id, data):
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "admin":
        answer_callback(callback_id, "Invalid review action")
        return
    _, kind, decision, user_id_text = parts
    if kind not in {"uid", "deposit"} or decision not in {"approve", "reject"}:
        answer_callback(callback_id, "Invalid review action")
        return
    try:
        user_id = int(user_id_text)
    except ValueError:
        answer_callback(callback_id, "Invalid user")
        return
    user = get_user_record(user_id)
    if decision == "reject":
        update_user_record(
            user_id,
            state="REJECTED" if kind == "uid" else "DEPOSIT_PENDING",
            last_reviewed_by=admin_id,
            last_reviewed_at=datetime.now(TIMEZONE).isoformat(),
        )
        answer_callback(callback_id, "Rejected")
        send_message(
            user_id,
            "❌ Verification was not approved. Please check your details "
            "or contact support.",
            user_home_keyboard() if kind == "uid" else deposit_pending_keyboard(),
        )
        return
    if kind == "uid":
        update_user_record(
            user_id,
            state="UID_VERIFIED",
            uid_verified_at=datetime.now(TIMEZONE).isoformat(),
            last_reviewed_by=admin_id,
        )
        answer_callback(callback_id, "UID approved")
        send_message(
            user_id,
            "✅ ACCOUNT VERIFIED\n\n"
            "Your free Apex Trader Money Management Sheet is ready.",
            claim_gift_keyboard(),
        )
        return
    update_user_record(
        user_id,
        state="DEPOSIT_VERIFIED",
        deposit_verified_at=datetime.now(TIMEZONE).isoformat(),
        last_reviewed_by=admin_id,
    )
    answer_callback(callback_id, "Deposit approved")
    grant_access(user_id)

def handle_callback(
    callback_query
):

    callback_id = (
        callback_query.get(
            "id"
        )
    )

    from_user = (
        callback_query.get(
            "from",
            {}
        )
    )

    user_id = (
        from_user.get(
            "id"
        )
    )

    data = (
        callback_query.get(
            "data",
            ""
        )
    )

    message = (
        callback_query.get(
            "message",
            {}
        )
    )

    chat = (
        message.get(
            "chat",
            {}
        )
    )

    chat_id = (
        chat.get(
            "id"
        )
    )

    message_id = (
        message.get(
            "message_id"
        )
    )

    if data.startswith("user:"):
        handle_user_callback(
            callback_id,
            user_id,
            from_user,
            data,
        )
        return

    if data.startswith("admin:"):
        if not is_admin(user_id):
            answer_callback(callback_id, "⛔ Unauthorized")
            return
        handle_admin_review_callback(callback_id, user_id, data)
        return

    if not is_admin(user_id):
        answer_callback(callback_id, "⛔ Unauthorized")
        return


    answer_callback(
        callback_id
    )


    if data == "start":

        text = handle_start()

    elif data == "stop":

        text = handle_stop()

    elif data in [
        "dashboard",
        "refresh"
    ]:

        text = dashboard_text()

    elif data == "buffer":

        text = buffer_text()

    elif data == "schedule":

        text = schedule_text()

    elif data == "today":

        text = today_text()

    elif data == "errors":

        text = error_text()

    elif data == "logs":

        text = log_text()

    elif data == "test":

        text = start_test()

    elif data == "users":

        text = admin_users_text()

    elif data == "gift_setup":

        gift = get_gift_document()
        if gift:
            text = (
                "🎁 GIFT SETUP\n\n"
                f"Current file: {gift.get('file_name', 'Unknown')}\n"
                f"Version: {gift.get('version', 'Unknown')}\n\n"
                "To replace it, send the Excel file to this bot and put "
                "/setgift in the file caption."
            )
        else:
            text = (
                "🎁 GIFT SETUP\n\n"
                "No Excel gift has been uploaded.\n\n"
                "Send the .xlsx or .xls file to this bot and put /setgift "
                "in the file caption."
            )

    else:

        text = dashboard_text()


    try:

        if chat_id and message_id:

            edit_message(
                chat_id,
                message_id,
                text,
                dashboard_keyboard()
            )

        elif chat_id:

            send_message(
                chat_id,
                text,
                dashboard_keyboard()
            )

    except Exception as e:

        print(
            f"Telegram message update error: {e}",
            flush=True
        )


# ============================================================
# HANDLE MESSAGE
# ============================================================

def handle_uid_submission(message, user):
    user_id = user["telegram_user_id"]
    uid = str(message.get("text", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", uid):
        send_message(
            user_id,
            "That UID format is not valid. Send only the UID shown in your "
            "trading account profile.",
        )
        return
    if uid_owner(uid, excluding_user_id=user_id):
        send_message(
            user_id,
            "This UID is already linked to another Telegram account. "
            "Contact support if you believe this is a mistake.",
        )
        return
    update_user_record(
        user_id,
        broker_uid=uid,
        state="UID_PENDING",
        uid_submitted_at=datetime.now(TIMEZONE).isoformat(),
    )
    send_message(user_id, "🔍 Checking your account UID…")
    try:
        verification = verify_uid_with_provider(uid, user_id)
    except Exception as error:
        record_error(error)
        update_user_record(user_id, state="UID_PENDING")
        send_message(
            user_id,
            "UID verification is temporarily unavailable. Your UID was saved; "
            "please check again shortly.",
            user_home_keyboard(),
        )
        return
    if verification["status"] == "verified":
        update_user_record(
            user_id,
            state="UID_VERIFIED",
            uid_reference=verification.get("reference"),
            uid_verified_at=datetime.now(TIMEZONE).isoformat(),
        )
        send_message(
            user_id,
            "✅ ACCOUNT VERIFIED\n\n"
            "Your free Apex Trader Money Management Sheet is ready.",
            claim_gift_keyboard(),
        )
        return
    if verification["status"] == "manual_review":
        notify_admin_review("uid", get_user_record(user_id))
        send_message(
            user_id,
            "Your UID was submitted successfully and is awaiting verification. "
            "We will notify you when it is approved.",
        )
        return
    send_message(
        user_id,
        "We could not verify this UID through the registration campaign yet. "
        "Confirm the UID and try again after a few minutes.",
        user_home_keyboard(),
    )


def admin_users_text():
    users = list(load_user_access_data().get("users", {}).values())
    counts = {}
    for user in users:
        state = user.get("state", "NEW")
        counts[state] = counts.get(state, 0) + 1
    lines = ["👥 USER ACCESS SUMMARY", "", f"Total users: {len(users)}"]
    for state in sorted(counts):
        lines.append(f"{state}: {counts[state]}")
    gift = get_gift_document()
    lines.extend([
        "",
        "Gift: " + (gift.get("file_name") or "Not uploaded"),
        "",
        "Upload or replace the Excel gift by sending it to this bot with "
        "the caption /setgift.",
    ])
    return "\n".join(lines)

def handle_message(
    message
):

    chat = (
        message.get(
            "chat",
            {}
        )
    )

    chat_id = (
        chat.get(
            "id"
        )
    )

    text = (
        message.get(
            "text",
            ""
        )
    )

    caption = str(message.get("caption", ""))

    if is_admin(chat_id):
        if caption.startswith("/setgift") or text.startswith("/setgift"):
            document = message.get("document")
            if not document:
                send_message(
                    chat_id,
                    "Attach the .xlsx or .xls file and put /setgift in its caption.",
                )
                return
            file_name = str(document.get("file_name", "")).lower()
            if not file_name.endswith((".xlsx", ".xls")):
                send_message(chat_id, "Only Excel .xlsx or .xls files are accepted.")
                return
            gift = set_gift_document(document, chat_id)
            send_message(
                chat_id,
                "✅ GIFT UPLOADED\n\n"
                f"File: {gift['file_name']}\n"
                f"Version: {gift['version']}\n\n"
                "Verified users can now claim this file.",
            )
            return

        if text.startswith("/users"):
            send_message(chat_id, admin_users_text(), dashboard_keyboard())
            return

        if text.startswith("/start"):
            send_message(chat_id, dashboard_text(), dashboard_keyboard())
            return

        if text.startswith("/dashboard"):
            send_message(chat_id, dashboard_text(), dashboard_keyboard())
            return

        if text.startswith("/buffer"):
            send_message(chat_id, buffer_text(), dashboard_keyboard())
            return

        if text.startswith("/schedule"):
            send_message(chat_id, schedule_text(), dashboard_keyboard())
            return

        if text.startswith("/today"):
            send_message(chat_id, today_text(), dashboard_keyboard())
            return

        if text.startswith("/errors"):
            send_message(chat_id, error_text(), dashboard_keyboard())
            return

        send_message(chat_id, dashboard_text(), dashboard_keyboard())
        return

    profile = message.get("from", {})
    user = get_user_record(chat_id, profile)

    if text.startswith("/start"):
        send_message(
            chat_id,
            user_welcome_text(user.get("first_name")),
            user_home_keyboard(),
        )
        return

    if text.startswith("/status"):
        send_message(chat_id, user_status_text(user), user_home_keyboard())
        return

    if user.get("state") == "AWAITING_UID":
        handle_uid_submission(message, user)
        return

    send_message(
        chat_id,
        user_status_text(user),
        user_home_keyboard(),
    )


# ============================================================
# TELEGRAM UPDATE
# ============================================================

def process_update(
    update
):

    try:

        callback_query = (
            update.get(
                "callback_query"
            )
        )

        if callback_query:

            handle_callback(
                callback_query
            )

            return

        message = (
            update.get(
                "message"
            )
        )

        if message:

            handle_message(
                message
            )

    except Exception as e:

        print(
            f"Telegram update error: {e}",
            flush=True
        )

        record_error(
            e
        )


# ============================================================
# WEBHOOK
# ============================================================

def telegram_webhook(
    request
):

    if not telegram_configured():

        return {
            "ok": False,
            "error":
                "Telegram variables missing."
        }

    secret_header = (
        request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )
    )

    if secret_header != (
        TELEGRAM_WEBHOOK_SECRET
    ):

        return {
            "ok": False,
            "error": "Unauthorized"
        }

    update = request.get_json(
        silent=True
    )

    if not update:

        return {
            "ok": True
        }

    thread = threading.Thread(
        target=process_update,
        args=(update,),
        daemon=True
    )

    thread.start()

    return {
        "ok": True
    }


# ============================================================
# SET WEBHOOK
# ============================================================

def set_webhook(
    webhook_url
):

    if not telegram_configured():

        raise RuntimeError(
            "Telegram configuration missing."
        )

    result = telegram_request(
        "setWebhook",
        {
            "url": webhook_url,

            "secret_token":
                TELEGRAM_WEBHOOK_SECRET,

            "allowed_updates": [
                "message",
                "callback_query"
            ],

            "drop_pending_updates": True
        }
    )

    print(
        "Telegram webhook configured.",
        flush=True
    )

    return result


# ============================================================
# TELEGRAM BOT STARTUP
# ============================================================

def initialize_telegram(
    public_base_url
):

    if not telegram_configured():

        print(
            "Telegram disabled: "
            "TELEGRAM_BOT_TOKEN or "
            "TELEGRAM_ADMIN_CHAT_ID missing.",
            flush=True
        )

        return False

    webhook_url = (
        public_base_url.rstrip("/")
        + "/telegram/webhook/"
        + TELEGRAM_WEBHOOK_SECRET
    )

    try:

        set_webhook(
            webhook_url
        )

        send_message(
            TELEGRAM_ADMIN_CHAT_ID,
            dashboard_text(),
            dashboard_keyboard()
        )

        print(
            "Telegram bot initialized.",
            flush=True
        )

        print(
            f"Webhook: {webhook_url}",
            flush=True
        )

        return True

    except Exception as e:

        print(
            f"Telegram initialization failed: {e}",
            flush=True
        )

        record_error(
            e
        )

        return False
