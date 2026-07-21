# Build from the repo root:
#   docker build -f demo/node/mcp/Dockerfile -t bdshare-mcp-demo .
# Runs bdshare-mcp over streamable-http instead of the default stdio
# transport, so the Node.js container (or any non-Python program) can reach
# it over the network the way an AI agent would over stdio locally.
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[mcp]"

EXPOSE 8000

ENTRYPOINT ["bdshare-mcp"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
