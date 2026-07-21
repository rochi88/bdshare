# Build from the repo root:
#   docker build -f demo/node/stream/Dockerfile -t bdshare-stream-demo .
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[stream]"

EXPOSE 8765

ENTRYPOINT ["bdshare-stream"]
CMD ["--host", "0.0.0.0", "--port", "8765", "--symbols", "GP,ACI,SQURPHARMA,BEXIMCO,RENATA,BRACBANK"]
