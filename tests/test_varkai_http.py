"""Transport-level test: real ASGI HTTP messages, without social-network I/O.

This verifies that the Streamable HTTP endpoint is mounted, requires a bearer
token, checks Host/Origin headers, and accepts a valid MCP initialization.
"""
from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="Varkai HTTP tests require the optional MCP integration")
httpx = pytest.importorskip("httpx")
from varkai_reach.server import create_http_app, create_server
from varkai_reach.store import ResearchStore

TOKEN = "alpha-test-bearer-token-that-is-not-real"
HOST = "reach.example.org"


class StubGateway:
    def channels(self):
        return [{"name": "web", "level": "default", "actions": ["read", "search"]}]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_http_auth_host_origin_and_mcp_initialize(tmp_path):
    server = create_server(
        gateway=StubGateway(),
        store=ResearchStore(tmp_path / "research.sqlite3"),
    )
    app = create_http_app(server, TOKEN, HOST)
    transport = httpx.ASGITransport(app=app)
    async with app.app.router.lifespan_context(app.app):
        async with httpx.AsyncClient(transport=transport, base_url=f"https://{HOST}") as client:
            health = await client.get("/healthz")
            assert health.status_code == 200
            assert health.json()["ok"] is True

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "Varkai HTTP integration test", "version": "1"},
                },
            }
            common = {
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
            }
            denied = await client.post("/mcp", json=payload, headers=common)
            assert denied.status_code == 401
            assert "unauthorized" in denied.text.lower()

            headers = {**common, "authorization": f"Bearer {TOKEN}"}

            wrong_host = await client.post(
                "/mcp", json=payload, headers={**headers, "host": "attacker.example"}
            )
            assert wrong_host.status_code == 421

            wrong_origin = await client.post(
                "/mcp", json=payload, headers={**headers, "origin": "https://evil.example"}
            )
            assert wrong_origin.status_code == 403

            good = await client.post(
                "/mcp", json=payload, headers={**headers, "origin": "https://chatgpt.com"}
            )
            assert good.status_code == 200, good.text[:500]
            response = good.json()
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response

            tools = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers=headers,
            )
            assert tools.status_code == 200, tools.text[:500]
            names = {tool["name"] for tool in tools.json()["result"]["tools"]}
            assert names == {
                "reach_channels", "reach_search", "reach_read", "reach_findings"
            }
