import pytest

@pytest.mark.asyncio
async def test_list_messages_pagination(client):
    response = client.get("/messages?limit=2&offset=0")
    data = response.json()
    
    assert len(data["data"]) == 2

    assert data["data"][0]["message_id"] == "m1"


@pytest.mark.asyncio
async def test_list_messages_filter_from(client):
    response = client.get("/messages", params={"from": "+222"}) 
    data = response.json()
    
    assert len(data["data"]) == 1
    assert data["data"][0]["message_id"] == "m3"

@pytest.mark.asyncio
async def test_list_messages_filter_since(client):

    response = client.get("/messages?since=2025-01-02T00:00:00Z")
    data = response.json()
    
    ids = [d['message_id'] for d in data['data']]
    assert "m2" in ids
    assert "m3" in ids
    assert "m1" not in ids