import re
import time

import config
import db
import keyboards as kb
import telegram_api as tg
import scheduler

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# =========================================================
# Entry point
# =========================================================

def handle_update(update):
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])


# =========================================================
# Messages (text / photo)
# =========================================================

def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})
    user_id = from_user.get("id")
    first_name = from_user.get("first_name", "there")
    username = from_user.get("username", "")

    if user_id is None or chat_id is None:
        return

    db.upsert_user(user_id, first_name, username)
    text = (message.get("text") or "").strip()

    # ---- Commands ----
    if text.startswith("/start"):
        db.clear_state(user_id)
        send_welcome(chat_id, first_name)
        return

    if text.startswith("/donate"):
        db.set_state(user_id, None, temp={})
        prompt_category(chat_id)
        return

    if text.startswith("/history"):
        show_history(chat_id, user_id)
        return

    if text.startswith("/stats"):
        if user_id in config.ADMIN_IDS:
            show_stats(chat_id)
        else:
            tg.send_message(chat_id, "🚫 This command is for admins only.")
        return

    if text.startswith("/broadcast"):
        if user_id in config.ADMIN_IDS:
            do_broadcast(chat_id, text)
        else:
            tg.send_message(chat_id, "🚫 This command is for admins only.")
        return

    # ---- Conversation state machine ----
    user = db.get_user(user_id) or {}
    state = user.get("state")

    if state == config.STATE_AWAITING_AMOUNT:
        handle_amount_input(chat_id, user_id, text, user.get("temp", {}))
        return

    if state == config.STATE_AWAITING_DESCRIPTION:
        desc = "Not provided" if (not text or text.lower() == "skip") else text
        db.update_temp(user_id, "description", desc)
        prompt_name(chat_id, user_id)
        return

    if state == config.STATE_AWAITING_NAME:
        if not text:
            tg.send_message(chat_id, "Please type a name to be written on the donation record.")
            return
        db.update_temp(user_id, "name", text)
        prompt_instagram(chat_id, user_id)
        return

    if state == config.STATE_AWAITING_INSTAGRAM:
        insta = None if (not text or text.lower() == "skip") else text
        db.update_temp(user_id, "instagram", insta)
        prompt_email(chat_id, user_id)
        return

    if state == config.STATE_AWAITING_EMAIL:
        if not EMAIL_RE.match(text):
            tg.send_message(chat_id, "That doesn't look like a valid email. Please enter a valid email address (for the donation proof).")
            return
        db.update_temp(user_id, "email", text)
        show_qr(chat_id, user_id)
        return

    if state == config.STATE_AWAITING_UTR:
        if not text:
            tg.send_message(chat_id, "Please send the UTR / transaction reference ID from your payment.")
            return
        db.update_temp(user_id, "utr", text)
        prompt_screenshot(chat_id, user_id)
        return

    if state == config.STATE_AWAITING_SCREENSHOT:
        photos = message.get("photo")
        if not photos:
            tg.send_message(chat_id, "Please send the *screenshot* of your payment as a photo.", parse_mode="Markdown")
            return
        file_id = photos[-1]["file_id"]
        db.update_temp(user_id, "screenshot_file_id", file_id)
        finalize_submission(chat_id, user_id)
        return

    # ---- Fallback ----
    tg.send_message(
        chat_id,
        "I didn't quite get that. Use /start to see the menu, /donate to make a donation, "
        "or /history to see your past donations.",
    )


# =========================================================
# Callback queries (inline button taps)
# =========================================================

def handle_callback(cq):
    cq_id = cq["id"]
    data = cq.get("data", "")
    from_user = cq.get("from", {})
    user_id = from_user.get("id")
    first_name = from_user.get("first_name", "there")
    username = from_user.get("username", "")
    message = cq.get("message", {})
    chat_id = message.get("chat", {}).get("id")

    db.upsert_user(user_id, first_name, username)
    tg.answer_callback_query(cq_id)

    if data == "start_donate":
        db.set_state(user_id, None, temp={})
        prompt_category(chat_id)
        return

    if data in ("cat_child", "cat_dog", "cat_both"):
        category = data.split("_", 1)[1]
        db.set_state(user_id, config.STATE_AWAITING_AMOUNT, temp={"category": category})
        prompt_amount(chat_id, category)
        return

    if data == "paid_confirm":
        db.set_state(user_id, config.STATE_AWAITING_UTR)
        tg.send_message(
            chat_id,
            "🧾 Great! Please send the *UTR / Transaction Reference ID* from your payment.",
            parse_mode="Markdown",
        )
        return

    if data == "history":
        show_history(chat_id, user_id)
        return

    if data == "skip_instagram_text":
        db.update_temp(user_id, "instagram", None)
        prompt_email(chat_id, user_id)
        return

    if data.startswith("approve_") or data.startswith("decline_"):
        handle_admin_decision(cq_id, user_id, data)
        return


# =========================================================
# Conversation flow steps
# =========================================================

def send_welcome(chat_id, first_name):
    text = (
        f"👋 Hi <b>{first_name}</b>!\n\n"
        "This is a donation drive for a <b>one-time meal</b> for children and stray dogs "
        "who need it. 🍛🐾\n\n"
        "Every rupee you give goes directly toward feeding someone who needs it today.\n\n"
        "If you'd like to proceed, tap the button below 👇"
    )
    tg.send_message(chat_id, text, reply_markup=kb.start_keyboard())


def prompt_category(chat_id):
    text = (
        "Who would you like to donate for? 🙏\n\n"
        f"👶 <b>{config.DONATION_RATES['child']['label']}</b> — min ₹{config.DONATION_RATES['child']['min_amount']} per meal\n"
        f"🐕 <b>{config.DONATION_RATES['dog']['label']}</b> — min ₹{config.DONATION_RATES['dog']['min_amount']} per meal\n"
        f"🤝 <b>{config.DONATION_RATES['both']['label']}</b> — min ₹{config.DONATION_RATES['both']['min_amount']}\n"
    )
    tg.send_message(chat_id, text, reply_markup=kb.category_keyboard())


def prompt_amount(chat_id, category):
    rate = config.DONATION_RATES[category]
    text = (
        f"You chose: <b>{rate['label']}</b>\n"
        f"Minimum donation: ₹{rate['min_amount']}\n\n"
        f"You're welcome to donate more than ₹{rate['min_amount']} if you'd like to feed "
        "more than one child/dog. 💛\n\n"
        "Please enter the amount you'd like to donate (numbers only):"
    )
    tg.send_message(chat_id, text)


def handle_amount_input(chat_id, user_id, text, temp):
    category = temp.get("category")
    rate = config.DONATION_RATES.get(category)
    if rate is None:
        tg.send_message(chat_id, "Something went wrong. Please use /donate to start again.")
        db.clear_state(user_id)
        return

    cleaned = text.replace(",", "").replace("₹", "").strip()
    try:
        amount = float(cleaned)
    except ValueError:
        tg.send_message(chat_id, "Please enter a valid number, e.g. 30 or 50.")
        return

    if amount < rate["min_amount"]:
        tg.send_message(
            chat_id,
            f"The minimum for {rate['label']} is ₹{rate['min_amount']}. "
            "Please enter an amount equal to or greater than that.",
        )
        return

    db.update_temp(user_id, "amount", amount)
    db.set_state(user_id, config.STATE_AWAITING_DESCRIPTION)
    tg.send_message(
        chat_id,
        "🙏 Thank you! Now, please write a short message about your donation.\n\n"
        "For example: <i>\"I have paid ₹90 to feed 3 children\"</i> or any note you'd like "
        "to add. You can also just type <b>skip</b>.",
    )


def prompt_name(chat_id, user_id):
    db.set_state(user_id, config.STATE_AWAITING_NAME)
    tg.send_message(chat_id, "✍️ What name would you like written on the donation record?")


def prompt_instagram(chat_id, user_id):
    db.set_state(user_id, config.STATE_AWAITING_INSTAGRAM)
    tg.send_message(
        chat_id,
        "📸 (Optional) Share your Instagram username if you'd like a shout-out/mention on our "
        "story. Otherwise, tap Skip.",
        reply_markup=kb.skip_keyboard("skip_instagram_text"),
    )
    # Note: users can also just send any text; empty/"skip" handled as None in handle_message.


def prompt_email(chat_id, user_id):
    db.set_state(user_id, config.STATE_AWAITING_EMAIL)
    tg.send_message(chat_id, "📧 Please share your email address — we'll send the donation proof/receipt there.")


def show_qr(chat_id, user_id):
    user = db.get_user(user_id) or {}
    temp = user.get("temp", {})
    category = temp.get("category")
    amount = temp.get("amount")
    rate = config.DONATION_RATES.get(category, {})

    caption = (
        f"💳 <b>Scan & Pay ₹{amount}</b>\n"
        f"For: {rate.get('label', '')}\n\n"
        "⏳ This QR code is valid for <b>5 minutes</b> and will be deleted after that.\n"
        "Once you've paid, tap <b>I've Paid</b> below."
    )

    photo_source = config.QR_FILE_ID or config.QR_IMAGE_URL
    if not photo_source:
        tg.send_message(
            chat_id,
            "⚠️ Payment QR is not configured yet. Please contact the admin.\n"
            "(Set QR_FILE_ID or QR_IMAGE_URL in the bot's environment variables.)",
        )
        return

    result = tg.send_photo(chat_id, photo_source, caption=caption, reply_markup=kb.paid_keyboard())
    msg_id = None
    if result.get("ok"):
        msg_id = result["result"]["message_id"]
        scheduler.schedule_message_deletion(chat_id, msg_id, config.QR_TIMEOUT_SECONDS)

    # State stays "awaiting UTR" only once they tap "I've Paid"; until then we just wait.


def prompt_screenshot(chat_id, user_id):
    db.set_state(user_id, config.STATE_AWAITING_SCREENSHOT)
    tg.send_message(chat_id, "📷 Lastly, please send a *screenshot* of your payment for approval.", parse_mode="Markdown")


def finalize_submission(chat_id, user_id):
    user = db.get_user(user_id) or {}
    temp = user.get("temp", {})

    donation_id = db.get_next_donation_id()
    donation = db.create_donation(donation_id, user_id, temp)
    db.clear_state(user_id)

    tg.send_message(
        chat_id,
        "✅ Your information has been submitted!\n\n"
        "Our admins will review and approve your donation request as soon as possible. "
        "Thank you so much for your kindness ❤️",
        reply_markup=kb.main_menu_keyboard(),
    )

    post_to_admin_channel(donation, user)


def post_to_admin_channel(donation, user):
    rate = config.DONATION_RATES.get(donation["category"], {})
    username = user.get("username") or ""
    username_str = f"@{username}" if username else "N/A"

    details = (
        f"👤 Name on record: {donation.get('name')}\n"
        f"🆔 Telegram: {username_str} (ID: {donation['user_id']})\n"
        f"📂 Category: {rate.get('label', donation['category'])}\n"
        f"💰 Amount: ₹{donation.get('amount')}\n"
        f"📝 Note: {donation.get('description')}\n"
        f"📸 Instagram: {donation.get('instagram') or 'Not provided'}\n"
        f"📧 Email: {donation.get('email')}\n"
        f"🧾 UTR ID: {donation.get('utr')}"
    )

    caption = (
        f"🔔 <b>New Donation Request #{donation['_id']}</b>\n\n"
        f"<span class=\"tg-spoiler\">{details}</span>"
    )

    result = tg.send_photo(
        config.CHANNEL_ID,
        donation["screenshot_file_id"],
        caption=caption,
        reply_markup=kb.approve_decline_keyboard(donation["_id"]),
    )
    if result.get("ok"):
        db.set_channel_message_id(donation["_id"], result["result"]["message_id"])


# =========================================================
# Admin approve / decline
# =========================================================

def handle_admin_decision(cq_id, user_id, data):
    if user_id not in config.ADMIN_IDS:
        tg.answer_callback_query(cq_id, "🚫 You're not authorized to do this.", show_alert=True)
        return

    action, donation_id_str = data.split("_", 1)
    try:
        donation_id = int(donation_id_str)
    except ValueError:
        tg.answer_callback_query(cq_id, "Invalid donation reference.", show_alert=True)
        return

    donation = db.get_donation(donation_id)
    if not donation:
        tg.answer_callback_query(cq_id, "Donation not found.", show_alert=True)
        return

    if donation["status"] != "pending":
        tg.answer_callback_query(cq_id, f"Already {donation['status']}.", show_alert=True)
        return

    donor_chat_id = donation["user_id"]
    channel_message_id = donation.get("channel_message_id")
    rate = config.DONATION_RATES.get(donation["category"], {})

    if action == "approve":
        db.update_donation_status(donation_id, "approved")
        status_line = "✅ <b>APPROVED</b>"
        user_msg = (
            "🎉 Great news! The admins have approved your donation request and your "
            "payment has been successfully reviewed.\n\n"
            f"Thank you so much for your donation towards {rate.get('label', '')}! "
            "Your kindness means a lot. ❤️"
        )
    else:
        db.update_donation_status(donation_id, "declined")
        status_line = "❌ <b>DECLINED</b>"
        user_msg = (
            "😔 Your donation request could not be verified and was declined.\n\n"
            "If you believe this is a mistake, please contact the admin with your "
            "UTR ID and payment screenshot."
        )

    tg.send_message(donor_chat_id, user_msg)

    if channel_message_id:
        details = (
            f"👤 Name on record: {donation.get('name')}\n"
            f"📂 Category: {rate.get('label', donation['category'])}\n"
            f"💰 Amount: ₹{donation.get('amount')}\n"
            f"📝 Note: {donation.get('description')}\n"
            f"📸 Instagram: {donation.get('instagram') or 'Not provided'}\n"
            f"📧 Email: {donation.get('email')}\n"
            f"🧾 UTR ID: {donation.get('utr')}"
        )
        caption = (
            f"🔔 <b>Donation Request #{donation_id}</b> — {status_line}\n\n"
            f"<span class=\"tg-spoiler\">{details}</span>"
        )
        tg.edit_message_caption(config.CHANNEL_ID, channel_message_id, caption, reply_markup=None)

    tg.answer_callback_query(cq_id, f"Marked as {action}d.")


# =========================================================
# History / stats / broadcast
# =========================================================

def show_history(chat_id, user_id):
    donations = db.get_user_donations(user_id, limit=10)
    if not donations:
        tg.send_message(chat_id, "You don't have any donations yet. Tap below to make your first one! 💛", reply_markup=kb.main_menu_keyboard())
        return

    lines = ["📜 <b>Your Donation History</b>\n"]
    status_emoji = {"pending": "⏳", "approved": "✅", "declined": "❌"}
    for d in donations:
        rate = config.DONATION_RATES.get(d["category"], {})
        emoji = status_emoji.get(d["status"], "•")
        date_str = d["created_at"].strftime("%d %b %Y")
        lines.append(
            f"{emoji} #{d['_id']} — ₹{d.get('amount')} for {rate.get('label', d['category'])} "
            f"({d['status'].capitalize()}) — {date_str}"
        )
    tg.send_message(chat_id, "\n".join(lines), reply_markup=kb.main_menu_keyboard())


def show_stats(chat_id):
    total_users = db.count_users()
    s = db.donation_stats()
    text = (
        "📊 <b>Bot Stats</b>\n\n"
        f"👥 Total users: {total_users}\n\n"
        f"💌 Total donation requests: {s['total']}\n"
        f"⏳ Pending: {s['pending']}\n"
        f"✅ Approved: {s['approved']}\n"
        f"❌ Declined: {s['declined']}\n\n"
        f"💰 Total approved amount: ₹{s['approved_sum']:.2f}"
    )
    tg.send_message(chat_id, text)


def do_broadcast(chat_id, text):
    parts = text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        tg.send_message(chat_id, "Usage: /broadcast Your message here")
        return

    message = parts[1].strip()
    user_ids = db.all_user_ids()
    tg.send_message(chat_id, f"📢 Broadcasting to {len(user_ids)} users...")

    sent = 0
    failed = 0
    for uid in user_ids:
        result = tg.send_message(uid, message)
        if result.get("ok"):
            sent += 1
        else:
            failed += 1
        time.sleep(0.05)  # basic flood-control pacing

    tg.send_message(chat_id, f"✅ Broadcast complete. Sent: {sent}, Failed: {failed}")
