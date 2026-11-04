---
name: monitoring
description: Create and verify bounded research-monitoring plans, find newly reported information, and report changes without claiming that a watcher or scheduler is active when it is not.
---

# Varkai Reach monitored-source workflow

## Determine monitoring intent
Clarify what concrete source, keyword, product, issue, region, and time window should be watched using prior conversation context. An ongoing request requires a real scheduled job or approved hosting worker—not merely a research prompt or plugin skill.

## If the Varkai Reach monitor runtime is available
- Use repository `varkai-reach-monitor --plan PLAN.json --database PATH` for a **single** bounded pass. It does not schedule itself.
- Plan is a JSON object with `jobs`: each job requires `id`, `channel`, `query`, optional `limit`. Limits are up to 20 jobs and 10 source results per job, with a query up to 400 characters. Confirm each channel supports search.
- Save only user-authorized source records; keep source URLs, collection timestamps, publication times (when available), and upsert deduplication.
- Treat `RATE_LIMITED`, `NEED_LOGIN`, `PLATFORM_BLOCKED`, `BUSY` as stop signals; don't defeat site controls.
- Report newly discovered links separately from previously known ones; do not assume any absence of new items means the entire internet had no new posts.
- Choose a persistent database, verified scheduler (cron/systemd or authorized automation), protected credentials and error alerts before describing monitoring as active. Free ephemeral hosts can lose data or sleep.

## If the runtime is not connected
Use any available user-authorized scheduled automation for research alerts only when actually created, or provide a validated plan. Do not claim the Varkai Reach backend is working or watching.

## Deliverables
Include checks performed, latest collection timestamp, real new-source count, errors and restrictions, next scheduled run only when it truly exists, and the user action needed for unresolved setup.
