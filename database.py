"""
database.py — The single source of truth for all data.

WHY THIS FILE EXISTS:
  All data lives in data.json. Every read and write goes through this
  module so we never accidentally corrupt our JSON or cause race conditions.

KEY CONCEPT — File Locking:
  Imagine two users register at the same time and only 1 seat is left.
  Without locking, both could read "1 seat available", both pass the check,
  and both get registered → overbooking!

  filelock.FileLock() ensures only ONE process can write at a time.
  The other has to WAIT until the lock is released.
"""

import json
import os
from filelock import FileLock  # pip install filelock

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(BASE_DIR, "data.json")
LOCK_FILE  = DATA_FILE + ".lock"   # A companion file used as the mutex

# ── Schema ─────────────────────────────────────────────────────────────────
# This is what data.json always looks like:
#
#  {
#    "events": {
#      "<event_id>": {
#        "id":          "evt_...",
#        "name":        "Tech Summit",
#        "total_seats": 100,
#        "date":        "2025-09-15",
#        "created_at":  "2025-06-01T10:00:00"
#      }
#    },
#    "registrations": {
#      "<reg_id>": {
#        "id":           "reg_...",
#        "event_id":     "evt_...",
#        "user_name":    "Alice",
#        "status":       "active",          # "active" | "cancelled"
#        "registered_at":"2025-06-01T11:00:00"
#      }
#    }
#  }


def _empty_db() -> dict:
    """Return a fresh, empty database structure."""
    return {"events": {}, "registrations": {}}


def load_db() -> dict:
    """
    Read the JSON file and return it as a Python dict.
    If the file doesn't exist yet, create it with an empty structure.
    """
    if not os.path.exists(DATA_FILE):
        save_db(_empty_db())

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data: dict) -> None:
    """
    Write the Python dict back to disk as formatted JSON.
    indent=2 makes the file human-readable.
    """
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_lock():
    """
    Return a FileLock object.

    USAGE (always like this for writes):
        with get_lock():
            db = load_db()
            # ... make changes ...
            save_db(db)

    The 'with' block automatically releases the lock even if an exception occurs.
    """
    return FileLock(LOCK_FILE, timeout=5)   # Wait max 5 seconds before giving up
