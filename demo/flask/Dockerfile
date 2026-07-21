# Build from the repo root:
#   docker build -f demo/flask/Dockerfile -t bdshare-flask-demo .
# (docker-compose.yml in this directory sets the context automatically.)
FROM python:3.11-slim

# time-zone
RUN set -x \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Dhaka  /etc/localtime \
    && echo "Asia/Dhaka" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r demo/flask/requirements.txt --upgrade

WORKDIR /app/demo/flask

EXPOSE 9999

CMD [ "python", "app.py" ]