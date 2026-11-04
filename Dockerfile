# Alpha deployment: single-owner read-only MCP bridge.
# Browser-backed login channels are NOT configured in this image.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY agent_reach ./agent_reach
COPY varkai_reach ./varkai_reach
RUN python -m pip install --no-cache-dir ".[integrations]" \
    && useradd --system --create-home --home-dir /home/varkai varkai
USER varkai
EXPOSE 10000
CMD ["sh", "-c", "exec python -m varkai_reach --transport http --host 0.0.0.0 --port ${PORT:-10000}"]
