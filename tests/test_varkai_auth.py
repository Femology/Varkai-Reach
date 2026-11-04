import asyncio
import pytest
from varkai_reach.server import BearerTokenMiddleware

async def fake_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})

def call(headers, path="/mcp"):
    events = []
    app = BearerTokenMiddleware(fake_app, "secure-long-development-token-0123456")
    async def record(event):
        events.append(event)
    async def run():
        await app({"type": "http", "path": path, "headers": headers}, lambda: None, record)
    asyncio.run(run())
    return events

def test_http_bearer_required():
    assert call([])[0]["status"] == 401
    assert call([(b"authorization", b"Bearer wrong")])[0]["status"] == 401
    assert call([(b"authorization", b"Bearer secure-long-development-token-0123456")])[0]["status"] == 200
    assert call([], path="/healthz")[0]["status"] == 200

def test_unsafe_short_token_rejected():
    with pytest.raises(ValueError):
        BearerTokenMiddleware(fake_app, "unsafe")
