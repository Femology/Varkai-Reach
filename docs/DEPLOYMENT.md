# Varkai Reach deployment (single-owner alpha)

**Not deployed yet.** The Docker image and Render Blueprint are installation
templates, not a hosted product or an already connected ChatGPT plugin.

## Local container
Generate a strong secret privately. Use your own HTTPS hostname for
VARKAI_REACH_PUBLIC_HOST, for example reach.example.com.

    docker build -t varkai-reach .
    docker run --rm -p 10000:10000 \
      -e PORT=10000 \
      -e VARKAI_REACH_TOKEN \
      -e VARKAI_REACH_PUBLIC_HOST \
      varkai-reach

The health check is GET /healthz. The protected MCP endpoint is POST /mcp.
Requests require Authorization: Bearer <token>, with a matching Host header.
The MCP SDK enforces explicit Host and Origin allowlists.

For public use, terminate TLS at a trusted HTTPS reverse proxy and keep the
app isolated behind a network egress policy. Python hostname/IP preflight
is **not sufficient** to stop SSRF caused by HTTP redirects or DNS rebinding.

## Optional Render free-tier evaluation

A [render.yaml](../render.yaml) blueprint is included; deploying it is **not automatic**.
In Render, create a Blueprint from this repository only after selecting the
workspace and confirming the plan is free and will not replace existing services.

The blueprint generates a private bearer token and uses Render's assigned
RENDER_EXTERNAL_HOSTNAME. Configure the secret privately in an MCP client
supporting custom authorization headers. Do not post credentials in ChatGPT.

The image does not run Agent Reach's interactive platform setup automatically,
so channels requiring browser login are not available out of the box.
The free tier spins down when idle; the local SQLite database resets on
restarts/deploys. Do not store valuable or private findings on this test instance.

## Before making this multi-user or submitting to an app directory

- Replace static bearer auth with a tested OAuth 2.1 provider, supported
  client registration/metadata, user-scoped tokens and revocation.
- Move findings to persistent per-user storage and constrain queries.
- Block private-network outbound requests and validate redirect targets.
- Add rate limits, concurrency controls, and observability.
- Add real platform-specific integration tests and user-managed login procedures.
- Confirm official platform rules, privacy and acceptable-use requirements.
- Test with the exact ChatGPT/Claude clients and account permissions.

This alpha is NOT yet ready for public listing or shared hosting.
