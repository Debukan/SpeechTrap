import pytest
import json
from datetime import datetime
import asyncio
from app.api.endpoints.ws import manager, ConnectionManager


class DummyWebSocket:
    def __init__(self):
        self.sent = []
        self.headers = {}
        self.closed = False

    async def accept(self):
        pass

    async def send_text(self, message: str):
        self.sent.append(message)

    async def close(self, code=None, reason=None):
        self.closed = True


@pytest.fixture(autouse=True)
def clear_connections():
    manager.active_connections.clear()
    yield
    manager.active_connections.clear()


@pytest.mark.asyncio
async def test_serialize_datetime_success():
    cm = ConnectionManager()
    dt = datetime(2021, 12, 31, 23, 59, 59)
    iso = cm.serialize_datetime(dt)
    assert iso == dt.isoformat()


@pytest.mark.asyncio
async def test_serialize_datetime_error():
    cm = ConnectionManager()
    with pytest.raises(TypeError):
        cm.serialize_datetime("not a datetime")


@pytest.mark.asyncio
async def test_connect_and_disconnect_user():
    ws = DummyWebSocket()
    await manager.connect(ws, "roomX", user_id=42)
    assert "roomX" in manager.active_connections
    assert 42 in manager.active_connections["roomX"]
    manager.disconnect("roomX", user_id=42)
    assert "roomX" not in manager.active_connections


@pytest.mark.asyncio
async def test_connect_and_disconnect_anonymous():
    ws = DummyWebSocket()
    await manager.connect(ws, "roomY")
    room = manager.active_connections.get("roomY", {})
    assert ws in room.values()
    manager.disconnect("roomY", websocket=ws)
    assert "roomY" not in manager.active_connections


@pytest.mark.asyncio
async def test_broadcast_and_exclusions():
    ws1 = DummyWebSocket()
    ws2 = DummyWebSocket()
    await manager.connect(ws1, "roomB", user_id=1)
    await manager.connect(ws2, "roomB", user_id=2)
    await manager.broadcast("roomB", {"type": "msg_all"})
    assert len(ws1.sent) == 1 and len(ws2.sent) == 1
    ws1.sent.clear()
    ws2.sent.clear()
    await manager.broadcast("roomB", {"type": "msg_excl"}, exclude_user_id=2)
    assert len(ws1.sent) == 1 and len(ws2.sent) == 0


@pytest.mark.asyncio
async def test_send_personal_message():
    ws1 = DummyWebSocket()
    ws2 = DummyWebSocket()
    await manager.connect(ws1, "roomZ", user_id=5)
    await manager.connect(ws2, "roomZ", user_id=6)
    await manager.send_personal_message("5", {"hello": "user5"})
    assert any("hello" in s for s in ws1.sent)
    assert not ws2.sent
