import pytest

@pytest.mark.asyncio
async def test_stats(client):
    response = client.get("/stats")
    assert response.status_code == 200
    stats = response.json()
    
    assert "total_messages" in stats
    assert stats["total_messages"] >= 3
    assert "senders_count" in stats
    assert isinstance(stats["messages_per_sender"], list)