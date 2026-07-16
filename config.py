import os

# ---- Core secrets / connection info (set these as ENV VARS on Render) ----
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MONGO_URL = os.environ.get("MONGO_URL", "")

# Channel where donation proofs + approve/decline buttons are posted
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003870548002"))

# Comma separated list of Telegram numeric user IDs allowed to use admin commands
# and approve/decline buttons.
ADMIN_IDS = [
    int(x.strip()) for x in os.environ.get("ADMIN_IDS", "8192070400").split(",")
    if x.strip()
]

# QR code source. Either:
#  - QR_FILE_ID: a Telegram file_id (grab this once by sending the QR image to
#    your bot / any chat and reading the file_id from the response), OR
#  - QR_IMAGE_URL: a direct https link to the image (e.g. a GitHub "raw" link).
QR_FILE_ID = os.environ.get("QR_FILE_ID", "")
QR_IMAGE_URL = os.environ.get("QR_IMAGE_URL", "")

# Used to build the webhook URL and to protect the webhook endpoint.
BASE_URL = os.environ.get("BASE_URL", "")  # e.g. https://your-app.onrender.com
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "change-this-secret")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---- Donation rules ----
DONATION_RATES = {
    "child": {"label": "Children 👶", "min_amount": 30},
    "dog": {"label": "Dogs 🐕", "min_amount": 20},
    "both": {"label": "Both (Children + Dogs) 🤝", "min_amount": 50},
}

QR_TIMEOUT_SECONDS = 5 * 60  # 5 minutes

# ---- Conversation states ----
STATE_AWAITING_AMOUNT = "awaiting_amount"
STATE_AWAITING_DESCRIPTION = "awaiting_description"
STATE_AWAITING_NAME = "awaiting_name"
STATE_AWAITING_INSTAGRAM = "awaiting_instagram"
STATE_AWAITING_EMAIL = "awaiting_email"
STATE_AWAITING_UTR = "awaiting_utr"
STATE_AWAITING_SCREENSHOT = "awaiting_screenshot"
