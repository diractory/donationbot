def _kb(rows):
    return {"inline_keyboard": rows}


def start_keyboard():
    return _kb([[{"text": "❤️ Donate Now", "callback_data": "start_donate"}]])


def category_keyboard():
    return _kb([
        [{"text": "👶 Children - ₹30", "callback_data": "cat_child"}],
        [{"text": "🐕 Dogs - ₹20", "callback_data": "cat_dog"}],
        [{"text": "🤝 Both - ₹50", "callback_data": "cat_both"}],
    ])


def skip_keyboard(callback_data, label="⏭ Skip"):
    return _kb([[{"text": label, "callback_data": callback_data}]])


def paid_keyboard():
    return _kb([[{"text": "✅ I've Paid", "callback_data": "paid_confirm"}]])


def approve_decline_keyboard(donation_id):
    return _kb([[
        {"text": "✅ Approve", "callback_data": f"approve_{donation_id}"},
        {"text": "❌ Decline", "callback_data": f"decline_{donation_id}"},
    ]])


def main_menu_keyboard():
    return _kb([
        [{"text": "❤️ New Donation", "callback_data": "start_donate"}],
        [{"text": "📜 My History", "callback_data": "history"}],
    ])
