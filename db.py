"""
Thin MongoDB helper layer.

Two collections:
  sessions   -> temporary conversation state while a user is filling the
               donation flow (both on Telegram and on the website)
  donations  -> a permanent record once a user reaches the "submit" step,
               including the admin's final decision
"""

import time
import uuid
import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config

log = logging.getLogger("rdh-helper-hands.db")

_client = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=5000)
_db = _client[config.DB_NAME]

sessions = _db["sessions"]
donations = _db["donations"]
users = _db["users"]

# Helpful indexes (safe to call repeatedly, no-ops if they already exist).
# Wrapped in try/except so a slow/unreachable Atlas cluster (e.g. IP not
# whitelisted yet) never crashes the whole app on boot — it just logs and
# the app keeps running; DB calls will simply fail until connectivity is fixed.
try:
    sessions.create_index("key", unique=True)
    donations.create_index("donation_id", unique=True)
    users.create_index("chat_id", unique=True)
except PyMongoError:
    log.exception("Could not create Mongo indexes on boot (will retry lazily on first use)")


# ---------------------------------------------------------------------------
# Session helpers (conversation state machine)
# ---------------------------------------------------------------------------

def get_session(key: str) -> dict:
    """key is usually the telegram chat_id (as string) or a random web session id."""
    doc = sessions.find_one({"key": key})
    return doc["data"] if doc else {}


def set_session(key: str, data: dict) -> None:
    sessions.update_one(
        {"key": key},
        {"$set": {"key": key, "data": data, "updated_at": time.time()}},
        upsert=True,
    )


def update_session(key: str, **fields) -> dict:
    data = get_session(key)
    data.update(fields)
    set_session(key, data)
    return data


def clear_session(key: str) -> None:
    sessions.delete_one({"key": key})


# ---------------------------------------------------------------------------
# Donation records
# ---------------------------------------------------------------------------

def new_donation_id() -> str:
    return uuid.uuid4().hex[:10].upper()


def create_donation(payload: dict) -> str:
    donation_id = new_donation_id()
    record = {
        "donation_id": donation_id,
        "status": "pending",          # pending -> approved | declined
        "created_at": time.time(),
        **payload,
    }
    donations.insert_one(record)
    return donation_id


def get_donation(donation_id: str) -> dict:
    return donations.find_one({"donation_id": donation_id}, {"_id": 0})


def set_donation_status(donation_id: str, status: str, decided_by: str = "") -> None:
    donations.update_one(
        {"donation_id": donation_id},
        {"$set": {"status": status, "decided_at": time.time(), "decided_by": decided_by}},
    )


# ---------------------------------------------------------------------------
# Users (for /stats and /broadcast)
# ---------------------------------------------------------------------------

def upsert_user(chat_id, username: str = "", first_name: str = "") -> None:
    users.update_one(
        {"chat_id": chat_id},
        {
            "$set": {"username": username or "", "first_name": first_name or "", "last_seen": time.time()},
            "$setOnInsert": {"chat_id": chat_id, "first_seen": time.time()},
        },
        upsert=True,
    )


def count_users() -> int:
    return users.count_documents({})


def all_user_chat_ids():
    return [u["chat_id"] for u in users.find({}, {"chat_id": 1})]
