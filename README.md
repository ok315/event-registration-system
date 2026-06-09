# 🎫 Event Registration System

A Python CLI + REST API for managing events and registrations.

---

## Project Structure

```
event_system/
├── database.py   # Data layer — reads/writes JSON file
├── service.py    # Business logic — all rules and validation
├── api.py        # REST API — Flask HTTP endpoints
├── cli.py        # CLI  — Rich terminal interface
├── data.json     # Auto-created on first run (your database)
└── README.md
```

---

## Setup & Run

```bash
# Install dependencies
pip install flask filelock rich

# Run CLI
python cli.py

# Run REST API (separate terminal)
python api.py
```

---

## REST API Endpoints

| Method   | URL                                | Description                     |
|----------|------------------------------------|---------------------------------|
| `POST`   | `/events`                          | Create a new event              |
| `GET`    | `/events`                          | List all events                 |
| `GET`    | `/events?upcoming=true`            | Upcoming events only            |
| `GET`    | `/events/<id>`                     | Get one event                   |
| `GET`    | `/events/<id>/registrations`       | List registrations for an event |
| `POST`   | `/registrations`                   | Register a user                 |
| `DELETE` | `/registrations/<id>`              | Cancel a registration           |
| `GET`    | `/health`                          | Health check                    |

### Example curl commands

```bash
# Create an event
curl -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{"name": "Tech Summit", "total_seats": 5, "date": "2025-12-01"}'

# List all events
curl http://localhost:5000/events

# List upcoming events only
curl "http://localhost:5000/events?upcoming=true"

# Register a user
curl -X POST http://localhost:5000/registrations \
  -H "Content-Type: application/json" \
  -d '{"user_name": "Alice", "event_id": "evt_XXXXX"}'

# Cancel a registration
curl -X DELETE http://localhost:5000/registrations/reg_XXXXX

# See all registrations for an event
curl http://localhost:5000/events/evt_XXXXX/registrations
```

---

## Key Design Decisions (for interview)

### 1. Three-layer architecture
- `database.py` — only knows how to read/write files
- `service.py`  — only knows the business rules
- `api.py`/`cli.py` — only knows how to talk to users

If you swap JSON for SQLite, only `database.py` changes.

### 2. Race conditions solved with FileLock
Two users registering simultaneously for the last seat
can't both succeed because the entire check+write block
runs inside a file lock. One waits; one wins; one fails cleanly.

### 3. Available seats are derived, not stored
`available_seats = total_seats - count(active_registrations)`

This is always correct. Storing it separately risks bugs
where the count and the registrations go out of sync.

### 4. Soft deletes (cancellations)
Registrations are never deleted — just marked `"status": "cancelled"`.
This keeps an audit trail and makes debugging much easier.

### 5. Consistent return format
Every service function returns `{"success": bool, ...}`.
This makes it trivial to handle results in both CLI and API.

---

## Tricky Requirements Addressed

| Requirement              | Solution                                         |
|--------------------------|--------------------------------------------------|
| Race condition / overbooking | `filelock.FileLock` around check + write    |
| Duplicate registration   | Check for existing active reg before inserting   |
| Correct seat count       | Always computed dynamically from DB              |
| Proper error messages    | Every validation returns a descriptive message   |
| Soft cancel              | Status field: "active" / "cancelled"             |
