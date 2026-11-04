"""Unit tests mock upstream; no platform accounts are accessed."""
import json
import socket
import subprocess
import pytest
from varkai_reach.gateway import ReachGateway, ReachGatewayError, validate_public_url

CHANNELS = {"ok": True, "channels": [
    {"name": "youtube", "level": "default", "actions": [
        {"name": "search", "params": [
            {"name": "query", "required": True, "type": "str"},
            {"name": "limit", "required": False, "type": "int"}]}]},
    {"name": "github", "level": "default", "actions": [{"name": "read", "params": []}]},
]}

class FakeRunner:
    def __init__(self): self.calls = []
    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[-1] == "channels":
            payload = CHANNELS
        else:
            payload = {"ok": True, "channel": "youtube", "action": "search",
                       "items": [{"title": "Example", "url": "https://youtube.com/watch?v=1",
                                  "text": "A complaint", "raw": {"token": "DO_NOT_RETURN"}}],
                       "meta": {"cookies": "DO_NOT_RETURN"}}
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="private")

def fake_resolver(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]

def test_search_uses_allowlisted_channel_and_no_shell():
    runner = FakeRunner()
    bridge = ReachGateway(runner=runner)
    result = bridge.search("youtube", "accessibility problems", limit=7)
    assert result["ok"] is True
    assert "--limit" in runner.calls[1]
    assert "raw" not in result["items"][0]
    assert "cookies" not in str(result)

def test_disallow_management_and_unknown_channels():
    bridge = ReachGateway(runner=FakeRunner())
    with pytest.raises(ReachGatewayError, match="Unsupported"):
        bridge.search("login", "password")
    with pytest.raises(ReachGatewayError, match="no search"):
        bridge.search("github", "issues")

@pytest.mark.parametrize("target", [
    "file:///etc/passwd", "http://localhost/x", "http://127.0.0.1/admin",
    "https://192.168.1.5", "https://metadata.google.internal/", "https://x.com:9000/test",
    "https://user:pass@example.com", "https://[::1]/", "https://localhost.example.com@localhost/",
])
def test_url_ssrf_inputs_are_blocked(target):
    with pytest.raises(ReachGatewayError):
        validate_public_url(target, fake_resolver)

def test_dns_private_addresses_blocked():
    def private(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]
    with pytest.raises(ReachGatewayError, match="non-public"):
        validate_public_url("https://example.org/path", private)

def test_public_url_accepted_and_passed_to_read():
    bridge = ReachGateway(runner=FakeRunner(), resolver=fake_resolver)
    assert bridge.read("https://example.org/article")["ok"]

def test_upstream_error_code_preserved():
    def runner(argv, **kw):
        return subprocess.CompletedProcess(argv, 1, stdout=json.dumps({
            "ok": False, "channel": "reddit", "action": "read",
            "error": {"code": "NEED_LOGIN", "message": "Log in first", "hint": "Log in locally"}
        }), stderr="secret")
    reply = ReachGateway(runner=runner, resolver=fake_resolver).read("https://reddit.com/r/python")
    assert reply["ok"] is False
    assert reply["error"]["code"] == "NEED_LOGIN"
    assert "secret" not in str(reply)

def test_timeout_and_bad_json_fail_closed():
    def slow(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
    with pytest.raises(ReachGatewayError, match="timed out"):
        ReachGateway(runner=slow).channels()
    def broken(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="broken", stderr="secret")
    with pytest.raises(ReachGatewayError, match="JSON"):
        ReachGateway(runner=broken).channels()
