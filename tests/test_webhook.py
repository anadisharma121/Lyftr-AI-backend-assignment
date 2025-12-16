import os
import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient


os.environ["WEBHOOK_SECRET"] = "testsecret"
os.environ["DATABASE_URL"] = "sqlite:///test_app.db"

from app.main import app
from app.storage import init_db


def compute_signature(secret: str, body: bytes) -> str:
    return hmac.new(
        secret.encode(), 
        body, 
        hashlib.sha256
    ).hexdigest()

@pytest.fixture(scope="module")
def client():

    with TestClient(app) as c:
        yield c
    

    if os.path.exists("test_app.db"):
        os.remove("test_app.db")

def test_health_check(client):
    """Simple check to ensure app is up."""
    response = client.get("/health/live")
    assert response.status_code == 200

def test_webhook_valid_insert(client):
    """
    Test a valid message insertion with correct signature.
    Requirements: Return 200, status ok[cite: 55].
    """
    secret = "testsecret"
    payload = {
        "message_id": "msg_001",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello World"
    }
    

    body_bytes = json.dumps(payload).encode()
    signature = compute_signature(secret, body_bytes)
    
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature
    }
    

    response = client.post("/webhook", content=body_bytes, headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_webhook_idempotency_duplicate(client):
    """
    Test sending the SAME message_id twice.
    Requirements: 
    1. First call: 200 OK.
    2. Second call: 200 OK (must not fail). 
    """
    secret = "testsecret"
    payload = {
        "message_id": "msg_duplicate_test",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Idempotency Check"
    }
    
    body_bytes = json.dumps(payload).encode()
    signature = compute_signature(secret, body_bytes)
    headers = {"Content-Type": "application/json", "X-Signature": signature}
    
    response1 = client.post("/webhook", content=body_bytes, headers=headers)
    assert response1.status_code == 200
    
    response2 = client.post("/webhook", content=body_bytes, headers=headers)
    assert response2.status_code == 200
    assert response2.json() == {"status": "ok"}

def test_webhook_invalid_signature(client):
    """
    Test with a wrong signature.
    Requirements: Return 401[cite: 41].
    """
    payload = {
        "message_id": "msg_hacker",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Malicious payload"
    }
    body_bytes = json.dumps(payload).encode()
    
    headers = {"X-Signature": "deadbeef1234567890"}
    
    response = client.post("/webhook", content=body_bytes, headers=headers)
    
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}

def test_webhook_missing_signature(client):
    """
    Test with missing X-Signature header.
    Requirements: Return 401 [cite: 40-41].
    """
    payload = {"message_id": "msg_no_sig", "from": "+123", "to": "+456", "ts": "2025-01-01"}
    
    response = client.post("/webhook", json=payload) 
    
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}

def test_webhook_invalid_payload(client):
    """
    Test with invalid schema (missing required fields).
    Requirements: Return 422.
    """
    secret = "testsecret"

    payload = {
        "message_id": "msg_bad_schema",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Missing fields"
    }
    
    body_bytes = json.dumps(payload).encode()
    signature = compute_signature(secret, body_bytes)
    headers = {"Content-Type": "application/json", "X-Signature": signature}
    
    response = client.post("/webhook", content=body_bytes, headers=headers)
    
    assert response.status_code == 422

    assert "detail" in response.json()