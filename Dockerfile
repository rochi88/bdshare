FROM python:3.11-slim-buster

# time-zone
RUN set -x \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Dhaka  /etc/localtime \
    && echo "Asia/Dhaka" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /demo

COPY ./demo/ ./

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 9999

# COPY . .

CMD [ "python", "app.py" ]