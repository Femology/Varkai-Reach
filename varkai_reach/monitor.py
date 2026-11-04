"""Bounded one-shot research monitoring.

Run from cron/systemd/a trusted worker. This does not create a background
daemon or auto-login to social platforms. Every result retains source links.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .gateway import ReachGateway, ReachGatewayError
from .store import ResearchStore

STOP_CHANNEL = frozenset({"RATE_LIMITED", "PLATFORM_BLOCKED", "NEED_LOGIN", "BUSY"})
MAX_JOBS = 20
MAX_PER_JOB = 10
MAX_PLAN_BYTES = 65_536


def validate_plan(plan: Any) -> list[dict[str, Any]]:
    if not isinstance(plan, dict) or set(plan) != {"jobs"}:
        raise ValueError("Plan must be an object with only a 'jobs' key")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= MAX_JOBS:
        raise ValueError(f"Plan must contain 1–{MAX_JOBS} jobs")
    result: list[dict[str, Any]] = []
    names: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict) or not {"id", "channel", "query"}.issubset(job):
            raise ValueError("Every job needs an id, channel and query")
        if set(job) - {"id", "channel", "query", "limit"}:
            raise ValueError("Unknown job configuration keys")
        name, channel, query = job["id"], job["channel"], job["query"]
        limit = job.get("limit", 5)
        if not isinstance(name, str) or not 1 <= len(name) <= 64 or name in names:
            raise ValueError("Job IDs must be unique strings of 1–64 characters")
        if not isinstance(channel, str) or not channel.isascii() or not channel.isidentifier() or len(channel) > 24:
            raise ValueError("Invalid channel name")
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 400:
            raise ValueError("Each query must be 1–400 characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PER_JOB:
            raise ValueError(f"Limit must be 1–{MAX_PER_JOB} per job")
        names.add(name)
        result.append({"id": name, "channel": channel, "query": query.strip(), "limit": limit})
    return result


def run_plan(plan: Any, gateway: ReachGateway, store: ResearchStore) -> dict[str, Any]:
    """Check each configured source once. Never retry rate limits or login walls."""
    jobs = validate_plan(plan)
    held: set[str] = set()
    results: list[dict[str, Any]] = []
    for job in jobs:
        channel = job["channel"]
        row: dict[str, Any] = {"id": job["id"], "channel": channel}
        if channel in held:
            row.update({"status": "skipped", "reason": "Platform suspended for this run"})
            results.append(row)
            continue
        try:
            response = gateway.search(channel, job["query"], limit=job["limit"])
        except ReachGatewayError as exc:
            row.update({"status": "error", "error": {"code": "GATEWAY_ERROR", "message": str(exc)[:300]}})
            results.append(row)
            continue
        if not response.get("ok"):
            error = response.get("error") or {}
            code = str(error.get("code") or "UPSTREAM_ERROR")[:40] if isinstance(error, dict) else "UPSTREAM_ERROR"
            row.update({"status": "error", "error": {
                "code": code, "message": str(error.get("message") or "")[:300] if isinstance(error, dict) else ""
            }})
            if code in STOP_CHANNEL:
                held.add(channel)
            results.append(row)
            continue

        items = response.get("items") or []
        if not isinstance(items, list):
            items = []
        found = [item for item in items if isinstance(item, dict) and isinstance(item.get("url"), str)
                 and item["url"].startswith(("https://", "http://"))]
        known = store.known_urls(channel, [item["url"] for item in found])
        new = []
        seen: set[str] = set()
        for item in found:
            url = item["url"]
            if url not in known and url not in seen:
                new.append({"url": url, "title": str(item.get("title", ""))[:200]})
            seen.add(url)
        saved = store.save(channel, found)
        row.update({"status": "ok", "fetched": len(items), "saved": saved, "new_count": len(new), "new": new})
        results.append(row)
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "jobs": results,
        "total_new": sum(row.get("new_count", 0) for row in results),
        "errors": sum(row["status"] == "error" for row in results),
    }


def load_plan(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError("Plan file exceeds maximum allowed size")
    plan = json.loads(path.read_text(encoding="utf-8"))
    validate_plan(plan)
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded Varkai Reach research collection once")
    parser.add_argument("--plan", required=True, help="Path to a local JSON research plan")
    parser.add_argument("--database", help="Optional persistent SQLite database location")
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
        report = run_plan(plan, ReachGateway(), ResearchStore(args.database))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Invalid monitoring configuration: {exc}\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
