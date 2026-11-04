# Varkai Reach — ChatGPT / Codex plugin (private alpha)

Varkai Reach is an AI-assistant research workflow package sourced from the open-source codebase at https://github.com/Femology/Varkai-Reach (based on Agent Reach, https://github.com/Panniantong/Agent-Reach; MIT license).

This plugin includes four skills: setup, research, monitoring, and startup-intelligence. They guide research using whatever tools are **actually connected** to the assistant and document how to access the Varkai Reach MCP runtime when a suitable account/host is configured. It contains **no server executable**, login session, API key, OAuth registration, or active MCP connection.

The repository has a read-only MCP server exposing `reach_channels`, `reach_search`, `reach_read`, and `reach_findings`. A previous temporary smoke test proved public GitHub search through the MCP server; that does not prove access to the other declared Agent Reach channels. X, Instagram, Facebook and Reddit may be login-gated, experimental, or unavailable at any given time. Installing this plugin does **not** activate them.

Backend source and instructions:
- https://github.com/Femology/Varkai-Reach/tree/main/docs/CONNECTING_AI_AGENTS.md
- https://github.com/Femology/Varkai-Reach/tree/main/docs/MONITORING.md
- https://github.com/Femology/Varkai-Reach/tree/main/docs/LIVE_SMOKE_2026-11-04.md

To connect actual remote MCP tools, deploy on a suitable host, protect the endpoint with compatible user authentication, and connect through the client's supported MCP workflow. Do not remove authentication or expose platform login cookies. ChatGPT account and plugin connection permissions may vary.

This is **not** the separate Varkai REA software reverse-engineering plugin.
