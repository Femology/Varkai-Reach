import pytest
from varkai_reach.store import ResearchStore

def test_save_upsert_search_and_provenance(tmp_path):
    store = ResearchStore(tmp_path / "nested" / "research.db")
    count = store.save("reddit", [
        {"url": "https://reddit.com/r/example/abc", "title": "Screen reader broken",
         "text": "App has no alt text", "author": "public-post", "published_at": "2026-11-01"},
        {"title": "No URL should be ignored", "text": "Anonymous"}])
    assert count == 1
    saved = store.find("alt text")
    assert saved[0]["channel"] == "reddit"
    assert saved[0]["published_at"] == "2026-11-01"
    assert saved[0]["url"].startswith("https://reddit.com/")
    assert saved[0]["collected_at"]
    store.save("reddit", [{"url": "https://reddit.com/r/example/abc", "title": "Updated", "text": "New"}])
    assert len(store.find("reddit")) == 1
    assert store.find("Updated")[0]["text"] == "New"

def test_search_metacharacters_are_literal(tmp_path):
    store = ResearchStore(tmp_path / "data.db")
    store.save("web", [{"url": "https://example.com/1", "title": "100% works"},
                       {"url": "https://example.com/2", "title": "unrelated"}])
    assert len(store.find("%")) == 1
    assert store.find("_") == []
    with pytest.raises(ValueError): store.find("", 10)
    with pytest.raises(ValueError): store.find("test", 1000)
