# Varkai Reach — cross-agent MCP bridge (alpha)

The original Agent Reach code and MIT licence remain intact. Varkai Reach adds **read-only** MCP tools for compatible AI clients. It does not automatically install into ChatGPT, handle social-media logins, bypass rate limits, or post content.

## Install and run

Requires Python 3.10+ and Agent Reach's original platform dependencies.

    python -m venv .venv
    . .venv/bin/activate
    pip install -e '.[integrations]'
    agent-reach setup
    python -m varkai_reach --transport stdio

On Windows, use .venv\Scripts\activate. The original setup command may install tools or require approval. Optional social channels must be enabled and authenticated **locally by the user**, on the machine hosting the bridge.

## Read-only MCP tools

- reach_channels(): list installed channels and their actions.
- reach_search(channel, query, limit=5, save=False): search one supported channel.
- reach_read(url, save=False): read one public HTTP(S) URL.
- reach_findings(query, limit=20): find saved source-backed research.

The MCP adapter deliberately exposes no login, setup, configuration, comment, posting or messaging commands. Results include only title, URL, author, date and text fields (where upstream supplies them); error codes are returned without secret CLI logs. Some channels lack search or require manual login.

Set save=true to persist research into local SQLite (default ~/.varkai-reach/findings.sqlite3; override VARKAI_REACH_DB). Stored data is **single-user only**, not isolated for multiple accounts.

### Claude Desktop / Claude Code / Cursor

Register this stdio server in your client's MCP configuration (see integrations/claude/mcp.json):

    {
      "mcpServers": {
        "varkai-reach": {
          "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
          "args": ["-m", "varkai_reach", "--transport", "stdio"]
        }
      }
    }

For Codex use integrations/codex/config.toml as a configuration template. Replace the interpreter path with the real Python path for your installation.

### Protected remote HTTP for MCP clients with custom bearer headers

This is a **manual-bearer-token** implementation, *not* OAuth 2.1. It does not yet support ChatGPT's automatic third-party OAuth connector or public directory submission.

    export VARKAI_REACH_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
    export VARKAI_REACH_PUBLIC_HOST="reach.example.com"
    python -m varkai_reach --transport http --host 127.0.0.1 --port 8000

Use an HTTPS reverse proxy to expose https://reach.example.com/mcp. Pass the bearer token through the client configuration (never paste secrets in chat or commit them). All MCP HTTP requests require Authorization: Bearer <token>; /healthz only exposes basic service health. HTTP will not start without a token of 24+ characters and an explicit hostname.

**Security:** URL input filtering is only a preflight against obvious SSRF targets; DNS rebinding and redirects remain possible. Deploy in an isolated, outbound-restricted network before allowing any untrusted input. Never enable this single-user service as shared, multi-tenant SaaS without per-user authentication and storage isolation. Observe website rules, privacy requirements, platform limits, and copyright.

## Verification

    pip install -e '.[dev,integrations]'
    pytest -q tests/test_varkai_gateway.py tests/test_varkai_store.py tests/test_varkai_auth.py

These are **mocked unit tests** and do not prove access to live YouTube, X, Instagram, Facebook or Reddit accounts. For live proof, run reach_channels then search/read a no-login channel, and separately verify each login-dependent channel.

## Roadmap

1. Alpha (this branch): MCP 2.x stdio + token-protected HTTP, read-only upstream adapter, SQLite source memory, unit tests and client templates.
2. Beta: deployed worker, scheduled and rate-limit-aware monitoring, Postgres, deduplication and provenance metrics.
3. Production: OAuth 2.1 identity provider, per-user isolation, scoped access and revocation, platform integration tests, app-directory submission.
4. Developer ecosystem: Claude plugin bundle, ChatGPT app integration, Codex skill packaging, SDKs and research dashboard.

Keep original upstream files intact to make merging future Agent Reach changes easier.
