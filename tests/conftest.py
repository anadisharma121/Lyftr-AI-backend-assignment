import pytest
import os
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.storage import init_db, insert_message


TEST_DB_FILE = "test_shared.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DB_URL

async def _seed_logic():
    """Internal async logic to populate the DB."""
    await init_db()
    
    messages = [
        {"message_id": "m1", "from": "+111", "to": "+999", "ts": "2025-01-01T10:00:00Z", "text": "Oldest", "created_at": "2025-01-01T10:00:00Z"},
        {"message_id": "m2", "from": "+111", "to": "+999", "ts": "2025-01-02T10:00:00Z", "text": "Middle", "created_at": "2025-01-02T10:00:00Z"},
        {"message_id": "m3", "from": "+222", "to": "+999", "ts": "2025-01-03T10:00:00Z", "text": "Newest", "created_at": "2025-01-03T10:00:00Z"},
    ]
    
    for m in messages:
        
        try:
            await insert_message(m)
        except Exception:
            pass

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Synchronous fixture that runs once per session.
    It manually runs the async seed logic to guarantee execution.
    """

    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
         
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_seed_logic())
    loop.close()
    
    yield
    
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c