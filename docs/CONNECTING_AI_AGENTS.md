# Connecting Varkai Reach to AI assistants

Varkai Reach currently runs as a **self-hosted MCP server**, not as an installed
ChatGPT Directory plugin. There is no live Varkai Reach URL yet.

## ChatGPT (important account boundary)

As of November 2026, direct custom MCP connections are documented for ChatGPT
Business and Enterprise/Edu workspaces, with more limited read/fetch options on
Pro. Do not assume ChatGPT Plus can install an arbitrary development server.
See the official account requirements:

https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt

If your workspace is eligible, the documented flow is Plugins → plus button →
Add custom MCP server, enter the HTTPS MCP URL (usually /mcp), configure an
authentication method that the client supports, and review the security warning.

**The current single-owner Varkai Bearer token is NOT OAuth 2.1.** It is
intended for controlled MCP clients that can send custom authorization headers,
NOT for public ChatGPT distribution. Do not remove authentication just to get
past a connector error. For a ChatGPT-compatible public release, implement and
verify a standards-compliant OAuth flow and submit the plugin for review.
Directory publication also requires OpenAI's organizational/individual
verification and review.

Official publishing guidance:
https://developers.openai.com/plugins/deploy/connect-chatgpt
https://developers.openai.com/plugins/build/auth

## Claude Code, Codex and Cursor

These local MCP clients can use the existing stdio endpoint. Install the
repository on your own computer or server, then load the example MCP configs
under `integrations/`. The agent-specific client must be configured by the
account owner; cloning the repository alone does not connect any assistant.

## Remote server and monitoring

The optional Docker/Render configuration provides an evaluation endpoint,
NOT automatic social-platform accounts. Run approved channel setup locally;
most login-gated sources require user interaction. Use the one-shot monitoring
runner with a persistent database and a deliberate scheduler for recurring
collection. Never publish session cookies, app keys, or private reports.

## Live connection acceptance criteria

1. Public HTTPS endpoint responds to `/healthz`.
2. MCP initialize, tool discovery and read actions pass from a real remote client.
3. Unauthorized requests cannot discover tools.
4. Each intended media platform is individually tested, documenting its
   authentication requirements and gaps.
5. Identity, user separation, persistent data, rate limiting, network egress
   controls and audit logging are verified before broad use.

These steps are **not yet complete**.
