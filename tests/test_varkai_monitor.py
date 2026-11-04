"""Offline deterministic tests of bounded monitoring (no public APIs)."""
import pytest

from varkai_reach.gateway import ReachGatewayError
from varkai_reach.monitor import run_plan, validate_plan
from varkai_reach.store import ResearchStore


class StubGateway:
    def __init__(self):
        self.calls = []

    def search(self, channel, query, limit=5):
        self.calls.append((channel, query, limit))
        return {
            "ok": True, "channel": channel,
            "items": [
                {"title": "Accessible software complaint",
                 "url": "https://example.org/discussion/42",
                 "text": "Assistive tech users struggle with the dashboard"},
                {"title": "Another issue", "url": "https://example.org/discussion/43"},
            ]
        }


def plan(jobs):
    return {"jobs": jobs}


def job(id="accessibility", channel="reddit", query="screen reader software"):
    return {"id": id, "channel": channel, "query": query, "limit": 3}


def test_first_run_identifies_new_links_repeat_does_not(tmp_path):
    store = ResearchStore(tmp_path / "data.sqlite3")
    gateway = StubGateway()
    first = run_plan(plan([job()]), gateway, store)
    second = run_plan(plan([job()]), gateway, store)
    assert first["total_new"] == 2
    assert second["total_new"] == 0
    assert first["errors"] == 0
    assert len(store.known_urls("reddit", ["https://example.org/discussion/42"])) == 1
    assert len(store.find("Accessible software")) == 1
    assert len(gateway.calls) == 2


def test_duplicate_links_within_one_search_not_counted_as_new(tmp_path):
    class Duplicates(StubGateway):
        def search(self, channel, query, limit=5):
            item = {"title": "Same post", "url": "https://example.org/a"}
            return {"ok": True, "items": [item, item]}

    summary = run_plan(plan([job()]), Duplicates(), ResearchStore(tmp_path / "dedup.db"))
    assert summary["total_new"] == 1
    assert summary["jobs"][0]["new"] == [{"url": "https://example.org/a", "title": "Same post"}]


def test_rate_limit_stops_same_channel_only(tmp_path):
    class Blocked(StubGateway):
        def search(self, channel, query, limit=5):
            self.calls.append(channel)
            if channel == "reddit":
                return {"ok": False, "error": {
                    "code": "RATE_LIMITED", "message": "Please wait"
                }}
            return {"ok": True, "items": [
                {"title": "Real article", "url": "https://example.com/article"}
            ]}

    gateway = Blocked()
    summary = run_plan(plan([
        job("a", "reddit"), job("b", "reddit", "more"), job("c", "web", "AI news"),
    ]), gateway, ResearchStore(tmp_path / "db.sqlite3"))
    assert gateway.calls == ["reddit", "web"]
    assert [entry["status"] for entry in summary["jobs"]] == ["error", "skipped", "ok"]
    assert summary["errors"] == 1
    assert summary["total_new"] == 1


def test_gateway_exception_does_not_crash_remaining_jobs(tmp_path):
    class Broken(StubGateway):
        def search(self, channel, query, limit=5):
            if channel == "reddit":
                raise ReachGatewayError("Upstream unavailable")
            return super().search(channel, query, limit)

    summary = run_plan(plan([job(), job("web", "web")]), Broken(),
                       ResearchStore(tmp_path / "db.sqlite3"))
    assert summary["errors"] == 1
    assert summary["jobs"][0]["error"]["code"] == "GATEWAY_ERROR"
    assert summary["jobs"][1]["status"] == "ok"


@pytest.mark.parametrize("invalid", [
    {}, {"jobs": []}, {"jobs": "bad"},
    {"jobs": [job()], "shell": "rm -rf /"},
    {"jobs": [job(), job()]},
    {"jobs": [{"id": "x", "channel": "reddit"}]},
    {"jobs": [{**job(), "limit": True}]},
    {"jobs": [{**job(), "limit": 999}]},
    {"jobs": [{**job(), "channel": "../etc"}]},
])
def test_invalid_configurations_rejected(invalid):
    with pytest.raises(ValueError):
        validate_plan(invalid)
