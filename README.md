# Lyftr AI - Backend Assignment

A production-ready FastAPI service for ingesting webhook messages, built with Python, SQLite, and Docker. This service implements "`exactly-once`" message processing, `HMAC` security validation, and comprehensive observability.

## Setup Used
**Tools:** VSCode + GitHub Copilot + ChatGPT (used for Docker configuration, pytest setup, and debugging).

## Prerequisites
* **Docker Desktop** (must be installed and running)
* **Make** (optional, for running shortcut commands)

## How to Run
1.  **Start the Application:**
    ```bash
    make up
    # OR: docker compose up -d --build
    ```
    * The API will be available at: `http://localhost:8000`
    * Health Check: `http://localhost:8000/health/live`

2.  **Stop the Application:**
    ```bash
    make down
    # OR: docker compose down -v
    ```

## Testing
The project includes a comprehensive test suite covering security, idempotency, data persistence, and analytics.

**Run the tests:**
```bash
make test
# OR: docker compose exec -e PYTHONPATH=. api pytest
```

## API Endpoints

| Method | Endpoint          | Description |
|------|------------------|------------|
| POST | /webhook          | Ingests messages. Requires valid `X-Signature` header (HMAC-SHA256). |
| GET  | /messages         | Lists stored messages. Supports pagination (`limit`, `offset`) and filtering (`from`, `since`, `q`). |
| GET  | /stats            | Returns analytics (total count, top senders). |
| GET  | /metrics          | Prometheus-style metrics for monitoring. |
| GET  | /health/live      | Liveness probe (returns `200 OK`). |
| GET  | /health/ready     | Readiness probe (checks DB connection). |

---

## Example: Fetch Messages

```bash
# Fetch first 10 messages
curl "http://localhost:8000/messages?limit=10"

# Filter by sender (Note: '+' must be encoded as '%2B')
curl "http://localhost:8000/messages?from=%2B919876543210"
```

## Project Structure

```
/lyftr AI-backend-assignment
├── app/
│   ├── main.py            # API Routes & Lifespan logic
│   ├── storage.py         # Async SQLite database operations
│   ├── models.py          # SQL Schema & Pydantic models
│   ├── logging_utils.py   # JSON logging configuration
│   ├── metrics.py         # Prometheus metric definitions
│   └── config.py          # Environment variable management (12-factor)
├── tests/
│   ├── conftest.py        # Shared test fixtures (DB setup)
│   ├── test_webhook.py    # HMAC & Idempotency tests
│   ├── test_messages.py   # Pagination & Filter tests
│   └── test_stats.py      # Analytics tests
├── Dockerfile             # Multi-stage build
├── docker-compose.yml     # Service definition
├── Makefile               # Shortcuts (up, down, test, logs)
├── pytest.ini             # Pytest configuration
├── requirements.txt       # Python dependencies
└── README.md              # Documentation
```

## Design Decisions
**1. Security (HMAC Verification)**

**Implementation**: I used Python's `hmac.compare_digest` to validate the `X-Signature` header against the raw request body bytes.

**Reasoning**: `compare_digest` is designed to be resistant to timing attacks, whereas standard string comparison (`==`) can leak information about the signature length. Invalid signatures immediately return `401 Unauthorized` without hitting the database.

**2. Idempotency & Persistence**

**Implementation**: Idempotency is enforced at the database layer using a `PRIMARY KEY` constraint on `message_id`.

**Logic**: The application attempts to insert the row. If an `IntegrityError` is caught (indicating a duplicate), the app gracefully handles it, logs the event as `result="duplicate"`, and returns `200 OK` as required by the spec. This ensures data consistency even during retries or crashes.

**3. Pagination & Filtering**

**Strategy**: I used standard SQL `LIMIT` and `OFFSET` for pagination.

**Total Count**: The `total` field in the response reflects the count of the filtered dataset, not just the page size. This is achieved via a separate `SELECT COUNT(*)` query constructed dynamically based on the active filters (`from`, `since`, `q`).

**Input Validation**: `limit` (max 100) and `offset` (min 0) are strictly validated using FastAPI's Query parameters.

**4. Observability**

**Structured Logs**: All logs are emitted in JSON format using python-json-logger. Each log entry includes `request_id`, `latency_ms`, and relevant context (e.g., `message_id`, `dup`).

**Metrics**: I implemented Prometheus counters (`http_requests_total`, `webhook_requests_total`) to allow monitoring of success rates, duplicates, and validation errors.

---
**Submitted by**: Anadi Sharma





