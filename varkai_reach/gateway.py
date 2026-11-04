"""Constrained adapter around Agent Reach's read-only JSON CLI."""
from __future__ import annotations
import ipaddress
import json
import socket
import subprocess
import sys
from typing import Any, Callable
from urllib.parse import urlsplit

MAX_QUERY = 400
MAX_ITEMS = 25
MAX_TEXT = 12000
MAX_STDOUT = 4000000

class ReachGatewayError(Exception):
    """Invalid request or unavailable upstream command."""

def validate_public_url(url: str, resolver: Callable[..., Any] = socket.getaddrinfo) -> str:
    """Reject obvious SSRF targets; production MUST also enforce network egress policies."""
    if not isinstance(url, str) or len(url) > 2048:
        raise ReachGatewayError("URL must be a string of at most 2048 characters")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ReachGatewayError("Malformed URL") from exc
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ReachGatewayError("Only public HTTP(S) URLs are supported")
    if parsed.username or parsed.password or (port is not None and port not in (80, 443)):
        raise ReachGatewayError("URL credentials and nonstandard ports are not allowed")
    hostname = parsed.hostname.rstrip(".").lower()
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None and not literal_ip.is_global:
        raise ReachGatewayError("URL contains a non-public IP address")
    if (hostname in ("localhost", "localhost.localdomain")
            or hostname.endswith((".localhost", ".local", ".internal", ".test"))
            or "." not in hostname):
        raise ReachGatewayError("Private or unqualified hostnames are not allowed")
    try:
        addresses = resolver(hostname, port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise ReachGatewayError("Cannot resolve URL hostname") from exc
    if not addresses:
        raise ReachGatewayError("URL hostname has no addresses")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address[4][0])
        except (ValueError, IndexError, TypeError) as exc:
            raise ReachGatewayError("Unverifiable DNS response") from exc
        if not ip.is_global:
            raise ReachGatewayError("URL resolves to a non-public IP address")
    return url

def _clean_items(items: object) -> list[dict[str, Any]]:
    """Return useful source fields, not raw backend data or credentials."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items[:MAX_ITEMS]:
        if not isinstance(item, dict):
            continue
        clean = {}
        for key in ("title", "url", "author", "published_at", "text"):
            val = item.get(key)
            if isinstance(val, (str, int, float)) and not isinstance(val, bool):
                clean[key] = str(val)[:MAX_TEXT]
        if clean:
            result.append(clean)
    return result

def _normalise(reply: dict[str, Any]) -> dict[str, Any]:
    error = reply.get("error")
    return {
        "ok": reply.get("ok") is True,
        "channel": reply.get("channel"),
        "action": reply.get("action"),
        "items": _clean_items(reply.get("items")),
        "error": {k: str(error[k])[:500] for k in ("code", "message", "hint") if k in error}
        if isinstance(error, dict) else None,
    }

class ReachGateway:
    """Read-only bridge; account management and shell commands are inaccessible."""
    def __init__(self, runner: Callable[..., Any] = subprocess.run,
                 command: list[str] | None = None,
                 resolver: Callable[..., Any] = socket.getaddrinfo):
        self._runner = runner
        self._command = command or [sys.executable, "-m", "agent_reach.cli"]
        self._resolver = resolver

    def _invoke(self, args: list[str], timeout: int = 35) -> dict[str, Any]:
        if not 1 <= timeout <= 90:
            raise ReachGatewayError("Timeout must be between 1 and 90 seconds")
        try:
            completed = self._runner(self._command + args, capture_output=True, text=True,
                                     timeout=timeout + 5, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ReachGatewayError("Agent Reach timed out") from exc
        except OSError as exc:
            raise ReachGatewayError("Agent Reach is not installed or cannot start") from exc
        stdout = completed.stdout or ""
        if len(stdout) > MAX_STDOUT:
            raise ReachGatewayError("Agent Reach returned an oversized response")
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ReachGatewayError("Agent Reach did not return its expected JSON envelope") from exc
        if not isinstance(data, dict) or not isinstance(data.get("ok"), bool):
            raise ReachGatewayError("Unexpected Agent Reach response format")
        return data

    def channels(self) -> list[dict[str, Any]]:
        data = self._invoke(["channels"], timeout=10)
        if not data["ok"] or not isinstance(data.get("channels"), list):
            raise ReachGatewayError("Could not retrieve Agent Reach channels")
        channels = []
        for ch in data["channels"]:
            if not isinstance(ch, dict):
                continue
            actions = ch.get("actions", [])
            channels.append({"name": ch.get("name"), "level": ch.get("level"),
                             "actions": [a.get("name") for a in actions if isinstance(a, dict)]})
        return channels

    def search(self, channel: str, query: str, limit: int = 5, timeout: int = 35) -> dict[str, Any]:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= MAX_QUERY:
            raise ReachGatewayError(f"Query must be between 1 and {MAX_QUERY} characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_ITEMS:
            raise ReachGatewayError(f"Limit must be between 1 and {MAX_ITEMS}")
        data = self._invoke(["channels"], timeout=10)
        channels = {c.get("name"): c for c in data.get("channels", []) if isinstance(c, dict)}
        current = channels.get(channel)
        if current is None:
            raise ReachGatewayError("Unsupported channel")
        action = next((a for a in current.get("actions", [])
                       if isinstance(a, dict) and a.get("name") == "search"), None)
        if action is None:
            raise ReachGatewayError(f"Channel '{channel}' has no search action")
        params = action.get("params", [])
        required = [p for p in params if isinstance(p, dict) and p.get("required")]
        if len(required) != 1 or required[0].get("type") != "str":
            raise ReachGatewayError("This channel requires a different search input")
        argv = [channel, "search", query.strip()]
        if any(p.get("name") == "limit" for p in params if isinstance(p, dict)):
            argv += ["--limit", str(limit)]
        argv += ["--timeout", str(timeout)]
        return _normalise(self._invoke(argv, timeout=timeout))

    def read(self, url: str, timeout: int = 35) -> dict[str, Any]:
        url = validate_public_url(url, self._resolver)
        return _normalise(self._invoke(["read", url, "--timeout", str(timeout)], timeout=timeout))
