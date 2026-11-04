"""Single-user SQLite research memory shared by agents on one host."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any

class ResearchStore:
    def __init__(self, path: str | Path | None = None):
        location = path or os.environ.get("VARKAI_REACH_DB", "~/.varkai-reach/findings.sqlite3")
        self.path = Path(location).expanduser()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(mode=0o600)
        self._init()

    def _connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '', published_at TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL DEFAULT '',
                collected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                UNIQUE(channel, url)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS findings_collected_at ON findings(collected_at)")

    def save(self, channel: str, items: list[dict[str, Any]]) -> int:
        """Only save normalized findings with real HTTP(S) source links."""
        saved = 0
        with self._connect() as db:
            for item in items:
                url = item.get("url", "")
                if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                    continue
                db.execute("""INSERT INTO findings(channel, url, title, author, published_at, text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(channel, url) DO UPDATE SET
                      title=excluded.title, author=excluded.author,
                      published_at=excluded.published_at, text=excluded.text,
                      collected_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')""",
                    (channel[:32], url[:2048], str(item.get("title", ""))[:2000],
                     str(item.get("author", ""))[:300], str(item.get("published_at", ""))[:100],
                     str(item.get("text", ""))[:12000]))
                saved += 1
        return saved

    def find(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 400:
            raise ValueError("Query must be between 1 and 400 characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")
        needle = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search = f"%{needle}%"
        with self._connect() as db:
            rows = db.execute("""SELECT id, channel, url, title, author, published_at,
                             text, collected_at FROM findings
                             WHERE title LIKE ? ESCAPE '\\' OR text LIKE ? ESCAPE '\\'
                               OR channel LIKE ? ESCAPE '\\'
                             ORDER BY collected_at DESC, id DESC LIMIT ?""",
                              (search, search, search, limit)).fetchall()
        return [dict(row) for row in rows]
