---
name: varkai-reach
description: Retrieve source-backed web and social research through Varkai Reach MCP; read-only.
---
# Varkai Reach
Use when an agent is asked to research media, communities or sites and retain evidence.
1. Call reach_channels before selecting a platform; channel actions vary.
2. Use reach_search for targeted queries and reach_read to verify actual source text.
3. Only set save=true if the user wants research memory; saved records contain source URLs and timestamps.
4. Use reach_findings to compare previous evidence.
5. Stop on NEED_LOGIN, RATE_LIMITED, PLATFORM_BLOCKED or BUSY and explain the failure.
Never claim exhaustive access, invent source text, bypass access checks, log passwords or use posting actions.
