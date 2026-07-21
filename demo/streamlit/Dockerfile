# Build from the repo root so we can install bdshare itself from source:
#   docker build -f demo/streamlit/Dockerfile -t bdshare-streamlit-demo .
# (docker-compose.yml in this directory sets the context automatically.)
FROM python:3.11-slim

WORKDIR /app

# time-zone
RUN set -x \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Dhaka  /etc/localtime \
    && echo "Asia/Dhaka" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy the whole repo so bdshare (with the new indicators/portfolio/stream/mcp
# features) installs from local source rather than whatever's on PyPI.
COPY . /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[ta,stream]" \
    && pip install --no-cache-dir -r demo/streamlit/requirements.txt

WORKDIR /app/demo/streamlit

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
