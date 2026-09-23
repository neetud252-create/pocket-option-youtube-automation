import os
import json
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

DATA_DIR = "/app/data"

BUFFER_FILE = os.path.join(
    DATA_DIR,
    "buffer_queue.json"
)

AUTOMATION_STATE_FILE = os.path.join(
    DATA_DIR,
    "automation_state.json"
)

TIMEZONE = ZoneInfo(
    "Asia/Kolkata"
)

AUTOMATION_LOCK = threading.Lock()


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
            ]
        ]
    }


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
            f"{index}. "
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

    if not is_admin(
        user_id
    ):

        answer_callback(
            callback_id,
            "⛔ Unauthorized"
        )

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

    if not is_admin(
        chat_id
    ):

        return

    text = (
        message.get(
            "text",
            ""
        )
    )

    if text.startswith(
        "/start"
    ):

        send_message(
            chat_id,
            dashboard_text(),
            dashboard_keyboard()
        )

    elif text.startswith(
        "/dashboard"
    ):

        send_message(
            chat_id,
            dashboard_text(),
            dashboard_keyboard()
        )

    elif text.startswith(
        "/buffer"
    ):

        send_message(
            chat_id,
            buffer_text(),
            dashboard_keyboard()
        )

    elif text.startswith(
        "/schedule"
    ):

        send_message(
            chat_id,
            schedule_text(),
            dashboard_keyboard()
        )

    elif text.startswith(
        "/today"
    ):

        send_message(
            chat_id,
            today_text(),
            dashboard_keyboard()
        )

    elif text.startswith(
        "/errors"
    ):

        send_message(
            chat_id,
            error_text(),
            dashboard_keyboard()
        )

    else:

        send_message(
            chat_id,
            dashboard_text(),
            dashboard_keyboard()
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
