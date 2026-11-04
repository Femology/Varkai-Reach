# Varkai Reach live smoke test — 2026-11-04

## Environment
Ephemeral Ubuntu 22.04-based browser VM, Python 3.10, isolated virtualenv.
Source: the latest public Femology/Varkai-Reach main branch at the time of test.
The VM was destroyed after testing. No passwords, cookies or paid API keys were used.
No persistent cloud deployment or ChatGPT connector was created.

## Evidence and outcomes

1. Original \`agent-reach channels\` returned \`ok: true\` and 14 channels;
   these are **declared capabilities**, not 14 confirmed functional integrations.
2. Original \`agent-reach github search accessibility\` returned \`ok: true\`,
   backend \`github-api\` and five results, with source URLs.
3. Varkai monitor ran twice with query \`accessibility\`, channel \`github\`,
   and max 3 items. The first run saved three new URLs; the second found
   **zero new** URLs. Both runs returned \`errors: 0\`.
4. The real Varkai Reach HTTP server started with an ephemeral test token,
   a sample public hostname and its local listening socket.
5. HTTP requests with no bearer token returned \`401\`; authenticated
   \`tools/list\` returned \`200\` and exposed \`reach_channels\`,
   \`reach_search\`, \`reach_read\`, \`reach_findings\`.
6. An authenticated \`tools/call\` invoking \`reach_search\` on public GitHub
   returned \`HTTP 200\`, \`ok: true\`, two source URLs, and \`saved_count: 2\`.
   Example returned sources: https://github.com/nvaccess/nvda and
   https://github.com/dkager/tolk.

## What this proves — and does not prove

Proves that the **real** Agent Reach CLI and Varkai MCP HTTP adapter cooperate
on public GitHub searches, returning structured results and saving links.

It **does not prove** that all the declared channels work; authentication-
required and experimental Twitter/X, Instagram, Facebook, and Reddit modes
were not exercised. Nor does this prove that the hosted client can connect from
a real ChatGPT Plus account or that persistent cloud monitoring is configured.

## Repeatable tests

The deterministic tests are under \`tests/test_varkai_*.py\`.
To run another platform test, install the repository and the optional
integrations extra, configure the channel according to upstream guidance,
and invoke \`agent-reach channels\` followed by an explicitly authorized
read-only search. Respect platform rate limits and never commit sessions.

For local monitoring:

    varkai-reach-monitor --plan examples/monitor-plan.json --database /your/persistent/research.sqlite3

No monitoring scheduler is automatically created by this repo.
