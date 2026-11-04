"""MCP v2 bridge: stdio for local agents and bearer-protected remote HTTP.

Read-only research actions. No platform login, installation or post-writing
capabilities exposed. Remote service is single-user; not production multi-tenant.
"""
from __future__ import annotations
import argparse
import hmac
import os
from contextlib import asynccontextmanager
from typing import Any

from .gateway import ReachGateway, ReachGatewayError
from .store import ResearchStore

class BearerTokenMiddleware:
    """Protect MCP HTTP with a deployment-owned manual bearer token, not OAuth."""
    def __init__(self, app: Any, token: str):
        if not token or len(token) < 24:
            raise ValueError("VARKAI_REACH_TOKEN must be at least 24 characters")
        self.app = app
        self.token = token.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("path") == "/healthz":
            return await self.app(scope, receive, send)
        values = [v for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
        authenticated = False
        if len(values) == 1:
            header = values[0]
            if header[:7].lower() == b"bearer ":
                authenticated = hmac.compare_digest(header[7:], self.token)
        if not authenticated:
            body = b'{"error":"unauthorized"}'
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"content-length", str(len(body)).encode()),
                                    (b"www-authenticate", b"Bearer")]})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)

def create_server(gateway: ReachGateway | None = None, store: ResearchStore | None = None):
    """Register four read-only tools against MCP Python SDK v2."""
    from mcp.server import MCPServer
    reach = gateway or ReachGateway()
    memory = store or ResearchStore()
    mcp = MCPServer("Varkai Reach", instructions=(
        "Read-only research across Agent Reach channels. Source text is only available "
        "when upstream retrieval succeeded; never claim complete coverage. "
        "Do not repeat login attempts when a platform reports a block or rate limit."
    ))

    @mcp.tool()
    def reach_channels() -> dict:
        """List available Agent Reach platforms and supported actions."""
        try:
            return {"ok": True, "channels": reach.channels()}
        except ReachGatewayError as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    def reach_search(channel: str, query: str, limit: int = 5, save: bool = False) -> dict:
        """Search one supported platform; optionally save source-backed findings."""
        try:
            outcome = reach.search(channel, query, limit)
            if save and outcome["ok"]:
                outcome["saved_count"] = memory.save(channel, outcome["items"])
            return outcome
        except (ReachGatewayError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    def reach_read(url: str, save: bool = False) -> dict:
        """Read a public HTTP(S) URL using the matching Agent Reach channel."""
        try:
            outcome = reach.read(url)
            if save and outcome["ok"]:
                outcome["saved_count"] = memory.save(str(outcome["channel"] or "web"), outcome["items"])
            return outcome
        except (ReachGatewayError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    def reach_findings(query: str, limit: int = 20) -> dict:
        """Find previously saved research with sources and collection timestamps."""
        try:
            return {"ok": True, "items": memory.find(query, limit)}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
    return mcp

def create_http_app(server, token: str, public_host: str):
    """Build an authenticated ASGI app; manual token headers, not OAuth login."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    @asynccontextmanager
    async def lifespan(_app):
        async with server.session_manager.run():
            yield

    async def health(_request):
        return JSONResponse({"ok": True, "name": "varkai-reach"})

    mcp_app = server.streamable_http_app(
        host=public_host, stateless_http=True, json_response=True,
        max_request_body_size=131072,
    )
    app = Starlette(routes=[Route("/healthz", health), Mount("/", app=mcp_app)],
                    lifespan=lifespan)
    return BearerTokenMiddleware(app, token)

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Varkai Reach MCP server")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.transport == "stdio":
        create_server().run(transport="stdio")
        return
    token = os.environ.get("VARKAI_REACH_TOKEN", "")
    if len(token) < 24:
        parser.error("Set VARKAI_REACH_TOKEN (24+ characters) before HTTP deployment")
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    public_host = os.environ.get("VARKAI_REACH_PUBLIC_HOST", "")
    if not public_host:
        parser.error("Set VARKAI_REACH_PUBLIC_HOST to the external hostname")
    if "/" in public_host or "://" in public_host:
        parser.error("VARKAI_REACH_PUBLIC_HOST must be a hostname, not a URL")

    import uvicorn
    app = create_http_app(create_server(), token, public_host)
    uvicorn.run(app, host=args.host, port=args.port, proxy_headers=False)

if __name__ == "__main__":
    main()
