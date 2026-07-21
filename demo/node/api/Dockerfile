# Build from the repo root so we can install bdshare itself from source:
#   docker build -f demo/node/api/Dockerfile -t bdshare-node-api .
# (docker-compose.yml in demo/ sets the context automatically.)
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[ta]" \
    && pip install --no-cache-dir -r demo/node/api/requirements.txt

WORKDIR /app/demo/node/api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
