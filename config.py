"""
Central configuration for the RDH Helper Hands bot + website.
Every value below is read from an environment variable so nothing
sensitive ever needs to live in the code. Set these in Render's
"Environment" tab for your service.
"""

import os

# ---- Telegram -------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8398198634:AAHtUGoO4h1KAhzzdez0jAo823_5F0jQSl8")  # from @BotFather
ADMIN_CHANNEL_ID = os.environ.get("ADMIN_CHANNEL_ID", "-1003870548002")  # where approvals happen

# Optional: comma separated telegram user ids allowed to press Approve/Decline,
# and to use /stats and /broadcast. Leave empty to allow anyone who can post in
# the admin channel to approve (but /stats and /broadcast then need OWNER_USER_ID).
ADMIN_USER_IDS = [
    x.strip() for x in os.environ.get("ADMIN_USER_IDS", "").split(",") if x.strip()
]
# Optional: your own numeric telegram user id (get it from @userinfobot), always
# treated as an admin for /stats and /broadcast even if ADMIN_USER_IDS is empty.
OWNER_USER_ID = os.environ.get("OWNER_USER_ID", "8192070400").strip()

# ---- QR code ----------------------------------------------------------------
# RECOMMENDED: commit a QR image to the repo (e.g. static/qr.jpg) and it will
# always be used first — this is far more reliable than scraping Telegram.
QR_LOCAL_PATH = os.environ.get("QR_LOCAL_PATH", "static/qr.jpg")
# Fallback 1: public channel post that has the latest QR code posted in it.
QR_CHANNEL_POST_URL = os.environ.get("QR_CHANNEL_POST_URL", "https://t.me/scisst/20")
# Fallback 2: a telegram file_id for the QR image, used if both of the above fail.
# Get a file_id by forwarding the QR photo to @userinfobot or @RawDataBot once.
QR_FALLBACK_FILE_ID = os.environ.get("QR_FALLBACK_FILE_ID", "")
QR_VALID_MINUTES = int(os.environ.get("QR_VALID_MINUTES", "5"))

# ---- Mongo ------------------------------------------------------------------
MONGO_URL = os.environ.get(
    "MONGO_URL",
    "mongodb+srv://wasdimu:xivasudev@cluster0.zjkb7od.mongodb.net/?appName=Cluster0",
)
DB_NAME = os.environ.get("DB_NAME", "rdh_helper_hands")

# ---- Web server / webhook ---------------------------------------------------
# Render sets RENDER_EXTERNAL_URL automatically for every web service, so you
# usually don't need to set WEBHOOK_BASE_URL yourself.
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL") or os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_SECRET_PATH = os.environ.get("WEBHOOK_SECRET_PATH", BOT_TOKEN.split(":")[-1] if BOT_TOKEN else "hook")
PORT = int(os.environ.get("PORT", "10000"))

# ---- Misc ---------------------------------------------------------------
OWNER_HANDLE = os.environ.get("OWNER_HANDLE", "@Youradhey")
OWNER_SIGNATURE = os.environ.get("OWNER_SIGNATURE", "#RADHEY \u2022 #rdh")
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))

# Preset donation categories: key -> (label, suggested amount in INR)
CATEGORIES = {
    "child": {"label": "Meal for a Child", "amount": 30, "emoji": "\U0001F9D2"},
    "dog":   {"label": "Meal for a Dog",   "amount": 20, "emoji": "\U0001F415"},
    "both":  {"label": "Meal for Both",    "amount": 50, "emoji": "\U0001F91D"},
}
