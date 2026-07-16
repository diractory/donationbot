import os
from flask import Flask, request, jsonify

import config
import handlers
import telegram_api as tg

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "🤖 Donation bot is running.", 200


@app.route(f"/webhook/{config.WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    # Optional extra safety check: Telegram sends this header when a secret
    # token was set via setWebhook.
    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_header and secret_header != config.WEBHOOK_SECRET:
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(force=True, silent=True)
    if update:
        try:
            handlers.handle_update(update)
        except Exception as e:
            print(f"[webhook] error handling update: {e}")
    return jsonify({"ok": True})


@app.route("/set_webhook", methods=["GET"])
def set_webhook_route():
    """Visit this URL once after deploying to register the webhook with Telegram.
    e.g. https://your-app.onrender.com/set_webhook
    """
    if not config.BASE_URL:
        return jsonify({"ok": False, "error": "BASE_URL env var not set"}), 400

    url = f"{config.BASE_URL}/webhook/{config.WEBHOOK_SECRET}"
    result = tg.set_webhook(url, config.WEBHOOK_SECRET)

    # Also set the visible command menu for regular users.
    tg.set_my_commands([
        {"command": "start", "description": "Start / show intro"},
        {"command": "donate", "description": "Make a donation"},
        {"command": "history", "description": "View your donation history"},
    ])
    # Admin-only commands, scoped just to each admin's private chat with the bot.
    for admin_id in config.ADMIN_IDS:
        tg.set_my_commands(
            [
                {"command": "start", "description": "Start / show intro"},
                {"command": "donate", "description": "Make a donation"},
                {"command": "history", "description": "View your donation history"},
                {"command": "stats", "description": "View bot stats (admin)"},
                {"command": "broadcast", "description": "Broadcast a message (admin)"},
            ],
            scope={"type": "chat", "chat_id": admin_id},
        )

    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
