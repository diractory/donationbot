# RDH Helper Hands — bot + website

## Where do the donation details actually go?
Every submission (Telegram or website) is posted by the bot into your admin
channel: `ADMIN_CHANNEL_ID` (default `-1003870548002`). The bot **must be an
admin of that channel** with "Post Messages" permission, otherwise the send
silently fails. The photo is posted with a spoiler; the caption has category
and amount visible, and name / Instagram / email / message / UTR hidden
behind a `<tg-spoiler>` block that the admin taps to reveal. The Approve /
Decline buttons are attached to that same post.

## QR code — put a real file in the repo (recommended, most reliable)
Replace `static/qr.jpg` with your actual payment QR image, **same filename**.
That's it — the website's `/api/qr` and the bot's "Click to Pay" step both
check this file *first*, before anything else. No scraping, no channel
dependency, nothing to break. (There's a placeholder in that file right now
saying "replace this file" — if you ever see that image, it means you forgot
to swap it.)

If you'd rather keep pulling from your public channel post, that still works
as a fallback (`QR_CHANNEL_POST_URL`), and then a `QR_FALLBACK_FILE_ID` after
that — but the local file is the one to trust.

## One URL to check if anything is broken: `/diag`
Visit `https://your-app.onrender.com/diag`. It returns JSON with:
- `telegram_webhook` — Telegram's own view of your webhook (errors show here)
- `mongo` — `"ok"` or the exact connection error
- `qr_source` / `qr_reason` — which QR source is being used, or why none worked
- `admin_channel_id`, `webhook_expected_url` — to sanity check your env vars

Paste the output of `/diag` back if something's still wrong — it tells us
exactly which piece is failing instead of guessing.

## Deploy on Render
1. Repo root must contain `app.py` directly (or set **Root Directory** in
   Render's Settings to the subfolder if it's nested).
2. **Start Command**:
   `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120`
3. **Environment** tab — set:
   - `BOT_TOKEN` (from @BotFather)
   - `MONGO_URL`
   - `OWNER_USER_ID` (your numeric id from @userinfobot, for /stats /broadcast)
   - `ADMIN_CHANNEL_ID` (default already correct if unset)
4. MongoDB Atlas → Network Access → allow `0.0.0.0/0`.
5. Add the bot as **admin** of your channel.
6. Deploy, then check `/healthz`, then `/diag`, then `/` (website), then send
   `/start` to the bot on Telegram.

## Admin commands (Telegram, DM the bot)
- `/stats` — user count + donation counts (pending/approved/declined)
- `/broadcast <text>` — sends text to every user who has started the bot
- reply to any message with `/broadcast` — forwards that exact message to everyone

Only `OWNER_USER_ID` (or ids in `ADMIN_USER_IDS`) can use these.

## Files
- `app.py` — Flask app: webhook + website + JSON API + `/diag`
- `bot_handlers.py` — all Telegram conversation logic
- `qr_fetcher.py` — local file → channel scrape → fallback file_id, in that order
- `db.py` — MongoDB access (never crashes boot if Atlas is unreachable)
- `config.py` — env vars
- `templates/`, `static/` — the website (put your real QR at `static/qr.jpg`)
