# Donation Telegram Bot

A Flask + MongoDB Telegram bot for collecting one-time-meal donations for
children and dogs, with QR-code payment, UTR + screenshot verification, an
admin approval channel, and admin tools (stats, broadcast).

## How it works

1. **`/start`** — Greets the user by name, explains the cause, shows a
   **"❤️ Donate Now"** button.
2. User taps Donate → chooses **Children (₹30) / Dogs (₹20) / Both (₹50)**.
3. Bot asks for the **amount** (must be ≥ the minimum for that category — they
   can donate more to cover multiple meals).
4. Bot asks for a short **note/description** (optional — can type `skip`).
5. Bot asks for the **name** to record the donation under.
6. Bot asks for an **Instagram username** (optional — for a story mention).
7. Bot asks for an **email** (for the donation proof).
8. Bot sends the **QR code**, which auto-deletes after **5 minutes**. A
   **"✅ I've Paid"** button then asks for the **UTR / transaction ID**.
9. Bot asks for the **payment screenshot**.
10. User gets: *"Your information has been submitted..."*
11. The screenshot + all details (wrapped in a Telegram spoiler so only admins
    reading the channel see them) are posted to your **admin channel**, with
    **✅ Approve / ❌ Decline** buttons.
12. When an admin taps Approve/Decline, the donor is notified automatically,
    and the channel post is updated to show the final status.

Users can also use **`/history`** (or the "📜 My History" button) to see their
past donations and statuses.

### Admin commands (restricted to `ADMIN_IDS`)
- `/stats` — total users, total/pending/approved/declined donations, total
  approved amount.
- `/broadcast <message>` — sends `<message>` to every user who has ever
  messaged the bot.
- Tapping **Approve/Decline** in the channel — only works for admins.

## Project structure

```
app.py           Flask app + webhook endpoint
handlers.py       All conversation logic (the "brain")
db.py             MongoDB access layer
telegram_api.py   Thin wrapper around Telegram Bot API calls
keyboards.py      Inline keyboard builders
scheduler.py      Background timer to auto-delete the QR after 5 minutes
config.py         Reads all settings from environment variables
requirements.txt  Python dependencies
Procfile          Render/Heroku-style start command
render.yaml       Render "blueprint" for one-click setup (optional)
.env.example      Every environment variable you need to set
```

## 1. Create your bot

1. Open Telegram, message **@BotFather**, run `/newbot`, follow the prompts.
2. Copy the token it gives you — this is `BOT_TOKEN`.
3. Add your bot as an **admin** of your donation channel
   (`-1003870548002`) so it can post messages there.

## 2. Get your QR code onto the bot

You mentioned uploading `qr.jpg` to GitHub or grabbing it from a channel post.
Two supported options — set **one** of these env vars:

- **`QR_IMAGE_URL`** (recommended, simplest): upload `qr.jpg` to a GitHub repo
  and use the **raw** link, e.g.
  `https://raw.githubusercontent.com/<you>/<repo>/main/qr.jpg`
  (Telegram can fetch this directly — a `https://t.me/...` post link will
  **not** work here, Telegram post links aren't direct image URLs.)

- **`QR_FILE_ID`**: send `qr.jpg` to your bot once (in a private chat, after
  it's deployed) and read the returned `file_id` from the Telegram API
  response (you can check this via
  `https://api.telegram.org/bot<token>/getUpdates`). Put that string in
  `QR_FILE_ID` — Telegram will serve the same cached image instantly with no
  external hosting needed.

## 3. MongoDB

Your Atlas connection string is already set up — just paste it into
`MONGO_URL`:
```
mongodb+srv://wasdimu:xivasudev@cluster0.zjkb7od.mongodb.net/?appName=Cluster0
```
Nothing else to configure — collections (`users`, `donations`, `counters`)
are created automatically on first use.

**Security note:** this connection string contains a real username/password.
Treat it as a secret — don't commit it to a public GitHub repo. Put it only
in Render's environment variable settings (see below).

## 4. Deploy to Render

1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service** → connect your repo.
   - Environment: **Python 3**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --workers 1 --threads 4 --timeout 60`
   - (Or just let Render auto-detect via `render.yaml`.)
3. Add these **Environment Variables** in Render's dashboard:

   | Key | Value |
   |---|---|
   | `BOT_TOKEN` | token from BotFather |
   | `MONGO_URL` | your Atlas connection string |
   | `CHANNEL_ID` | `-1003870548002` |
   | `ADMIN_IDS` | `8192070400` |
   | `QR_IMAGE_URL` or `QR_FILE_ID` | see step 2 |
   | `BASE_URL` | `https://<your-render-app-name>.onrender.com` (fill this in *after* the first deploy gives you the URL) |
   | `WEBHOOK_SECRET` | any random string |

4. Deploy. Once it's live, visit:
   ```
   https://<your-render-app-name>.onrender.com/set_webhook
   ```
   once, in your browser. This registers the webhook with Telegram and sets
   the bot's command menu. You should see `{"ok": true, ...}`.

5. Message your bot `/start` on Telegram — you're live! 🎉

### Important: keep the service awake (free plan)
Render's free web services spin down after inactivity, which means Telegram
webhooks (and the 5-minute QR-deletion timer) may not fire instantly on the
very first request after idling. If this matters to you, use Render's paid
"always-on" plan, or a free uptime-pinger (e.g. UptimeRobot hitting `/` every
few minutes).

## Notes & things you may want to extend later

- The QR auto-delete uses an in-process timer (`scheduler.py`). This is fine
  for a single Render instance (we pin `--workers 1` in the `Procfile` for
  this reason). If you ever scale to multiple instances, replace it with a
  persisted job queue (APScheduler + DB job store, or Celery/RQ) so timers
  survive restarts.
- `/broadcast` sends messages one at a time with a small delay to respect
  Telegram's rate limits. For very large user bases you may want a proper
  task queue instead of a blocking loop.
- Admin IDs are a comma-separated list (`ADMIN_IDS=8192070400,111111111`) if
  you want more than one admin later.
