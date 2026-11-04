"""Wire-level MCP integration tests with the official v2 in-memory client.

These tests make real MCP initialize / tools-list / tools-call requests, rather
than only unit-testing Python functions. Network/platform I/O remains mocked.
"""
import pytest
from mcp import Client

from varkai_reach.server import create_server
from varkai_reach.store import ResearchStore

SOURCE = {
    "title": "Screen readers lack usable labels",
    "url": "https://example.org/discussion/42",
    "author": "community-member",
    "published_at": "2026-11-04",
    "text": "The submit button is missing an accessible name.",
}


class StubGateway:
    def channels(self):
        return [{"name": "web", "level": "default", "actions": ["search", "read"]}]

    def search(self, channel, query, limit=5, timeout=35):
        assert channel == "web"
        assert query
        return {
            "ok": True, "channel": "web", "action": "search", "error": None,
            "items": [SOURCE],
        }

    def read(self, url, timeout=35):
        assert url.startswith("https://")
        return {
            "ok": True, "channel": "web", "action": "read", "error": None,
            "items": [SOURCE],
        }


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_client_can_discover_all_four_tools_and_call_them(tmp_path):
    server = create_server(gateway=StubGateway(), store=ResearchStore(tmp_path / "findings.sqlite3"))
    async with Client(server, raise_exceptions=True) as client:
        listing = await client.list_tools()
        tool_names = {tool.name for tool in listing.tools}
        assert tool_names == {
            "reach_channels", "reach_search", "reach_read", "reach_findings"
        }

        available = await client.call_tool("reach_channels", {})
        assert not available.is_error
        assert available.structured_content["channels"][0]["name"] == "web"

        search = await client.call_tool(
            "reach_search", {"channel": "web", "query": "accessibility",
                             "limit": 3, "save": True},
        )
        assert not search.is_error
        assert search.structured_content["saved_count"] == 1
        assert search.structured_content["items"][0]["url"] == SOURCE["url"]

        findings = await client.call_tool("reach_findings", {"query": "Screen readers"})
        assert not findings.is_error
        assert findings.structured_content["items"][0]["url"] == SOURCE["url"]

        read = await client.call_tool("reach_read", {"url": "https://example.org/discussion/42"})
        assert not read.is_error
        assert read.structured_content["items"][0]["text"] == SOURCE["text"]


@pytest.mark.anyio
async def test_invalid_search_error_is_structured_and_does_not_store(tmp_path):
    class InvalidGateway(StubGateway):
        def search(self, channel, query, limit=5, timeout=35):
            from varkai_reach.gateway import ReachGatewayError
            raise ReachGatewayError("Unsupported channel")

    store = ResearchStore(tmp_path / "records.sqlite3")
    server = create_server(gateway=InvalidGateway(), store=store)
    async with Client(server, raise_exceptions=True) as client:
        error = await client.call_tool(
            "reach_search", {"channel": "unavailable", "query": "startup", "save": True}
        )
        assert not error.is_error
        assert error.structured_content["ok"] is False
        assert "Unsupported" in error.structured_content["error"]
    assert store.find("startup") == []
