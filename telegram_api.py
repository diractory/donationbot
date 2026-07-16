import requests
import config


def _post(method, payload=None):
    url = f"{config.TELEGRAM_API}/{method}"
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"[telegram_api] {method} failed: {e}")
        return {"ok": False, "error": str(e)}


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("sendMessage", payload)


def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("editMessageText", payload)


def edit_message_caption(chat_id, message_id, caption, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": caption,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("editMessageCaption", payload)


def delete_message(chat_id, message_id):
    return _post("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


def send_photo(chat_id, photo, caption=None, reply_markup=None, parse_mode="HTML"):
    """`photo` can be either a Telegram file_id or a public https URL."""
    payload = {"chat_id": chat_id, "photo": photo}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("sendPhoto", payload)


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    return _post("answerCallbackQuery", payload)


def set_webhook(url, secret_token=None):
    payload = {"url": url, "allowed_updates": ["message", "callback_query"]}
    if secret_token:
        payload["secret_token"] = secret_token
    return _post("setWebhook", payload)


def set_my_commands(commands, scope=None):
    payload = {"commands": commands}
    if scope:
        payload["scope"] = scope
    return _post("setMyCommands", payload)
