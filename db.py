from datetime import datetime
from pymongo import MongoClient
import config

_client = MongoClient(config.MONGO_URL)
_db = _client["donation_bot"]

users_col = _db["users"]
donations_col = _db["donations"]
counters_col = _db["counters"]
processed_updates_col = _db["processed_updates"]

# Auto-expire dedupe records after 1 day so the collection doesn't grow forever.
try:
    processed_updates_col.create_index("created_at", expireAfterSeconds=86400)
except Exception as e:
    print(f"[db] could not ensure TTL index on processed_updates: {e}")


def already_processed(update_id):
    """Returns True (and records it) the first time an update_id is seen.
    Returns True again on any retry so callers can skip re-processing.
    Uses a unique index race: if insert fails with duplicate key, it's a retry.
    """
    try:
        processed_updates_col.insert_one({"_id": update_id, "created_at": datetime.utcnow()})
        return False  # first time seeing this update
    except Exception:
        return True  # already seen (duplicate key) -> this is a Telegram retry


# ---------------- Users ----------------

def get_user(user_id):
    return users_col.find_one({"_id": user_id})


def upsert_user(user_id, first_name, username):
    users_col.update_one(
        {"_id": user_id},
        {
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
                "blocked": False,
                "state": None,
                "temp": {},
            },
            "$set": {
                "last_seen": datetime.utcnow(),
                "first_name": first_name,
                "username": username,
            },
        },
        upsert=True,
    )


def set_state(user_id, state, temp=None):
    update = {"state": state}
    if temp is not None:
        update["temp"] = temp
    users_col.update_one({"_id": user_id}, {"$set": update}, upsert=True)


def update_temp(user_id, key, value):
    users_col.update_one({"_id": user_id}, {"$set": {f"temp.{key}": value}}, upsert=True)


def clear_state(user_id):
    users_col.update_one({"_id": user_id}, {"$set": {"state": None, "temp": {}}}, upsert=True)


def count_users():
    return users_col.count_documents({})


def all_user_ids():
    return [u["_id"] for u in users_col.find({}, {"_id": 1})]


# ---------------- Donations ----------------

def get_next_donation_id():
    result = counters_col.find_one_and_update(
        {"_id": "donation_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"] if result else 1


def create_donation(donation_id, user_id, data):
    doc = {
        "_id": donation_id,
        "user_id": user_id,
        "category": data.get("category"),
        "amount": data.get("amount"),
        "description": data.get("description"),
        "name": data.get("name"),
        "instagram": data.get("instagram"),
        "email": data.get("email"),
        "utr": data.get("utr"),
        "screenshot_file_id": data.get("screenshot_file_id"),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "channel_message_id": None,
    }
    donations_col.insert_one(doc)
    return doc


def set_channel_message_id(donation_id, message_id):
    donations_col.update_one({"_id": donation_id}, {"$set": {"channel_message_id": message_id}})


def get_donation(donation_id):
    return donations_col.find_one({"_id": donation_id})


def update_donation_status(donation_id, status):
    donations_col.update_one(
        {"_id": donation_id},
        {"$set": {"status": status, "resolved_at": datetime.utcnow()}},
    )


def get_user_donations(user_id, limit=10):
    return list(
        donations_col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    )


def donation_stats():
    total = donations_col.count_documents({})
    pending = donations_col.count_documents({"status": "pending"})
    approved = donations_col.count_documents({"status": "approved"})
    declined = donations_col.count_documents({"status": "declined"})
    approved_sum = 0
    for d in donations_col.find({"status": "approved"}, {"amount": 1}):
        try:
            approved_sum += float(d.get("amount") or 0)
        except (TypeError, ValueError):
            pass
    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "declined": declined,
        "approved_sum": approved_sum,
    }
