FROM python:3.10.1-buster

# time-zone
RUN set -x \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Dhaka  /etc/localtime \
    && echo "Asia/Dhaka" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir beautifulsoup4
RUN pip install --no-cache-dir requests
RUN pip install --no-cache-dir html5lib
RUN pip install --no-cache-dir pandas
RUN pip install --no-cache-dir bdshare --upgrade