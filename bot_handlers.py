"""
All Telegram bot behaviour lives here. app.py just wires this bot into a
Flask webhook route.

Conversation states (stored per chat in Mongo via db.sessions) walk through:

  idle -> awaiting_amount -> [awaiting_explanation] -> awaiting_name
       -> awaiting_instagram -> awaiting_email -> awaiting_message
       -> ready_to_pay -> awaiting_screenshot -> awaiting_utr -> submitted
"""

import io
import logging
import re
import threading

import telebot
from telebot import types

import config
import db
import qr_fetcher

log = logging.getLogger("rdh-helper-hands.bot")

# Make sure telebot's own internal logger actually prints somewhere (Render logs
# read from stdout/stderr) — otherwise handler crashes get silently swallowed
# and it just looks like "the bot doesn't respond to anything".
telebot.logger.addHandler(logging.StreamHandler())
telebot.logger.setLevel(logging.INFO)


class _LogAllExceptions(telebot.ExceptionHandler):
    def handle(self, exception):
        log.exception("Unhandled exception in a bot handler: %s", exception)
        return True  # tell telebot this was handled, so the bot keeps running


if not config.BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is not set. Add it in Render → your service → Environment."
    )

bot = telebot.TeleBot(
    config.BOT_TOKEN,
    parse_mode="HTML",
    threaded=True,
    exception_handler=_LogAllExceptions(),
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _key(chat_id) -> str:
    return f"tg:{chat_id}"


def _reset(chat_id):
    db.clear_session(_key(chat_id))


def _categories_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for code, info in config.CATEGORIES.items():
        kb.add(
            types.InlineKeyboardButton(
                f"{info['emoji']} {info['label']} \u2014 \u20b9{info['amount']}",
                callback_data=f"cat_{code}",
            )
        )
    return kb


def _skip_keyboard(callback_data):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Skip \u2192", callback_data=callback_data))
    return kb


def _pay_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("\u2705 Click to Pay", callback_data="pay_click"))
    return kb


def _sent_payment_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("\U0001F4F8 Send Payment Screenshot", callback_data="sent_payment"))
    return kb


def _admin_decision_keyboard(donation_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("\u2705 Approve", callback_data=f"appr_{donation_id}"),
        types.InlineKeyboardButton("\u274C Decline", callback_data=f"decl_{donation_id}"),
    )
    return kb


def _delete_message_later(chat_id, message_id, delay_seconds):
    def _job():
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass  # already deleted / too old, nothing to do

    timer = threading.Timer(delay_seconds, _job)
    timer.daemon = True
    timer.start()


# ---------------------------------------------------------------------------
# /start and /cancel
# ---------------------------------------------------------------------------

@bot.message_handler(commands=["start"])
def handle_start(message):
    _reset(message.chat.id)
    db.set_session(_key(message.chat.id), {"step": "idle", "source": "telegram"})
    db.upsert_user(message.chat.id, message.from_user.username, message.from_user.first_name)

    text = (
        "Hii there! \U0001F44B This is <b>#rdh Helper Hands Bot</b>.\n\n"
        "Here you can donate a small amount to give a poor child or a stray dog "
        "one good meal \U0001F37D\ufe0f\n\n"
        "Every rupee genuinely reaches someone who needs it \u2014 tap below to start."
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("\U0001F49D Tap below to donate", callback_data="donate_start"))
    bot.send_message(message.chat.id, text, reply_markup=kb)


@bot.message_handler(commands=["cancel"])
def handle_cancel(message):
    _reset(message.chat.id)
    bot.send_message(message.chat.id, "No worries, cancelled. Send /start whenever you're ready. \U0001F49B")


# ---------------------------------------------------------------------------
# category selection
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data == "donate_start")
def cb_donate_start(call):
    bot.answer_callback_query(call.id)
    db.update_session(_key(call.message.chat.id), step="awaiting_category")
    bot.send_message(
        call.message.chat.id,
        "What would you like to donate? \U0001F447",
        reply_markup=_categories_keyboard(),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def cb_category(call):
    code = call.data.split("_", 1)[1]
    info = config.CATEGORIES.get(code)
    if not info:
        bot.answer_callback_query(call.id, "Unknown option, please try again.")
        return
    bot.answer_callback_query(call.id)

    db.update_session(
        _key(call.message.chat.id),
        step="awaiting_amount",
        category=code,
        category_label=info["label"],
        suggested_amount=info["amount"],
    )

    lines = "\n".join(
        f"\u2022 {v['emoji']} {v['label']}: \u20b9{v['amount']}" for v in config.CATEGORIES.values()
    )
    text = (
        f"You picked <b>{info['label']}</b> (suggested \u20b9{info['amount']}).\n\n"
        f"Suggested amounts:\n{lines}\n\n"
        "You're welcome to donate any amount you like \u2014 just type the number "
        "below. If it's different from the suggested amount, we'll ask you to "
        "briefly tell us why (e.g. \"splitting between 2 meals\").\n\n"
        "How much would you like to donate, in \u20b9?"
    )
    bot.send_message(call.message.chat.id, text)


# ---------------------------------------------------------------------------
# text-driven steps (amount / explanation / name / instagram / email / message / utr)
# ---------------------------------------------------------------------------

def _step_of(chat_id):
    return db.get_session(_key(chat_id)).get("step")


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_amount", content_types=["text"])
def step_amount(message):
    raw = message.text.strip().replace("\u20b9", "").replace(",", "")
    try:
        amount = float(raw)
        assert amount > 0
    except (ValueError, AssertionError):
        bot.reply_to(message, "That doesn't look like a valid amount. Please type just the number, e.g. 30")
        return

    session = db.get_session(_key(message.chat.id))
    suggested = session.get("suggested_amount", 0)

    if abs(amount - suggested) < 0.001:
        db.update_session(_key(message.chat.id), amount=amount, step="awaiting_name")
        bot.send_message(message.chat.id, "Lovely \U0001F64C What name should we print on the record? (your full name)")
    else:
        db.update_session(_key(message.chat.id), amount=amount, step="awaiting_explanation")
        bot.send_message(
            message.chat.id,
            f"Got it, \u20b9{amount:g} \u2014 since that's different from the suggested amount, "
            "please tell us briefly why (one line is fine).",
        )


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_explanation", content_types=["text"])
def step_explanation(message):
    db.update_session(_key(message.chat.id), explanation=message.text.strip(), step="awaiting_name")
    bot.send_message(message.chat.id, "Thank you for explaining \U0001F64F What name should we print on the record?")


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_name", content_types=["text"])
def step_name(message):
    db.update_session(_key(message.chat.id), name=message.text.strip(), step="awaiting_instagram")
    bot.send_message(
        message.chat.id,
        "Want a shoutout? Send your Instagram username, or tap Skip.",
        reply_markup=_skip_keyboard("skip_insta"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "skip_insta")
def cb_skip_insta(call):
    bot.answer_callback_query(call.id)
    db.update_session(_key(call.message.chat.id), instagram="-", step="awaiting_email")
    bot.send_message(call.message.chat.id, "No problem. What email should we send your meal photos / proof to?")


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_instagram", content_types=["text"])
def step_instagram(message):
    db.update_session(_key(message.chat.id), instagram=message.text.strip(), step="awaiting_email")
    bot.send_message(message.chat.id, "Great! What email should we send your meal photos / proof to?")


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_email", content_types=["text"])
def step_email(message):
    email = message.text.strip()
    if not EMAIL_RE.match(email):
        bot.reply_to(message, "That doesn't look like a valid email, please try again.")
        return
    db.update_session(_key(message.chat.id), email=email, step="awaiting_message")
    bot.send_message(
        message.chat.id,
        "Anything you'd like to add \u2014 a message, dedication, or note? Or tap Skip.",
        reply_markup=_skip_keyboard("skip_message"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "skip_message")
def cb_skip_message(call):
    bot.answer_callback_query(call.id)
    db.update_session(_key(call.message.chat.id), message="-")
    _show_summary_and_pay(call.message.chat.id)


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_message", content_types=["text"])
def step_message(message):
    db.update_session(_key(message.chat.id), message=message.text.strip())
    _show_summary_and_pay(message.chat.id)


def _show_summary_and_pay(chat_id):
    s = db.get_session(_key(chat_id))
    db.update_session(_key(chat_id), step="ready_to_pay")
    text = (
        "Here's what we've got \U0001F4CB\n\n"
        f"\u2022 Donating for: <b>{s.get('category_label')}</b>\n"
        f"\u2022 Amount: <b>\u20b9{s.get('amount'):g}</b>\n"
        f"\u2022 Name: {s.get('name')}\n"
        f"\u2022 Instagram: {s.get('instagram')}\n"
        f"\u2022 Email: {s.get('email')}\n\n"
        "Whenever you're ready \u2014 tap below to get the payment QR."
    )
    bot.send_message(chat_id, text, reply_markup=_pay_keyboard())


# ---------------------------------------------------------------------------
# payment: QR -> screenshot -> UTR -> submit to admin channel
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data == "pay_click")
def cb_pay_click(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id

    kind, value, reason = qr_fetcher.get_qr_source()
    caption = (
        f"This QR is valid for {config.QR_VALID_MINUTES} minutes. "
        "After you pay, tap the button below."
    )

    if kind == "bytes":
        sent = bot.send_photo(chat_id, io.BytesIO(value), caption=caption, reply_markup=_sent_payment_keyboard())
    elif kind == "file_id":
        sent = bot.send_photo(chat_id, value, caption=caption, reply_markup=_sent_payment_keyboard())
    else:
        log.warning("QR could not be loaded for chat %s: %s", chat_id, reason)
        bot.send_message(
            chat_id,
            "Sorry, the QR code couldn't be loaded right now. Please try again in a moment, "
            f"or reach out to {config.OWNER_HANDLE}.",
        )
        return

    db.update_session(_key(chat_id), step="awaiting_screenshot_wait", qr_message_id=sent.message_id)
    _delete_message_later(chat_id, sent.message_id, config.QR_VALID_MINUTES * 60)


@bot.callback_query_handler(func=lambda c: c.data == "sent_payment")
def cb_sent_payment(call):
    bot.answer_callback_query(call.id)
    db.update_session(_key(call.message.chat.id), step="awaiting_screenshot")
    bot.send_message(call.message.chat.id, "Please send the payment screenshot now, as a photo. \U0001F4F8")


@bot.message_handler(
    func=lambda m: _step_of(m.chat.id) == "awaiting_screenshot",
    content_types=["photo"],
)
def step_screenshot(message):
    file_id = message.photo[-1].file_id
    db.update_session(_key(message.chat.id), screenshot_file_id=file_id, step="awaiting_utr")
    bot.send_message(message.chat.id, "Got the screenshot! Now please enter your UTR / transaction ID.")


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_screenshot", content_types=["text"])
def step_screenshot_wrong_type(message):
    bot.reply_to(message, "Please send the payment screenshot as a photo (not text).")


@bot.message_handler(func=lambda m: _step_of(m.chat.id) == "awaiting_utr", content_types=["text"])
def step_utr(message):
    s = db.update_session(_key(message.chat.id), utr=message.text.strip(), step="submitted")

    bot.send_message(
        message.chat.id,
        "Heyy, hold on \u2014 now the admin will check it out and approve your payment. "
        "We'll cross-check the details first and get back to you here. \U0001F64F",
    )

    donation_id = db.create_donation(
        {
            "source": "telegram",
            "chat_id": message.chat.id,
            "username": message.from_user.username or "",
            "category": s.get("category"),
            "category_label": s.get("category_label"),
            "suggested_amount": s.get("suggested_amount"),
            "amount": s.get("amount"),
            "explanation": s.get("explanation", "-"),
            "name": s.get("name"),
            "instagram": s.get("instagram", "-"),
            "email": s.get("email"),
            "message": s.get("message", "-"),
            "utr": s.get("utr"),
            "screenshot_file_id": s.get("screenshot_file_id"),
        }
    )

    _post_to_admin_channel(donation_id)
    _reset(message.chat.id)


def _admin_caption(d, source_line):
    """Amount/category stay visible; anything personally identifying is spoilered."""
    spoiler = (
        f"Name: {d.get('name')}\n"
        f"Instagram: {d.get('instagram')}\n"
        f"Email: {d.get('email')}\n"
        f"Message: {d.get('message')}\n"
        f"UTR: {d.get('utr')}"
    )
    return (
        f"\U0001F514 <b>New donation \u2014 #{d.get('donation_id')}</b>\n\n"
        f"Source: {source_line}\n"
        f"Category: {d.get('category_label')}\n"
        f"Amount: \u20b9{d.get('amount'):g} (suggested \u20b9{d.get('suggested_amount'):g})\n"
        f"Explanation: {d.get('explanation')}\n\n"
        f"<tg-spoiler>{spoiler}</tg-spoiler>"
    )


def _post_to_admin_channel(donation_id):
    d = db.get_donation(donation_id)
    caption = _admin_caption(d, f"Telegram (@{d.get('username') or 'no username'})")
    bot.send_photo(
        config.ADMIN_CHANNEL_ID,
        d.get("screenshot_file_id"),
        caption=caption,
        has_spoiler=True,
        reply_markup=_admin_decision_keyboard(donation_id),
    )


# ---------------------------------------------------------------------------
# admin approve / decline
# ---------------------------------------------------------------------------

def _is_authorised_admin(call) -> bool:
    if not config.ADMIN_USER_IDS:
        return True
    return str(call.from_user.id) in config.ADMIN_USER_IDS


def _is_admin_user_id(user_id) -> bool:
    uid = str(user_id)
    if config.OWNER_USER_ID and uid == config.OWNER_USER_ID:
        return True
    return uid in config.ADMIN_USER_IDS


@bot.message_handler(commands=["stats"])
def handle_stats(message):
    if not _is_admin_user_id(message.from_user.id):
        bot.reply_to(message, "This command is admin-only.")
        return
    total = db.count_users()
    pending = db.donations.count_documents({"status": "pending"})
    approved = db.donations.count_documents({"status": "approved"})
    declined = db.donations.count_documents({"status": "declined"})
    bot.reply_to(
        message,
        "\U0001F4CA <b>Bot stats</b>\n\n"
        f"Users who started the bot: <b>{total}</b>\n\n"
        f"Donations pending: <b>{pending}</b>\n"
        f"Donations approved: <b>{approved}</b>\n"
        f"Donations declined: <b>{declined}</b>",
    )


@bot.message_handler(commands=["broadcast"])
def handle_broadcast(message):
    if not _is_admin_user_id(message.from_user.id):
        bot.reply_to(message, "This command is admin-only.")
        return

    # /broadcast <text>          -> sends that text to every user
    # reply to a message with /broadcast -> forwards that exact message to every user
    text_after_command = message.text.partition(" ")[2].strip()
    forward_source = message.reply_to_message

    if not text_after_command and not forward_source:
        bot.reply_to(
            message,
            "Usage:\n"
            "\u2022 <code>/broadcast your message</code> \u2014 sends that text to everyone\n"
            "\u2022 reply to any message with <code>/broadcast</code> \u2014 forwards it to everyone",
        )
        return

    user_ids = db.all_user_chat_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            if forward_source:
                bot.forward_message(uid, message.chat.id, forward_source.message_id)
            else:
                bot.send_message(uid, text_after_command)
            sent += 1
        except Exception:
            failed += 1

    bot.reply_to(message, f"\U0001F4E2 Broadcast done. Sent: {sent}, failed: {failed} (out of {len(user_ids)}).")


@bot.callback_query_handler(func=lambda c: c.data.startswith("appr_") or c.data.startswith("decl_"))
def cb_admin_decision(call):
    if not _is_authorised_admin(call):
        bot.answer_callback_query(call.id, "You're not authorised to do this.", show_alert=True)
        return

    approve = call.data.startswith("appr_")
    donation_id = call.data.split("_", 1)[1]
    d = db.get_donation(donation_id)

    if not d:
        bot.answer_callback_query(call.id, "Donation not found (maybe already handled).", show_alert=True)
        return

    status = "approved" if approve else "declined"
    db.set_donation_status(donation_id, status, decided_by=call.from_user.username or str(call.from_user.id))
    bot.answer_callback_query(call.id, f"Marked as {status}.")

    decision_word = "\u2705 APPROVED" if approve else "\u274C DECLINED"
    decided_by = call.from_user.username or call.from_user.id
    decided_line = f"\n\n{decision_word} by @{decided_by}"
    try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + decided_line,
            reply_markup=None,
        )
    except Exception:
        pass

    # notify the donor, if this came from telegram
    if d.get("source") == "telegram" and d.get("chat_id"):
        if approve:
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
            bot.send_message(d["chat_id"], text)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# fallback for anything else
# ---------------------------------------------------------------------------

@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(message):
    step = _step_of(message.chat.id)
    if step in (None, "idle"):
        bot.reply_to(message, "Send /start to begin donating a meal. \U0001F49B")
