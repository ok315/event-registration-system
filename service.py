"""
service.py — All business logic lives here.

WHY SEPARATE FROM database.py?
  database.py only knows how to READ and WRITE data.
  service.py knows the RULES (validation, constraints, calculations).
  This separation is called "Separation of Concerns" — a core design principle.

  If you later switch from JSON to SQLite, you only change database.py,
  and service.py stays exactly the same. Clean!
"""

import uuid
from datetime import datetime, date

from database import load_db, save_db, get_lock


# ═══════════════════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _new_id(prefix: str) -> str:
    """
    Generate a unique ID like "evt_a3f9c2" or "reg_7b1d4e".

    uuid.uuid4() generates a random 128-bit number.
    [:6] takes the first 6 hex characters — short but unique enough for this project.
    """
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def _now_str() -> str:
    """Current UTC time as an ISO-8601 string, e.g. '2025-06-08T14:30:00'."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _available_seats(event_id: str, db: dict) -> int:
    """
    Calculate available seats dynamically by counting ACTIVE registrations.

    WHY DYNAMIC CALCULATION?
      Storing "available_seats" as a field and updating it is error-prone.
      If a bug skips the update, your count is wrong forever.
      Computing it fresh from registrations is always accurate.
      This is called "derived data" — calculate it, don't store it.
    """
    active_regs = sum(
        1 for r in db["registrations"].values()
        if r["event_id"] == event_id and r["status"] == "active"
    )
    total = db["events"][event_id]["total_seats"]
    return total - active_regs


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 1 — CREATE EVENT
# ═══════════════════════════════════════════════════════════════════════════

def create_event(name: str, total_seats: int, event_date: str) -> dict:
    """
    Create a new event.

    Parameters:
        name        : "Tech Summit 2025"
        total_seats : 100
        event_date  : "2025-09-15"  (YYYY-MM-DD format)

    Returns a dict with either:
        {"success": True,  "event": {...}}
        {"success": False, "error": "...reason..."}

    VALIDATION RULES:
        1. Name must be non-empty
        2. Name must be unique across all events
        3. total_seats must be > 0
        4. event_date must be in the future
    """

    # ── Input sanitization ─────────────────────────────────────────────────
    name = name.strip()
    if not name:
        return {"success": False, "error": "Event name cannot be empty."}

    # ── Validate seats ─────────────────────────────────────────────────────
    try:
        total_seats = int(total_seats)
    except (ValueError, TypeError):
        return {"success": False, "error": "Total seats must be a number."}

    if total_seats <= 0:
        return {"success": False, "error": "Total seats must be greater than 0."}

    # ── Validate date format ───────────────────────────────────────────────
    try:
        parsed_date = datetime.strptime(event_date, "%Y-%m-%d").date()
    except ValueError:
        return {"success": False, "error": "Date must be in YYYY-MM-DD format."}

    if parsed_date <= date.today():
        return {"success": False, "error": "Event date must be in the future."}

    # ── Write to DB (with lock to prevent concurrent duplicate names) ──────
    with get_lock():
        db = load_db()

        # Check name uniqueness (case-insensitive)
        name_lower = name.lower()
        for evt in db["events"].values():
            if evt["name"].lower() == name_lower:
                return {"success": False, "error": f"An event named '{evt['name']}' already exists."}

        event = {
            "id":          _new_id("evt"),
            "name":        name,
            "total_seats": total_seats,
            "date":        event_date,
            "created_at":  _now_str(),
        }

        db["events"][event["id"]] = event
        save_db(db)

    return {"success": True, "event": event}


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 2 — REGISTER USER
# ═══════════════════════════════════════════════════════════════════════════

def register_user(user_name: str, event_id: str) -> dict:
    """
    Register a user for an event.

    CRITICAL: The ENTIRE check-and-register block runs inside a lock.

    WHY? Without the lock:
      Thread A reads: "1 seat left" → passes check
      Thread B reads: "1 seat left" → passes check
      Thread A registers → 0 seats left
      Thread B registers → -1 seats left  ← OVERBOOKING BUG!

    With the lock, Thread B must wait, then re-reads 0 seats, and fails correctly.
    """
    user_name = user_name.strip()
    if not user_name:
        return {"success": False, "error": "User name cannot be empty."}

    with get_lock():
        db = load_db()

        # ── Check event exists ─────────────────────────────────────────────
        if event_id not in db["events"]:
            return {"success": False, "error": f"No event found with ID '{event_id}'."}

        event = db["events"][event_id]

        # ── Check for duplicate registration ──────────────────────────────
        # "Idempotency" — same request twice should not create two registrations
        for reg in db["registrations"].values():
            if (reg["event_id"] == event_id
                    and reg["user_name"].lower() == user_name.lower()
                    and reg["status"] == "active"):
                return {"success": False, "error": f"'{user_name}' is already registered for '{event['name']}'."}

        # ── Check seat availability ────────────────────────────────────────
        available = _available_seats(event_id, db)
        if available <= 0:
            return {"success": False, "error": f"Sorry, '{event['name']}' is fully booked."}

        # ── All checks passed — create the registration ────────────────────
        registration = {
            "id":            _new_id("reg"),
            "event_id":      event_id,
            "user_name":     user_name,
            "status":        "active",
            "registered_at": _now_str(),
        }

        db["registrations"][registration["id"]] = registration
        save_db(db)

    return {"success": True, "registration": registration}


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 3 — VIEW EVENTS
# ═══════════════════════════════════════════════════════════════════════════

def list_events(sort_by_date: bool = True, upcoming_only: bool = False) -> dict:
    """
    Return all events with enriched data (available seats, registration count).

    Parameters:
        sort_by_date  : If True, sort events by date ascending
        upcoming_only : If True, only return events whose date >= today
    """
    db = load_db()
    today_str = date.today().isoformat()   # e.g. "2025-06-08"

    result = []
    for evt in db["events"].values():
        # ── Filter upcoming only ───────────────────────────────────────────
        if upcoming_only and evt["date"] < today_str:
            continue

        available = _available_seats(evt["id"], db)
        total_registrations = sum(
            1 for r in db["registrations"].values()
            if r["event_id"] == evt["id"] and r["status"] == "active"
        )

        result.append({
            **evt,                                    # Spread all event fields
            "available_seats":     available,
            "total_registrations": total_registrations,
            "is_full":             available == 0,
        })

    # ── Sort ───────────────────────────────────────────────────────────────
    if sort_by_date:
        result.sort(key=lambda e: e["date"])

    return {"success": True, "events": result, "count": len(result)}


def get_event(event_id: str) -> dict:
    """Return a single event by ID with enriched seat info."""
    db = load_db()
    if event_id not in db["events"]:
        return {"success": False, "error": f"No event found with ID '{event_id}'."}

    evt = db["events"][event_id]
    available = _available_seats(event_id, db)

    return {
        "success": True,
        "event": {
            **evt,
            "available_seats":     available,
            "total_registrations": evt["total_seats"] - available,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 4 — CANCEL REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════

def cancel_registration(registration_id: str) -> dict:
    """
    Cancel a registration by its ID.

    We DON'T delete the record — we change status to "cancelled".

    WHY SOFT DELETE?
      - Audit trail: you can see the history of registrations
      - Debugging: easier to trace what happened
      - Business logic: the assessment says "cancelled users should not appear
        in ACTIVE registrations" — implying they still exist, just filtered out
    """
    with get_lock():
        db = load_db()

        if registration_id not in db["registrations"]:
            return {"success": False, "error": f"No registration found with ID '{registration_id}'."}

        reg = db["registrations"][registration_id]

        if reg["status"] == "cancelled":
            return {"success": False, "error": "This registration is already cancelled."}

        # Mark as cancelled — seat automatically becomes available
        # (because _available_seats counts only "active" regs)
        db["registrations"][registration_id]["status"] = "cancelled"
        db["registrations"][registration_id]["cancelled_at"] = _now_str()
        save_db(db)

    event_name = db["events"].get(reg["event_id"], {}).get("name", "unknown event")
    return {
        "success": True,
        "message": f"Registration for '{reg['user_name']}' at '{event_name}' has been cancelled.",
    }


def list_registrations(event_id: str) -> dict:
    """Return all active registrations for a given event."""
    db = load_db()
    if event_id not in db["events"]:
        return {"success": False, "error": f"No event found with ID '{event_id}'."}

    active = [
        r for r in db["registrations"].values()
        if r["event_id"] == event_id and r["status"] == "active"
    ]
    active.sort(key=lambda r: r["registered_at"])

    return {"success": True, "registrations": active, "count": len(active)}
