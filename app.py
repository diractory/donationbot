import io
import logging
import threading
import time
from functools import wraps

import requests
from flask import Flask, request, render_template, jsonify, send_file, abort, Response

import config
import db
import qr_fetcher
from bot_handlers import bot  # noqa: F401  (registers all handlers on import)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rdh-helper-hands")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

TELEGRAM_API = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


def _requires_admin_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != config.ADMIN_PANEL_USER or auth.password != config.ADMIN_PANEL_PASSWORD:
            return Response(
                "Login required.", 401, {"WWW-Authenticate": 'Basic realm="RDH Admin"'}
            )
        return f(*args, **kwargs)
    return wrapper


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Telegram webhook
# ---------------------------------------------------------------------------

@app.route(f"/{config.WEBHOOK_SECRET_PATH}", methods=["POST"])
def telegram_webhook():
    import telebot

    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "", 200
    abort(403)


def _ensure_webhook():
    if not config.WEBHOOK_BASE_URL:
        log.warning("No WEBHOOK_BASE_URL / RENDER_EXTERNAL_URL found, skipping webhook registration.")
        return
    url = f"{config.WEBHOOK_BASE_URL.rstrip('/')}/{config.WEBHOOK_SECRET_PATH}"
    try:
        bot.remove_webhook()
        bot.set_webhook(
            url=url,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
        log.info("Telegram webhook set to %s", url)
    except Exception:
        log.exception("Failed to set Telegram webhook (app keeps running regardless)")


def _ensure_webhook_delayed():
    # Give gunicorn a moment to finish booting the worker before we make an
    # outbound call — and do it off the main thread so a slow/failed Telegram
    # API call can never block or crash app startup.
    time.sleep(3)
    _ensure_webhook()


threading.Thread(target=_ensure_webhook_delayed, daemon=True).start()


# ---------------------------------------------------------------------------
# Admin panel — approve/decline from a browser (mainly for website donations)
# ---------------------------------------------------------------------------

@app.route("/admin")
@_requires_admin_auth
def admin_panel():
    return render_template("admin.html")


@app.route("/admin/api/list")
@_requires_admin_auth
def admin_list():
    status = request.args.get("status") or None
    return jsonify({"ok": True, "donations": db.list_donations(status=status)})


@app.route("/admin/api/screenshot/<donation_id>")
@_requires_admin_auth
def admin_screenshot(donation_id):
    d = db.get_donation(donation_id.upper())
    if not d or not d.get("screenshot_file_id"):
        abort(404)
    try:
        r = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": d["screenshot_file_id"]}, timeout=10)
        file_path = r.json()["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_path}"
        img = requests.get(file_url, timeout=10)
        return send_file(io.BytesIO(img.content), mimetype="image/jpeg")
    except Exception:
        log.exception("Failed to fetch screenshot for %s", donation_id)
        abort(502)


@app.route("/admin/api/decide", methods=["POST"])
@_requires_admin_auth
def admin_decide():
    data = request.get_json(force=True, silent=True) or {}
    donation_id = (data.get("donation_id") or "").upper()
    action = data.get("action")

    if action not in ("approve", "decline"):
        return jsonify({"ok": False, "error": "action must be 'approve' or 'decline'"}), 400

    d = db.get_donation(donation_id)
    if not d:
        return jsonify({"ok": False, "error": "Donation not found"}), 404

    status = "approved" if action == "approve" else "declined"
    db.set_donation_status(donation_id, status, decided_by=f"web:{config.ADMIN_PANEL_USER}")

    # Update the channel post too, so it doesn't sit there looking unhandled
    if d.get("channel_message_id"):
        decision_word = "\u2705 APPROVED" if action == "approve" else "\u274C DECLINED"
        try:
            requests.post(
                f"{TELEGRAM_API}/editMessageReplyMarkup",
                data={
                    "chat_id": config.ADMIN_CHANNEL_ID,
                    "message_id": d["channel_message_id"],
                    "reply_markup": "{}",
                },
                timeout=10,
            )
            requests.post(
                f"{TELEGRAM_API}/editMessageCaption",
                data={
                    "chat_id": config.ADMIN_CHANNEL_ID,
                    "message_id": d["channel_message_id"],
                    "parse_mode": "HTML",
                    "caption": f"{d.get('category_label')} \u2014 #{donation_id}\n\n{decision_word} (via website admin panel)",
                },
                timeout=10,
            )
        except Exception:
            log.exception("Failed to update channel post for %s", donation_id)

    # If this donor came from Telegram, message them directly too
    if d.get("source") == "telegram" and d.get("chat_id"):
        if action == "approve":
            text = (
                "Hey, your payment is approved now! \u2705 You'll need to wait about a week (min) as we have "
                "more orders to fulfil before yours \u2014 thank you for your patience and your kindness. \U0001F49B"
            )
        else:
            text = (
                "Hey, unfortunately we couldn't verify your payment and it's been declined. \u274C "
                f"If you think this is a mistake, please reach out to {config.OWNER_HANDLE}."
            )
        try:
            requests.post(f"{TELEGRAM_API}/sendMessage", data={"chat_id": d["chat_id"], "text": text}, timeout=10)
        except Exception:
            log.exception("Failed to notify telegram donor for %s", donation_id)

    return jsonify({"ok": True, "donation_id": donation_id, "status": status})


# ---------------------------------------------------------------------------
# Website
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", categories=config.CATEGORIES, qr_minutes=config.QR_VALID_MINUTES)


@app.route("/api/qr")
def api_qr():
    kind, value, reason = qr_fetcher.get_qr_source()
    if kind == "bytes":
        return send_file(io.BytesIO(value), mimetype="image/jpeg")
    if kind == "file_id":
        try:
            r = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": value}, timeout=10)
            file_path = r.json()["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_path}"
            img = requests.get(file_url, timeout=10)
            return send_file(io.BytesIO(img.content), mimetype="image/jpeg")
        except Exception:
            log.exception("Failed to resolve QR fallback file_id")
            abort(502)
    log.warning("No QR available: %s", reason)
    return jsonify({"ok": False, "error": reason}), 404


@app.route("/set_webhook")
def force_set_webhook():
    _ensure_webhook()
    try:
        r = requests.get(f"{TELEGRAM_API}/getWebhookInfo", timeout=10)
        return jsonify({"ok": True, "webhook_info": r.json().get("result")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/diag")
def diag():
    """One URL to check bot + website + db + QR health at a glance."""
    out = {}

    # Telegram webhook status
    try:
        r = requests.get(f"{TELEGRAM_API}/getWebhookInfo", timeout=10)
        out["telegram_webhook"] = r.json().get("result")
    except Exception as e:
        out["telegram_webhook"] = {"error": str(e)}

    # Mongo connectivity
    try:
        db._client.admin.command("ping")
        out["mongo"] = "ok"
        out["users_count"] = db.count_users()
    except Exception as e:
        out["mongo"] = f"error: {e}"

    # QR status
    kind, _, reason = qr_fetcher.get_qr_source()
    out["qr_source"] = kind or "none"
    out["qr_reason"] = reason
    out["qr_local_path_checked"] = config.QR_LOCAL_PATH

    out["admin_channel_id"] = config.ADMIN_CHANNEL_ID
    out["webhook_expected_url"] = (
        f"{config.WEBHOOK_BASE_URL.rstrip('/')}/{config.WEBHOOK_SECRET_PATH}" if config.WEBHOOK_BASE_URL else None
    )
    return jsonify(out)


@app.route("/api/submit", methods=["POST"])
def api_submit():
    form = request.form
    required = ["category", "amount", "name", "email", "utr"]
    missing = [f for f in required if not form.get(f)]
    if missing:
        return jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    screenshot = request.files.get("screenshot")
    if not screenshot or screenshot.filename == "":
        return jsonify({"ok": False, "error": "Payment screenshot is required."}), 400

    category = form.get("category")
    cat_info = config.CATEGORIES.get(category, {"label": category, "amount": form.get("amount")})

    try:
        amount = float(form.get("amount"))
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid amount."}), 400

    payload = {
        "source": "web",
        "category": category,
        "category_label": cat_info.get("label", category),
        "suggested_amount": cat_info.get("amount"),
        "amount": amount,
        "explanation": form.get("explanation", "-") or "-",
        "name": form.get("name"),
        "instagram": form.get("instagram", "-") or "-",
        "email": form.get("email"),
        "message": form.get("message", "-") or "-",
        "utr": form.get("utr"),
    }
    donation_id = db.create_donation(payload)

    spoiler = (
        f"Name: {payload['name']}\n"
        f"Instagram: {payload['instagram']}\n"
        f"Email: {payload['email']}\n"
        f"Message: {payload['message']}\n"
        f"UTR: {payload['utr']}"
    )
    caption = (
        f"\U0001F514 <b>New donation \u2014 #{donation_id}</b>\n\n"
        f"Source: Website\n"
        f"Category: {payload['category_label']}\n"
        f"Amount: \u20b9{amount:g} (suggested \u20b9{payload['suggested_amount']})\n"
        f"Explanation: {payload['explanation']}\n\n"
        f"<tg-spoiler>{spoiler}</tg-spoiler>"
    )

    tg_message_id = None
    screenshot_file_id = None
    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id": config.ADMIN_CHANNEL_ID,
                "caption": caption,
                "parse_mode": "HTML",
                "has_spoiler": "true",
                "reply_markup": (
                    '{"inline_keyboard": [[{"text": "\u2705 Approve", "callback_data": "appr_%s"}, '
                    '{"text": "\u274C Decline", "callback_data": "decl_%s"}]]}'
                    % (donation_id, donation_id)
                ),
            },
            files={"photo": (screenshot.filename, screenshot.stream, screenshot.mimetype)},
            timeout=20,
        )
        result = r.json().get("result", {})
        tg_message_id = result.get("message_id")
        photos = result.get("photo") or []
        if photos:
            screenshot_file_id = photos[-1]["file_id"]
    except Exception:
        log.exception("Failed to forward web submission to admin channel")

    if tg_message_id or screenshot_file_id:
        db.donations.update_one(
            {"donation_id": donation_id},
            {"$set": {"channel_message_id": tg_message_id, "screenshot_file_id": screenshot_file_id}},
        )

    return jsonify({"ok": True, "donation_id": donation_id})


@app.route("/api/status/<donation_id>")
def api_status(donation_id):
    d = db.get_donation(donation_id.upper())
    if not d:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify(
        {
            "ok": True,
            "donation_id": d["donation_id"],
            "status": d["status"],
            "category_label": d.get("category_label"),
            "amount": d.get("amount"),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
