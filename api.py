"""
api.py — REST API built with Flask.

WHAT IS A REST API?
  REST = Representational State Transfer
  It's a set of conventions for HTTP endpoints:

    POST   /events              → Create a resource
    GET    /events              → Read/list resources
    GET    /events/<id>         → Read one resource
    POST   /registrations       → Create a registration
    DELETE /registrations/<id>  → Cancel (soft-delete)

HOW TO RUN:
    python api.py
    Then test with: curl, Postman, or browser (for GET requests)

HTTP STATUS CODES USED:
    200 OK          — Request succeeded
    201 Created     — New resource created
    400 Bad Request — Client sent invalid data
    404 Not Found   — Resource doesn't exist
    409 Conflict    — Duplicate / constraint violation (e.g. already registered)
"""

from flask import Flask, request, jsonify
import service

app = Flask(__name__)


# ── Utility: turn service response into HTTP response ─────────────────────
def _respond(result: dict, success_code: int = 200):
    """
    Convert the standard {"success": bool, ...} dict from service.py
    into a proper Flask HTTP response with the right status code.
    """
    if result.get("success"):
        return jsonify(result), success_code
    else:
        # Pick the right error code based on the error message
        error = result.get("error", "")
        if "already" in error or "already registered" in error or "already exists" in error:
            code = 409  # Conflict
        elif "not found" in error.lower() or "No event" in error or "No registration" in error:
            code = 404  # Not Found
        else:
            code = 400  # Bad Request (validation error)
        return jsonify(result), code


# ═══════════════════════════════════════════════════════════════════════════
# EVENTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/events", methods=["POST"])
def create_event():
    """
    POST /events
    Body (JSON): {"name": "Tech Summit", "total_seats": 100, "date": "2025-09-15"}
    """
    body = request.get_json(silent=True) or {}
    result = service.create_event(
        name        = body.get("name", ""),
        total_seats = body.get("total_seats", 0),
        event_date  = body.get("date", ""),
    )
    return _respond(result, success_code=201)


@app.route("/events", methods=["GET"])
def list_events():
    """
    GET /events
    Query params:
        ?upcoming=true   → filter to future events only
        ?sort=date       → sort by date (default)
    """
    upcoming_only = request.args.get("upcoming", "").lower() == "true"
    sort_by_date  = request.args.get("sort", "date") == "date"
    result = service.list_events(sort_by_date=sort_by_date, upcoming_only=upcoming_only)
    return _respond(result)


@app.route("/events/<event_id>", methods=["GET"])
def get_event(event_id):
    """GET /events/evt_a3f9c2 → returns a single event with seat info"""
    result = service.get_event(event_id)
    return _respond(result)


@app.route("/events/<event_id>/registrations", methods=["GET"])
def event_registrations(event_id):
    """GET /events/<id>/registrations → list all active registrations for an event"""
    result = service.list_registrations(event_id)
    return _respond(result)


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/registrations", methods=["POST"])
def register_user():
    """
    POST /registrations
    Body (JSON): {"user_name": "Alice", "event_id": "evt_a3f9c2"}
    """
    body = request.get_json(silent=True) or {}
    result = service.register_user(
        user_name = body.get("user_name", ""),
        event_id  = body.get("event_id", ""),
    )
    return _respond(result, success_code=201)


@app.route("/registrations/<registration_id>", methods=["DELETE"])
def cancel_registration(registration_id):
    """DELETE /registrations/reg_7b1d4e → cancel a registration"""
    result = service.cancel_registration(registration_id)
    return _respond(result)


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    """GET /health → simple ping to confirm server is running"""
    return jsonify({"status": "ok", "service": "Event Registration API"}), 200


# ── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Event Registration API running at http://localhost:5000")
    print("   Try: GET http://localhost:5000/events")
    app.run(debug=True, port=5000)
