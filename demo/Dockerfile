FROM python:3.11-slim-buster

# time-zone
RUN set -x \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Dhaka  /etc/localtime \
    && echo "Asia/Dhaka" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*


COPY . ./bdshare

WORKDIR /bdshare

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 9999

CMD [ "python", "app.py" ]