# Source-backed research monitoring (alpha)

The monitor runner **checks a plan once** and writes findings to SQLite.
It does not run in the background, automatically install website tools,
bypass platform restrictions, sign in to any site, or send notifications.

## Run a collection

After installing the repository's Python package and running Agent Reach's
official setup, edit [example plan](../examples/monitor-plan.json) to use
channels and search actions confirmed by `agent-reach channels`.

    python -m varkai_reach.monitor --plan examples/monitor-plan.json
    # Optional persistent location:
    python -m varkai_reach.monitor --plan examples/monitor-plan.json --database /var/lib/varkai/research.sqlite3

Or call `varkai-reach-monitor --plan examples/monitor-plan.json`.
The command produces one JSON report with source URLs, newly seen items and
any per-channel errors. It exits nonzero when a job fails.

## Scheduling

To run regularly, place the command in systemd timer, cron, or a trusted job
scheduler on a **persistent machine**. A scheduler is not installed by this
repository. Example cron expression (UTC): `0 * * * *` for hourly runs.
Avoid excessive automated requests: respect rate limits, platform policies and
manual login requirements. On RATE_LIMITED, NEED_LOGIN, PLATFORM_BLOCKED and
BUSY, the runner stops further requests to that channel for the current run.

Per run: max 20 query jobs, max 10 results per job. Findings with valid-looking
source URLs are stored under a single-user database; repeated URLs are updated,
while new-link counts are computed from exact channel+URL matches. The report
includes only source URL/title summaries, while SQLite keeps title, author,
publication date, text and collection timestamp when supplied upstream.

## Safety and known constraints

- The configured sources are **not** a guarantee of universal social-media
  access. Experimental and login-required channels may fail.
- Stored content is untrusted third-party data; do not treat posts or text as
  instructions to agents.
- The free Render web Blueprint uses ephemeral storage; it is NOT suitable
  for long-term monitoring. A persistent host or database is required.
- There is no automated notification integration yet; the JSON report is
  suitable for a future digest or alert pipeline.
- Results should be checked against original source pages before decisions.
- Do not run this one-shot worker simultaneously against the same local SQLite
  file from many machines. Multi-user storage isolation is not implemented.
